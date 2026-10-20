from flask import Flask, jsonify, request

import openfoodfacts

app = Flask(__name__)

# Simulated database: a list of dicts shaped like OpenFoodFacts data
# plus our own fields (id, price, stock).
inventory = [
    {
        "id": 1,
        "barcode": "5449000000996",
        "product_name": "Coca-Cola",
        "brands": "Coca-Cola",
        "ingredients_text": "Carbonated water, sugar, colour (caramel E150d), acid (phosphoric acid), flavourings",
        "price": 1.50,
        "stock": 40,
    },
    {
        "id": 2,
        "barcode": "3017620422003",
        "product_name": "Nutella",
        "brands": "Ferrero",
        "ingredients_text": "Sugar, palm oil, hazelnuts, skimmed milk powder, cocoa",
        "price": 4.25,
        "stock": 15,
    },
    {
        "id": 3,
        "barcode": "7622210449283",
        "product_name": "Oreo Original",
        "brands": "Oreo",
        "ingredients_text": "Wheat flour, sugar, palm oil, cocoa, glucose-fructose syrup",
        "price": 2.10,
        "stock": 60,
    },
]

# Fields a client is allowed to set or change
EDITABLE_FIELDS = {"barcode", "product_name", "brands", "ingredients_text", "price", "stock"}
# Fields we can fill in from OpenFoodFacts
API_FIELDS = ("product_name", "brands", "ingredients_text")


def find_item(item_id):
    """Return the item with this id, or None."""
    return next((item for item in inventory if item["id"] == item_id), None)


def next_id():
    """Next free id (max + 1, so ids are never reused after a delete)."""
    return max((item["id"] for item in inventory), default=0) + 1


def validate_numbers(data):
    """Return an error message if price/stock are invalid, else None."""
    if "price" in data:
        if not isinstance(data["price"], (int, float)) or data["price"] < 0:
            return "price must be a non-negative number"
    if "stock" in data:
        if not isinstance(data["stock"], int) or data["stock"] < 0:
            return "stock must be a non-negative integer"
    return None


@app.route("/inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory), 200


@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item), 200


@app.route("/inventory", methods=["POST"])
def add_item():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    missing = [f for f in ("price", "stock") if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    error = validate_numbers(data)
    if error:
        return jsonify({"error": error}), 400

    barcode = str(data.get("barcode", "")).strip()
    if barcode and not barcode.isdigit():
        return jsonify({"error": "barcode must contain digits only"}), 400

    item = {"id": next_id()}
    for field in EDITABLE_FIELDS:
        item[field] = data.get(field, "")

    # Enrich with OpenFoodFacts data when a barcode is given.
    # Values the user typed always win; the API only fills the blanks.
    if item["barcode"]:
        try:
            product = openfoodfacts.fetch_by_barcode(item["barcode"])
        except openfoodfacts.ExternalAPIError:
            product = None  # API down: carry on with what the user gave us
        if product:
            for field in API_FIELDS:
                if not item[field]:
                    item[field] = product[field]

    if not item["product_name"]:
        return jsonify({"error": "product_name is required (or give a barcode that exists on OpenFoodFacts)"}), 400

    inventory.append(item)
    return jsonify(item), 201


@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    error = validate_numbers(data)
    if error:
        return jsonify({"error": error}), 400

    for field, value in data.items():
        if field in EDITABLE_FIELDS:
            item[field] = value

    return jsonify(item), 200


@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    inventory.remove(item)
    return jsonify({"message": f"Item {item_id} deleted"}), 200


@app.route("/lookup", methods=["GET"])
def lookup():
    """Search OpenFoodFacts by ?barcode= or ?name=."""
    barcode = request.args.get("barcode", "").strip()
    name = request.args.get("name", "").strip()

    if not barcode and not name:
        return jsonify({"error": "Provide a 'barcode' or 'name' query parameter"}), 400

    try:
        if barcode:
            product = openfoodfacts.fetch_by_barcode(barcode)
            if product is None:
                return jsonify({"error": "Product not found on OpenFoodFacts"}), 404
            return jsonify(product), 200

        results = openfoodfacts.search_by_name(name)
        return jsonify({"results": results}), 200
    except openfoodfacts.ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502  # 502 = bad gateway (upstream failed)


if __name__ == "__main__":
    app.run(debug=True)
