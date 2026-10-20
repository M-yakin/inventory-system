from unittest.mock import Mock, patch

import pytest
import requests

import openfoodfacts


def fake_response(json_data=None, status=200):
    """Build a stand-in for a requests.Response."""
    response = Mock()
    response.status_code = status
    response.json.return_value = json_data
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status} error")
    return response


def test_fetch_by_barcode_found():
    payload = {
        "status": 1,
        "product": {
            "code": "123",
            "product_name": "Organic Almond Milk",
            "brands": "Silk",
            "ingredients_text": "water, almonds",
            "some_other_field": "ignored",
        },
    }
    with patch("openfoodfacts.requests.get", return_value=fake_response(payload)) as mock_get:
        result = openfoodfacts.fetch_by_barcode("123")

    assert result == {
        "barcode": "123",
        "product_name": "Organic Almond Milk",
        "brands": "Silk",
        "ingredients_text": "water, almonds",
    }
    assert "User-Agent" in mock_get.call_args.kwargs["headers"]


def test_fetch_by_barcode_not_found_status_zero():
    with patch("openfoodfacts.requests.get", return_value=fake_response({"status": 0})):
        assert openfoodfacts.fetch_by_barcode("000") is None


def test_fetch_by_barcode_http_404_returns_none():
    with patch("openfoodfacts.requests.get", return_value=fake_response({}, status=404)):
        assert openfoodfacts.fetch_by_barcode("000") is None


def test_fetch_by_barcode_network_error():
    with patch("openfoodfacts.requests.get", side_effect=requests.ConnectionError("no network")):
        with pytest.raises(openfoodfacts.ExternalAPIError):
            openfoodfacts.fetch_by_barcode("123")


def test_fetch_by_barcode_server_error():
    with patch("openfoodfacts.requests.get", return_value=fake_response({}, status=403)):
        with pytest.raises(openfoodfacts.ExternalAPIError):
            openfoodfacts.fetch_by_barcode("123")


def test_fetch_by_barcode_invalid_json():
    bad = fake_response()
    bad.json.side_effect = ValueError("not json")
    with patch("openfoodfacts.requests.get", return_value=bad):
        with pytest.raises(openfoodfacts.ExternalAPIError):
            openfoodfacts.fetch_by_barcode("123")


def test_search_by_name_returns_cleaned_list():
    payload = {
        "products": [
            {"code": "1", "product_name": "A", "brands": "B", "ingredients_text": "x", "extra": "ignored"},
            {"code": "2", "product_name": "C"},  # missing fields get defaults
        ]
    }
    with patch("openfoodfacts.requests.get", return_value=fake_response(payload)) as mock_get:
        results = openfoodfacts.search_by_name("nutella", limit=2)

    assert results[0] == {"barcode": "1", "product_name": "A", "brands": "B", "ingredients_text": "x"}
    assert results[1]["brands"] == ""
    assert mock_get.call_args.kwargs["params"]["search_terms"] == "nutella"
    assert mock_get.call_args.kwargs["params"]["page_size"] == 2


def test_search_by_name_no_results():
    with patch("openfoodfacts.requests.get", return_value=fake_response({"products": []})):
        assert openfoodfacts.search_by_name("zzzzzz") == []


def test_search_by_name_network_error():
    with patch("openfoodfacts.requests.get", side_effect=requests.Timeout("slow")):
        with pytest.raises(openfoodfacts.ExternalAPIError):
            openfoodfacts.search_by_name("nutella")
