# Inventory Management System

A small retail inventory tool made of three parts:

- A **Flask REST API** with CRUD operations on an in-memory inventory list
- An **OpenFoodFacts integration** that fetches product details by barcode or name
- A **menu-driven CLI** that talks to the API
- **pytest** unit tests that mock the external API

Data is stored in a Python list while the server runs, so it resets whenever the server restarts.

## Project structure

```
inventory-system/
├── app.py             # Flask API
├── cli.py             # CLI frontend
├── openfoodfacts.py   # OpenFoodFacts helper
├── pytest.ini
├── requirements.txt
├── tests/
│   ├── test_api.py
│   ├── test_cli.py
│   └── test_external.py
└── README.md
```

## Installation and setup

```bash
git clone https://github.com/M-yakin/inventory-system.git
cd inventory-system
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running the app

Use two terminals, both with the virtual environment activated.

Terminal 1, the API:

```bash
python app.py
```

Terminal 2, the CLI:

```bash
python cli.py
```

The API runs at `http://127.0.0.1:5000`. The CLI needs the API running.

## API endpoints

| Method | Endpoint | Description | Success | Errors |
|---|---|---|---|---|
| GET | `/inventory` | List all items | 200 | |
| GET | `/inventory/<id>` | Get one item | 200 | 404 |
| POST | `/inventory` | Add an item | 201 | 400 |
| PATCH | `/inventory/<id>` | Update an item | 200 | 400, 404 |
| DELETE | `/inventory/<id>` | Delete an item | 200 | 404 |
| GET | `/lookup?barcode=...` | Look up a product on OpenFoodFacts | 200 | 400, 404, 502 |
| GET | `/lookup?name=...` | Search OpenFoodFacts by name (up to 5 results) | 200 | 400, 502 |

### Item format

```json
{
  "id": 1,
  "barcode": "3017620422003",
  "product_name": "Nutella",
  "brands": "Ferrero",
  "ingredients_text": "Sugar, palm oil, ...",
  "price": 4.25,
  "stock": 15
}
```

### POST /inventory

`price` and `stock` are required. If you send a `barcode`, any of `product_name`, `brands` and `ingredients_text` you leave blank are filled in from OpenFoodFacts. Values you send always take priority. If OpenFoodFacts is unreachable, the item is still created from what you sent, as long as it has a `product_name`.

```bash
curl -X POST http://127.0.0.1:5000/inventory \
  -H "Content-Type: application/json" \
  -d '{"barcode":"3017620422003","price":5.0,"stock":10}'
```

### PATCH /inventory/<id>

Send only the fields to change. `price` must be a non-negative number and `stock` a non-negative integer.

```bash
curl -X PATCH http://127.0.0.1:5000/inventory/1 \
  -H "Content-Type: application/json" \
  -d '{"price":6.5,"stock":8}'
```

### Error format

```json
{"error": "Item not found"}
```

## CLI usage

```
===== Inventory Manager =====
1. View all items
2. View item details
3. Add item
4. Update price / stock
5. Delete item
6. Find item on OpenFoodFacts
7. Exit
```

Example session:

```
Choose an option (1-7): 3
Barcode (optional): 3017620422003
Product name (optional if barcode is on OpenFoodFacts):
Price: 5
Stock: 10

Item added:
  ID:          4
  Name:        Nutella
  Brand:       Nutella, Ferrero
  ...
```

- **Update**: leave a field blank to keep its current value.
- **Delete**: asks for confirmation first.
- **Find on OpenFoodFacts**: search by barcode or by name, then optionally add the result to the inventory.
- Invalid numbers are re-prompted. A stopped or unreachable API prints a clear message instead of crashing.

## Running the tests

```bash
pytest -v
```

The tests use `unittest.mock` to simulate OpenFoodFacts, so they run offline and don't need the server running.

## Data source

Product data comes from the [OpenFoodFacts API](https://openfoodfacts.github.io/openfoodfacts-server/api/). Requests identify themselves with a `User-Agent` header, which OpenFoodFacts requires.

## Manual API testing

All five CRUD routes and the `/lookup` route were validated with Postman and `curl`
while running Flask in debug mode (`debug=True`), in addition to the automated pytest suite.
