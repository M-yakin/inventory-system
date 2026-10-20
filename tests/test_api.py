import copy
from unittest.mock import patch

import pytest

import app as app_module
from openfoodfacts import ExternalAPIError

SAMPLE = [
    {"id": 1, "barcode": "111", "product_name": "Cola", "brands": "BrandA",
     "ingredients_text": "water, sugar", "price": 1.5, "stock": 10},
    {"id": 2, "barcode": "222", "product_name": "Biscuit", "brands": "BrandB",
     "ingredients_text": "flour, sugar", "price": 2.0, "stock": 20},
]

FAKE_PRODUCT = {
    "barcode": "999",
    "product_name": "Nutella",
    "brands": "Ferrero",
    "ingredients_text": "sugar, palm oil",
}


@pytest.fixture
def client():
    """Fresh test client with a known inventory for every test."""
    app_module.inventory[:] = copy.deepcopy(SAMPLE)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


# ---------- GET ----------

def test_get_all_items(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_get_single_item(client):
    response = client.get("/inventory/1")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Cola"


def test_get_missing_item_returns_404(client):
    response = client.get("/inventory/99")
    assert response.status_code == 404
    assert "error" in response.get_json()


# ---------- POST ----------

def test_add_item(client):
    body = {"product_name": "Juice", "brands": "BrandC", "price": 3.0, "stock": 5}
    response = client.post("/inventory", json=body)
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] == 3
    assert data["product_name"] == "Juice"
    assert len(app_module.inventory) == 3


def test_add_item_enriched_from_api(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=FAKE_PRODUCT) as mock_fetch:
        response = client.post("/inventory", json={"barcode": "999", "price": 5.0, "stock": 10})
    assert response.status_code == 201
    data = response.get_json()
    assert data["product_name"] == "Nutella"
    assert data["brands"] == "Ferrero"
    assert data["ingredients_text"] == "sugar, palm oil"
    mock_fetch.assert_called_once_with("999")


def test_user_values_beat_api_values(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=FAKE_PRODUCT):
        response = client.post(
            "/inventory",
            json={"barcode": "999", "product_name": "My Spread", "price": 5.0, "stock": 10},
        )
    data = response.get_json()
    assert data["product_name"] == "My Spread"  # typed by the user, kept
    assert data["brands"] == "Ferrero"          # blank, filled by the API


def test_add_item_still_works_when_api_is_down(client):
    with patch("app.openfoodfacts.fetch_by_barcode", side_effect=ExternalAPIError("down")):
        response = client.post(
            "/inventory",
            json={"barcode": "999", "product_name": "Manual", "price": 1, "stock": 1},
        )
    assert response.status_code == 201
    assert response.get_json()["product_name"] == "Manual"


def test_add_item_without_name_and_unknown_barcode_fails(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=None):
        response = client.post("/inventory", json={"barcode": "000", "price": 1, "stock": 1})
    assert response.status_code == 400


def test_add_item_missing_price_and_stock(client):
    response = client.post("/inventory", json={"product_name": "X"})
    assert response.status_code == 400
    assert "price" in response.get_json()["error"]


def test_add_item_rejects_negative_price(client):
    response = client.post("/inventory", json={"product_name": "X", "price": -1, "stock": 1})
    assert response.status_code == 400


def test_add_item_rejects_non_integer_stock(client):
    response = client.post("/inventory", json={"product_name": "X", "price": 1, "stock": 2.5})
    assert response.status_code == 400


def test_add_item_without_body(client):
    response = client.post("/inventory")
    assert response.status_code == 400


# ---------- PATCH ----------

def test_update_item(client):
    response = client.patch("/inventory/1", json={"price": 9.99, "stock": 3})
    assert response.status_code == 200
    data = response.get_json()
    assert data["price"] == 9.99
    assert data["stock"] == 3
    assert data["product_name"] == "Cola"  # untouched fields stay


def test_update_ignores_unknown_fields(client):
    response = client.patch("/inventory/1", json={"id": 500, "price": 2})
    assert response.get_json()["id"] == 1


def test_update_rejects_invalid_values(client):
    response = client.patch("/inventory/1", json={"stock": -5})
    assert response.status_code == 400


def test_update_missing_item_returns_404(client):
    response = client.patch("/inventory/99", json={"price": 1})
    assert response.status_code == 404


# ---------- DELETE ----------

def test_delete_item(client):
    response = client.delete("/inventory/1")
    assert response.status_code == 200
    assert client.get("/inventory/1").status_code == 404
    assert len(app_module.inventory) == 1


def test_delete_missing_item_returns_404(client):
    response = client.delete("/inventory/99")
    assert response.status_code == 404


# ---------- LOOKUP ----------

def test_lookup_by_barcode(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=FAKE_PRODUCT):
        response = client.get("/lookup?barcode=999")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Nutella"


def test_lookup_barcode_not_found(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=None):
        response = client.get("/lookup?barcode=000")
    assert response.status_code == 404


def test_lookup_by_name(client):
    with patch("app.openfoodfacts.search_by_name", return_value=[FAKE_PRODUCT]):
        response = client.get("/lookup?name=nutella")
    assert response.status_code == 200
    assert response.get_json()["results"] == [FAKE_PRODUCT]


def test_lookup_needs_a_parameter(client):
    response = client.get("/lookup")
    assert response.status_code == 400


def test_lookup_api_failure_returns_502(client):
    with patch("app.openfoodfacts.fetch_by_barcode", side_effect=ExternalAPIError("down")):
        response = client.get("/lookup?barcode=999")
    assert response.status_code == 502
