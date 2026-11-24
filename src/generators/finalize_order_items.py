"""
Warehouse Logistics Data Generator - finalize order items

orders.py creates every order item in its START state
(picked/packed/shipped quantity 0, status NOT_STARTED). Picking,
packing and shipping then process the orders, but they never go back
to order_items.csv, so the file would claim that nothing happened.

This step runs AFTER shipping.py and writes the real result:

    picked_quantity  = sum of the picks of the item (picking.csv)
    packed_quantity  = picked_quantity   (packing is per order, all complete)
    shipped_quantity = picked_quantity   (every order has a shipment)
    item_status      = DELIVERED

It refuses to continue when the files disagree (a pick total different
from the requested quantity, or an order without a shipment), so an
inconsistent dataset can never be "finalized".
"""

import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = Path(
    os.environ.get("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed")
)

ORDER_ITEMS_FILE = PROCESSED_DIR / "order_items.csv"
PICKING_FILE = PROCESSED_DIR / "picking.csv"
SHIPPING_FILE = PROCESSED_DIR / "shipping.csv"

FINAL_ITEM_STATUS = "DELIVERED"


def read_rows(path):
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames, list(reader)


def main():
    print()
    print("Finalizing order items")
    print("======================")

    fieldnames, items = read_rows(ORDER_ITEMS_FILE)
    _, picks = read_rows(PICKING_FILE)
    _, shipments = read_rows(SHIPPING_FILE)

    picked_by_item = {}

    for pick in picks:
        item_id = pick["order_item_id"]
        picked_by_item[item_id] = (
            picked_by_item.get(item_id, 0) + int(float(pick["picked_quantity"]))
        )

    delivered_orders = {
        row["order_id"]
        for row in shipments
        if row["shipment_status"] == "DELIVERED"
    }

    for item in items:
        item_id = item["order_item_id"]
        requested = int(float(item["requested_quantity"]))
        picked = picked_by_item.get(item_id, 0)

        if picked != requested:
            raise ValueError(
                f"{item_id}: picked {picked} but requested {requested}. "
                "Fix picking.py before finalizing."
            )

        if item["order_id"] not in delivered_orders:
            raise ValueError(
                f"{item_id}: order {item['order_id']} has no delivered shipment."
            )

        item["picked_quantity"] = picked
        item["packed_quantity"] = picked
        item["shipped_quantity"] = picked
        item["item_status"] = FINAL_ITEM_STATUS

    with ORDER_ITEMS_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(items)

    print(f"Order items updated: {len(items):,}")
    print(f"Total quantity:      {sum(picked_by_item.values()):,}")
    print(f"Item status:         {FINAL_ITEM_STATUS}")
    print()
    print("Order item finalization completed successfully.")


if __name__ == "__main__":
    main()
