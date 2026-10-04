"""
Warehouse Control Tower - Full Pipeline Validation

Validates the complete synthetic operational data flow:

Product -> Location -> Inventory -> Order -> Order Item
       -> Picking -> Packing -> Shipping -> Delivery

This script validates referential integrity, quantities, timestamps,
packing rules, shipping rules, and delivery performance.

It does not modify any input files.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRODUCTS_FILE = PROCESSED_DIR / "product_master.csv"
LOCATIONS_FILE = PROCESSED_DIR / "locations.csv"
INVENTORY_FILE = PROCESSED_DIR / "inventory.csv"
ORDERS_FILE = PROCESSED_DIR / "orders.csv"
ORDER_ITEMS_FILE = PROCESSED_DIR / "order_items.csv"
PICKING_FILE = PROCESSED_DIR / "picking.csv"
PACKING_FILE = PROCESSED_DIR / "packing.csv"
SHIPPING_FILE = PROCESSED_DIR / "shipping.csv"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def require_columns(
    rows: list[dict],
    required: set[str],
    name: str,
) -> None:
    if not rows:
        raise AssertionError(f"{name} is empty.")

    missing = required - set(rows[0])
    assert not missing, (
        f"{name} missing columns: {missing}"
    )


def unique_ids(
    rows: list[dict],
    column: str,
    name: str,
) -> set[str]:
    values = [row[column] for row in rows]

    assert len(values) == len(set(values)), (
        f"Duplicate {column} values in {name}."
    )

    return set(values)


def validate_products(products: list[dict]) -> None:
    require_columns(
        products,
        {"product_id", "article_number"},
        "Products",
    )

    product_ids = unique_ids(
        products,
        "product_id",
        "Products",
    )

    article_numbers = [
        row["article_number"]
        for row in products
        if row["article_number"].strip()
    ]

    assert len(article_numbers) == len(set(article_numbers)), (
        "Duplicate article numbers in product master."
    )

    assert len(product_ids) > 0


def validate_locations(locations: list[dict]) -> None:
    require_columns(
        locations,
        {
            "location_id",
            "hall_id",
            "zone_nr",
            "storage_type",
            "picking_method",
            "position",
            "level",
            "side",
        },
        "Locations",
    )

    location_ids = unique_ids(
        locations,
        "location_id",
        "Locations",
    )

    assert len(location_ids) == len(locations)

    for row in locations:
        assert row["storage_type"] in {
            "PALLET_STORAGE",
            "BOX_STORAGE",
        }

        assert row["picking_method"] in {
            "FORKLIFT",
            "PICKING_CART",
            "VERTICAL_LIFT",
            "STAPLER",
        }


def validate_inventory(
    inventory: list[dict],
    products: list[dict],
    locations: list[dict],
) -> None:
    require_columns(
        inventory,
        {
            "inventory_id",
            "product_id",
            "location_id",
            "quantity",
            "container_type",
            "status",
        },
        "Inventory",
    )

    product_ids = {
        row["product_id"]
        for row in products
    }

    location_ids = {
        row["location_id"]
        for row in locations
    }

    unique_ids(
        inventory,
        "inventory_id",
        "Inventory",
    )

    for row in inventory:
        assert row["product_id"] in product_ids, (
            f"Inventory references unknown product "
            f"{row['product_id']}"
        )

        assert row["location_id"] in location_ids, (
            f"Inventory references unknown location "
            f"{row['location_id']}"
        )

        assert int(float(row["quantity"])) > 0


def validate_orders(
    orders: list[dict],
    order_items: list[dict],
) -> None:
    require_columns(
        orders,
        {
            "order_id",
            "order_datetime",
            "requested_delivery_datetime",
            "delivery_priority",
            "total_items",
            "total_weight_kg",
        },
        "Orders",
    )

    require_columns(
        order_items,
        {
            "order_item_id",
            "order_id",
            "product_id",
            "requested_quantity",
        },
        "Order Items",
    )

    order_ids = unique_ids(
        orders,
        "order_id",
        "Orders",
    )

    unique_ids(
        order_items,
        "order_item_id",
        "Order Items",
    )

    product_ids = {
        row["product_id"]
        for row in products_global
    }

    for order in orders:
        order_datetime = parse_datetime(
            order["order_datetime"]
        )

        delivery_datetime = parse_datetime(
            order["requested_delivery_datetime"]
        )

        assert delivery_datetime > order_datetime, (
            f"Invalid delivery deadline for "
            f"{order['order_id']}"
        )

        assert int(float(order["total_items"])) > 0
        assert float(order["total_weight_kg"]) > 0

    item_counts = defaultdict(int)

    for item in order_items:
        assert item["order_id"] in order_ids, (
            f"Order item references unknown order "
            f"{item['order_id']}"
        )

        assert item["product_id"] in product_ids, (
            f"Order item references unknown product "
            f"{item['product_id']}"
        )

        quantity = int(float(item["requested_quantity"]))

        assert quantity > 0

        item_counts[item["order_id"]] += 1

    assert set(item_counts) == order_ids, (
        "Some orders do not have order items."
    )


def validate_picking(
    orders: list[dict],
    order_items: list[dict],
    picking: list[dict],
) -> None:
    require_columns(
        picking,
        {
            "picking_id",
            "order_item_id",
            "order_id",
            "product_id",
            "inventory_id",
            "location_id",
            "picking_method",
            "container_type",
            "container_id",
            "location_scan",
            "container_scan",
            "pick_status",
            "pick_datetime",
            "picked_quantity",
        },
        "Picking",
    )

    order_ids = {
        row["order_id"]
        for row in orders
    }

    item_index = {
        row["order_item_id"]: row
        for row in order_items
    }

    inventory_index = {
        row["inventory_id"]: row
        for row in inventory_global
    }

    unique_ids(
        picking,
        "picking_id",
        "Picking",
    )

    picked_by_item = defaultdict(int)
    first_pick = {}
    last_pick = {}

    for row in picking:
        assert row["order_id"] in order_ids
        assert row["order_item_id"] in item_index
        assert row["inventory_id"] in inventory_index

        assert row["location_scan"].upper() == "TRUE"
        assert row["container_scan"].upper() == "TRUE"
        assert row["pick_status"] == "PICKED"

        quantity = int(float(row["picked_quantity"]))
        assert quantity > 0

        item_id = row["order_item_id"]
        picked_by_item[item_id] += quantity

        dt = parse_datetime(row["pick_datetime"])

        if item_id not in first_pick or dt < first_pick[item_id]:
            first_pick[item_id] = dt

        if item_id not in last_pick or dt > last_pick[item_id]:
            last_pick[item_id] = dt

    for item_id, item in item_index.items():
        assert picked_by_item.get(item_id, 0) == int(
            float(item["requested_quantity"])
        ), (
            f"Picked quantity mismatch for "
            f"{item_id}: expected "
            f"{item['requested_quantity']}, got "
            f"{picked_by_item.get(item_id, 0)}"
        )

    assert set(
        row["order_id"] for row in picking
    ) == order_ids


def validate_packing(
    orders: list[dict],
    order_items: list[dict],
    picking: list[dict],
    packing: list[dict],
) -> None:
    require_columns(
        packing,
        {
            "packing_id",
            "order_id",
            "packing_type",
            "packing_area",
            "packing_station",
            "container_id",
            "container_type",
            "container_count",
            "article_count",
            "total_quantity",
            "order_weight_kg",
            "container_scan",
            "order_complete",
            "packing_status",
            "packing_started_at",
            "packing_completed_at",
        },
        "Packing",
    )

    order_ids = {
        row["order_id"]
        for row in orders
    }

    picking_by_order = defaultdict(list)

    for row in picking:
        picking_by_order[row["order_id"]].append(row)

    packing_by_order = {
        row["order_id"]: row
        for row in packing
    }

    assert len(packing) == len(orders)
    assert set(packing_by_order) == order_ids

    unique_ids(
        packing,
        "packing_id",
        "Packing",
    )

    for order in orders:
        order_id = order["order_id"]
        row = packing_by_order[order_id]

        assert row["container_scan"].upper() == "TRUE"
        assert row["order_complete"].upper() == "TRUE"
        assert row["packing_status"] == "PACKED"

        article_count = int(
            row["article_count"]
        )

        weight = float(
            row["order_weight_kg"]
        )

        if article_count <= 4:
            assert row["packing_type"] == "SMALL_PACKAGE"
            assert row["packing_area"] == "KLEIN_PACKEN"

        elif weight <= 30:
            assert row["packing_type"] == "LARGE_PACKAGE"
            assert row["packing_area"] == "GROSS_PACKEN"

        else:
            assert row["packing_type"] == "PALLET_SHIPMENT"
            assert row["packing_area"] == "PALLET_PACKING"

        latest_pick = max(
            parse_datetime(
                pick["pick_datetime"]
            )
            for pick in picking_by_order[order_id]
        )

        packing_start = parse_datetime(
            row["packing_started_at"]
        )

        packing_end = parse_datetime(
            row["packing_completed_at"]
        )

        deadline = parse_datetime(
            order["requested_delivery_datetime"]
        )

        assert packing_start >= latest_pick
        assert packing_end > packing_start
        assert packing_end < deadline


def validate_shipping(
    orders: list[dict],
    packing: list[dict],
    shipping: list[dict],
) -> None:
    require_columns(
        shipping,
        {
            "shipment_id",
            "order_id",
            "packing_id",
            "shipping_method",
            "transport_mode",
            "vehicle_type",
            "carrier",
            "origin_country",
            "destination_country",
            "destination_region",
            "tracking_number",
            "shipment_status",
            "packing_completed_at",
            "shipped_at",
            "requested_delivery_datetime",
            "delivered_at",
            "transit_hours",
            "fulfillment_hours",
            "delivery_margin_hours",
            "on_time_delivery",
            "delivery_priority",
        },
        "Shipping",
    )

    order_ids = {
        row["order_id"]
        for row in orders
    }

    packing_ids = {
        row["packing_id"]
        for row in packing
    }

    unique_ids(
        shipping,
        "shipment_id",
        "Shipping",
    )

    tracking_numbers = unique_ids(
        shipping,
        "tracking_number",
        "Shipping",
    )

    assert len(tracking_numbers) == len(shipping)

    shipping_order_ids = {
        row["order_id"]
        for row in shipping
    }

    assert shipping_order_ids == order_ids
    assert len(shipping) == len(orders)

    order_index = {
        row["order_id"]: row
        for row in orders
    }

    for row in shipping:
        order_id = row["order_id"]

        assert row["packing_id"] in packing_ids

        packing_completed = parse_datetime(
            row["packing_completed_at"]
        )

        shipped_at = parse_datetime(
            row["shipped_at"]
        )

        delivered_at = parse_datetime(
            row["delivered_at"]
        )

        deadline = parse_datetime(
            order_index[order_id][
                "requested_delivery_datetime"
            ]
        )

        order_datetime = parse_datetime(
            order_index[order_id]["order_datetime"]
        )

        assert shipped_at > packing_completed
        assert delivered_at > shipped_at
        assert delivered_at > order_datetime

        expected_on_time = (
            delivered_at <= deadline
        )

        assert (
            row["on_time_delivery"].upper()
            == str(expected_on_time).upper()
        )

        assert row["origin_country"] == "Germany"

        assert row["transport_mode"] in {
            "ROAD",
            "AIR",
            "SEA",
        }

        assert row["vehicle_type"].strip()
        assert row["carrier"].strip()
        assert row["destination_country"].strip()
        assert row["destination_region"].strip()

        assert row["shipment_status"] == "DELIVERED"


def validate_cross_dataset_references(
    products: list[dict],
    locations: list[dict],
    inventory: list[dict],
    orders: list[dict],
    order_items: list[dict],
    picking: list[dict],
    packing: list[dict],
    shipping: list[dict],
) -> None:
    product_ids = {
        row["product_id"]
        for row in products
    }

    location_ids = {
        row["location_id"]
        for row in locations
    }

    inventory_ids = {
        row["inventory_id"]
        for row in inventory
    }

    order_ids = {
        row["order_id"]
        for row in orders
    }

    order_item_ids = {
        row["order_item_id"]
        for row in order_items
    }

    packing_ids = {
        row["packing_id"]
        for row in packing
    }

    for row in inventory:
        assert row["product_id"] in product_ids
        assert row["location_id"] in location_ids

    for row in order_items:
        assert row["order_id"] in order_ids
        assert row["product_id"] in product_ids

    for row in picking:
        assert row["order_id"] in order_ids
        assert row["order_item_id"] in order_item_ids
        assert row["product_id"] in product_ids
        assert row["inventory_id"] in inventory_ids
        assert row["location_id"] in location_ids

    for row in packing:
        assert row["order_id"] in order_ids

    for row in shipping:
        assert row["order_id"] in order_ids
        assert row["packing_id"] in packing_ids


def print_summary(
    products,
    locations,
    inventory,
    orders,
    order_items,
    picking,
    packing,
    shipping,
) -> None:
    on_time = sum(
        row["on_time_delivery"].upper() == "TRUE"
        for row in shipping
    )

    late = len(shipping) - on_time

    print()
    print("Warehouse Control Tower")
    print("Full Pipeline Validation")
    print("=========================")

    print()
    print("Dataset Counts")
    print("--------------")
    print(f"Products:       {len(products):,}")
    print(f"Locations:      {len(locations):,}")
    print(f"Inventory:      {len(inventory):,}")
    print(f"Orders:         {len(orders):,}")
    print(f"Order Items:    {len(order_items):,}")
    print(f"Picking:        {len(picking):,}")
    print(f"Packing:        {len(packing):,}")
    print(f"Shipping:       {len(shipping):,}")

    print()
    print("Delivery")
    print("--------")
    print(f"On-time:        {on_time:,}")
    print(f"Late:           {late:,}")
    print(
        f"On-time rate:   "
        f"{on_time / len(shipping) * 100:.2f}%"
    )

    print()
    print("Full pipeline validation passed.")


def main() -> None:
    print("Loading datasets...")

    products = read_csv(PRODUCTS_FILE)
    locations = read_csv(LOCATIONS_FILE)
    inventory = read_csv(INVENTORY_FILE)
    orders = read_csv(ORDERS_FILE)
    order_items = read_csv(ORDER_ITEMS_FILE)
    picking = read_csv(PICKING_FILE)
    packing = read_csv(PACKING_FILE)
    shipping = read_csv(SHIPPING_FILE)

    global products_global
    global inventory_global

    products_global = products
    inventory_global = inventory

    print("Datasets loaded.")
    print()

    print("Validating products...")
    validate_products(products)
    print("Products validation passed.")

    print("Validating locations...")
    validate_locations(locations)
    print("Locations validation passed.")

    print("Validating inventory...")
    validate_inventory(
        inventory,
        products,
        locations,
    )
    print("Inventory validation passed.")

    print("Validating orders...")
    validate_orders(
        orders,
        order_items,
    )
    print("Orders validation passed.")

    print("Validating picking...")
    validate_picking(
        orders,
        order_items,
        picking,
    )
    print("Picking validation passed.")

    print("Validating packing...")
    validate_packing(
        orders,
        order_items,
        picking,
        packing,
    )
    print("Packing validation passed.")

    print("Validating shipping...")
    validate_shipping(
        orders,
        packing,
        shipping,
    )
    print("Shipping validation passed.")

    print("Validating cross-dataset references...")
    validate_cross_dataset_references(
        products,
        locations,
        inventory,
        orders,
        order_items,
        picking,
        packing,
        shipping,
    )
    print("Cross-dataset validation passed.")

    print_summary(
        products,
        locations,
        inventory,
        orders,
        order_items,
        picking,
        packing,
        shipping,
    )


if __name__ == "__main__":
    main()
