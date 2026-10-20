from unittest.mock import Mock, patch

import requests

import cli

ITEM = {
    "id": 1, "barcode": "111", "product_name": "Cola", "brands": "BrandA",
    "ingredients_text": "water, sugar", "price": 1.5, "stock": 10,
}


def feed(monkeypatch, *answers):
    """Make input() return the given answers one after another."""
    answers_iter = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers_iter))


# ---------- api_request error handling ----------

def test_api_request_connection_error(capsys):
    with patch("cli.requests.request", side_effect=requests.ConnectionError()):
        assert cli.api_request("GET", "/inventory") is None
    assert "cannot reach the API" in capsys.readouterr().out


def test_api_request_timeout(capsys):
    with patch("cli.requests.request", side_effect=requests.Timeout()):
        assert cli.api_request("GET", "/inventory") is None
    assert "too long" in capsys.readouterr().out


def test_api_request_error_response(capsys):
    response = Mock(ok=False, status_code=404)
    response.json.return_value = {"error": "Item not found"}
    with patch("cli.requests.request", return_value=response):
        assert cli.api_request("GET", "/inventory/99") is None
    assert "Item not found" in capsys.readouterr().out


def test_api_request_success():
    response = Mock(ok=True, status_code=200)
    response.json.return_value = [ITEM]
    with patch("cli.requests.request", return_value=response):
        assert cli.api_request("GET", "/inventory") == [ITEM]


# ---------- input helpers ----------

def test_ask_int_retries_until_valid(monkeypatch):
    feed(monkeypatch, "abc", "-1", "7")
    assert cli.ask_int("n: ") == 7


def test_ask_float_retries_until_valid(monkeypatch):
    feed(monkeypatch, "cheap", "2.5")
    assert cli.ask_float("p: ") == 2.5


def test_ask_int_blank_allowed(monkeypatch):
    feed(monkeypatch, "")
    assert cli.ask_int("n: ", allow_blank=True) is None


# ---------- commands ----------

def test_view_all_prints_items(capsys):
    with patch("cli.api_request", return_value=[ITEM]):
        cli.view_all()
    output = capsys.readouterr().out
    assert "Cola" in output
    assert "1.5" in output


def test_view_all_empty(capsys):
    with patch("cli.api_request", return_value=[]):
        cli.view_all()
    assert "empty" in capsys.readouterr().out.lower()


def test_view_item_calls_correct_route(monkeypatch):
    feed(monkeypatch, "1")
    with patch("cli.api_request", return_value=ITEM) as mock_api:
        cli.view_item()
    mock_api.assert_called_once_with("GET", "/inventory/1")


def test_add_item_sends_payload(monkeypatch):
    # barcode, name (blank), price, stock
    feed(monkeypatch, "3017620422003", "", "5", "10")
    with patch("cli.api_request", return_value=ITEM) as mock_api:
        cli.add_item()
    mock_api.assert_called_once_with(
        "POST", "/inventory",
        json={"price": 5.0, "stock": 10, "barcode": "3017620422003"},
    )


def test_update_item_only_sends_changed_fields(monkeypatch):
    feed(monkeypatch, "4", "6.5", "")  # id, new price, stock left blank
    with patch("cli.api_request", return_value=ITEM) as mock_api:
        cli.update_item()
    mock_api.assert_called_once_with("PATCH", "/inventory/4", json={"price": 6.5})


def test_update_item_with_nothing_to_change(monkeypatch, capsys):
    feed(monkeypatch, "4", "", "")
    with patch("cli.api_request") as mock_api:
        cli.update_item()
    mock_api.assert_not_called()
    assert "Nothing to update" in capsys.readouterr().out


def test_delete_item_confirmed(monkeypatch):
    feed(monkeypatch, "2", "y")
    with patch("cli.api_request", return_value={"message": "Item 2 deleted"}) as mock_api:
        cli.delete_item()
    mock_api.assert_called_once_with("DELETE", "/inventory/2")


def test_delete_item_cancelled(monkeypatch):
    feed(monkeypatch, "2", "n")
    with patch("cli.api_request") as mock_api:
        cli.delete_item()
    mock_api.assert_not_called()


def test_find_on_api_by_barcode(monkeypatch):
    product = {"barcode": "123", "product_name": "Nutella", "brands": "Ferrero",
               "ingredients_text": "sugar"}
    feed(monkeypatch, "b", "123", "n")  # barcode mode, the barcode, don't add
    with patch("cli.api_request", return_value=product) as mock_api:
        cli.find_on_api()
    mock_api.assert_called_once_with("GET", "/lookup", params={"barcode": "123"})


def test_find_on_api_rejects_bad_choice(monkeypatch, capsys):
    feed(monkeypatch, "x")
    with patch("cli.api_request") as mock_api:
        cli.find_on_api()
    mock_api.assert_not_called()
    assert "'b' or 'n'" in capsys.readouterr().out
