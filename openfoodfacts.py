import requests

BASE_URL = "https://world.openfoodfacts.org"
# OpenFoodFacts requires every client to identify itself: AppName/Version (contact)
HEADERS = {"User-Agent": "InventoryManager/1.0 (yakin-student-project@example.com)"}
TIMEOUT = 10  # seconds


class ExternalAPIError(Exception):
    """Raised when OpenFoodFacts is unreachable or returns bad data."""


def _clean(product, barcode=""):
    """Keep only the fields we store in our inventory."""
    return {
        "barcode": product.get("code") or barcode,
        "product_name": product.get("product_name", ""),
        "brands": product.get("brands", ""),
        "ingredients_text": product.get("ingredients_text", ""),
    }


def fetch_by_barcode(barcode):
    """Return a cleaned product dict, or None if the barcode isn't found."""
    url = f"{BASE_URL}/api/v2/product/{barcode}.json"
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code == 404:
            return None  # OpenFoodFacts answers 404 for unknown barcodes
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalAPIError(f"Could not reach OpenFoodFacts: {exc}") from exc

    if data.get("status") != 1:
        return None
    return _clean(data.get("product", {}), barcode)


def search_by_name(name, limit=5):
    """Return a list of cleaned product dicts matching the name (may be empty)."""
    url = f"{BASE_URL}/cgi/search.pl"
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
    }
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExternalAPIError(f"Could not reach OpenFoodFacts: {exc}") from exc

    return [_clean(p) for p in data.get("products", [])]
