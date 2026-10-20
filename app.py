from flask import Flask, jsonify, request

app = Flask(__name__)


# Simulated database: a list of dicts shaped like OpenFoodFacts data
# plus our own fields (id, price, stock).
inventory = [
    {
        "id": 1,
        "barcode": "5449000000000",
        "product_name": "Nutella",
        "brands": "Nutella",
        "ingredients_text": "Sugar, Palm Oil, Hazelnuts, Cocoa, Skimmed Milk Powder, Whey Powder, Emulsifier: Lecithins (Soya), Vanillin",
        "price": 3.99,
        "stock": 10   
    },
    {
        "id": 2,
        "barcode": "5000159484695",
        "product_name": "Cadbury Dairy Milk",
        "brands": "Cadbury",
        "ingredients_text": "Milk Chocolate (Sugar, Cocoa Butter, Cocoa Mass, Skimmed Milk Powder, Milk Fat, Emulsifier: E442, Flavouring), Vegetable Fats (Palm, Shea), Sugar, Cocoa Mass, Whey Powder (Milk), Emulsifier: E476, Flavouring",
        "price": 2.49,
        "stock": 20
    },
    {
        "id": 3,
        "barcode": "7622210449283",
        "product_name": "Lindt Excellence 70% Cocoa",
        "brands": "Lindt",
        "ingredients_text": "Cocoa Mass, Sugar, Cocoa Butter, Emulsifier (Soy Lecithin), Natural Vanilla Extract",
        "price": 4.99,
        "stock": 15
    },
]

# Fields a client is allowed to set or change
EDITABLE_FIELDS = {"barcode", "product_name", "brands", "ingredients_text", "price", "stock"}

def find_item(item_id):
    """Return the item with this id, or None if not found."""
    return next((item for item in inventory if item["id"] == item_id), None)

def next_id():
    """Next free id (max + 1, so ids are never reused even if items are deleted)."""
    return max((item["id"] for item in inventory), default=0) + 1

def validate_numbers(data):
    """Return an error message if price or stock are invalid, else None."""
    if "price" in data:
        if not isinstance(data["price"], (int, float)) or data["price"] < 0:
            return "Price must be a non-negative number."
    if "stock" in data:
        if not isinstance(data["stock"], int) or data["stock"] < 0:
            return "Stock must be a non-negative integer."
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

    missing = [f for f in ["barcode", "product_name", "brands", "ingredients_text", "price", "stock"] if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    error = validate_numbers(data)
    if error:
        return jsonify({"error": error}), 400

    item = {"id": next_id()}
    for field in EDITABLE_FIELDS:
        item[field] = data.get(field,"")
    item["price"] = data["price"]
    item["stock"] = data["stock"]

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

    for field in EDITABLE_FIELDS:
        if field in data:
            item[field] = data[field]

    return jsonify(item), 200

@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if item is None:
        return jsonify({"error": "Item not found"}), 404

    inventory.remove(item)
    return jsonify({"message": "Item deleted"}), 200

if __name__ == "__main__":
    app.run(debug=True)