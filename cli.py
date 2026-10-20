import requests

API_URL = "http://127.0.0.1:5000"
TIMEOUT = 15  # seconds


# ---------- talking to the API ----------

def api_request(method, path, **kwargs):
    """Call the Flask API. Return the parsed JSON, or None after printing an error."""
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=TIMEOUT, **kwargs)
    except requests.Timeout:
        print("Error: the API took too long to respond.")
        return None
    except requests.ConnectionError:
        print("Error: cannot reach the API. Is 'python app.py' running?")
        return None
    except requests.RequestException as exc:
        print(f"Error: request failed ({exc})")
        return None

    try:
        data = response.json()
    except ValueError:
        print(f"Error: unexpected response from the API (status {response.status_code}).")
        return None

    if not response.ok:
        print(f"Error: {data.get('error', 'Unknown error')}")
        return None
    return data


# ---------- input helpers ----------

def ask_int(label, allow_blank=False):
    """Keep asking until the user types a whole number >= 0 (or blank, if allowed)."""
    while True:
        raw = input(label).strip()
        if raw == "" and allow_blank:
            return None
        try:
            value = int(raw)
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            print("Please enter a whole number (0 or more).")


def ask_float(label, allow_blank=False):
    """Keep asking until the user types a number >= 0 (or blank, if allowed)."""
    while True:
        raw = input(label).strip()
        if raw == "" and allow_blank:
            return None
        try:
            value = float(raw)
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            print("Please enter a valid price (0 or more).")


def confirm(label):
    return input(label).strip().lower() in ("y", "yes")


# ---------- display ----------

def print_item(item):
    print(f"  ID:          {item['id']}")
    print(f"  Name:        {item['product_name']}")
    print(f"  Brand:       {item['brands']}")
    print(f"  Barcode:     {item['barcode']}")
    print(f"  Price:       {item['price']}")
    print(f"  Stock:       {item['stock']}")
    print(f"  Ingredients: {item['ingredients_text']}")


def print_product(product):
    print(f"  Name:        {product['product_name']}")
    print(f"  Brand:       {product['brands']}")
    print(f"  Barcode:     {product['barcode']}")
    print(f"  Ingredients: {product['ingredients_text']}")


# ---------- commands ----------

def view_all():
    items = api_request("GET", "/inventory")
    if items is None:
        return
    if not items:
        print("Inventory is empty.")
        return
    print(f"\n{'ID':<4} {'Name':<30} {'Price':>8} {'Stock':>6}")
    print("-" * 51)
    for item in items:
        print(f"{item['id']:<4} {item['product_name'][:30]:<30} {item['price']:>8} {item['stock']:>6}")


def view_item():
    item_id = ask_int("Item ID: ")
    item = api_request("GET", f"/inventory/{item_id}")
    if item:
        print()
        print_item(item)


def add_item():
    print("Leave barcode blank to enter details by hand.")
    barcode = input("Barcode (optional): ").strip()
    name = input("Product name (optional if barcode is on OpenFoodFacts): ").strip()
    price = ask_float("Price: ")
    stock = ask_int("Stock: ")

    payload = {"price": price, "stock": stock}
    if barcode:
        payload["barcode"] = barcode
    if name:
        payload["product_name"] = name

    item = api_request("POST", "/inventory", json=payload)
    if item:
        print("\nItem added:")
        print_item(item)


def update_item():
    item_id = ask_int("Item ID to update: ")
    print("Leave a field blank to keep its current value.")
    price = ask_float("New price: ", allow_blank=True)
    stock = ask_int("New stock: ", allow_blank=True)

    payload = {}
    if price is not None:
        payload["price"] = price
    if stock is not None:
        payload["stock"] = stock
    if not payload:
        print("Nothing to update.")
        return

    item = api_request("PATCH", f"/inventory/{item_id}", json=payload)
    if item:
        print("\nItem updated:")
        print_item(item)


def delete_item():
    item_id = ask_int("Item ID to delete: ")
    if not confirm(f"Delete item {item_id}? (y/n): "):
        print("Cancelled.")
        return
    result = api_request("DELETE", f"/inventory/{item_id}")
    if result:
        print(result["message"])


def add_from_product(product):
    """Offer to add a product found on OpenFoodFacts to the inventory."""
    if not confirm("Add this product to inventory? (y/n): "):
        return
    price = ask_float("Price: ")
    stock = ask_int("Stock: ")
    payload = {
        "barcode": product["barcode"],
        "product_name": product["product_name"],
        "brands": product["brands"],
        "ingredients_text": product["ingredients_text"],
        "price": price,
        "stock": stock,
    }
    item = api_request("POST", "/inventory", json=payload)
    if item:
        print("\nItem added:")
        print_item(item)


def find_on_api():
    choice = input("Search by (b)arcode or (n)ame? ").strip().lower()

    if choice.startswith("b"):
        barcode = input("Barcode: ").strip()
        if not barcode:
            print("Barcode cannot be empty.")
            return
        product = api_request("GET", "/lookup", params={"barcode": barcode})
        if product:
            print()
            print_product(product)
            add_from_product(product)

    elif choice.startswith("n"):
        name = input("Product name: ").strip()
        if not name:
            print("Name cannot be empty.")
            return
        data = api_request("GET", "/lookup", params={"name": name})
        if data is None:
            return
        results = data["results"]
        if not results:
            print("No products found.")
            return
        for number, product in enumerate(results, start=1):
            print(f"\n[{number}]")
            print_product(product)
        pick = input("\nNumber to add to inventory (blank to skip): ").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(results):
            add_from_product(results[int(pick) - 1])

    else:
        print("Please type 'b' or 'n'.")


# ---------- menu ----------

MENU = """
===== Inventory Manager =====
1. View all items
2. View item details
3. Add item
4. Update price / stock
5. Delete item
6. Find item on OpenFoodFacts
7. Exit
"""

ACTIONS = {
    "1": view_all,
    "2": view_item,
    "3": add_item,
    "4": update_item,
    "5": delete_item,
    "6": find_on_api,
}


def main():
    while True:
        print(MENU)
        choice = input("Choose an option (1-7): ").strip()
        if choice == "7":
            print("Goodbye!")
            break
        action = ACTIONS.get(choice)
        if action is None:
            print("Invalid choice. Please enter a number from 1 to 7.")
            continue
        try:
            action()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")


if __name__ == "__main__":
    main()
