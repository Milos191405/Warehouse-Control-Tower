from pathlib import Path
import csv
import random
from datetime import datetime, timedelta


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ORDERS_FILE = PROCESSED_DIR / "orders.csv"
ORDER_ITEMS_FILE = PROCESSED_DIR / "order_items.csv"
INVENTORY_FILE = PROCESSED_DIR / "inventory.csv"
LOCATIONS_FILE = PROCESSED_DIR / "locations.csv"

PICKING_FILE = PROCESSED_DIR / "picking.csv"


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

PICK_ID_START = 1

PICK_STATUSES = [
    "PICKED",
]

PICKING_METHODS = [
    "FORKLIFT",
    "PICKING_CART",
    "VERTICAL_LIFT",
    "STAPLER",
]

CONTAINER_TYPES = [
    "BOX",
    "CART",
    "PALLET",
]

# Synthetic operational timeline rules.
# Picking starts after order creation and each subsequent pick for
# the same order advances the operational clock.
PICKING_START_DELAY_MINUTES = (15, 90)
PICKING_STEP_MINUTES = (5, 20)

# Keep the generated timeline reproducible.
# Each order gets its own operational clock, starting after order creation.


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(file_path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

    with file_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(csv.DictReader(file))


# ============================================================
# LOAD DATA
# ============================================================

def load_orders():
    orders = read_csv(ORDERS_FILE)

    required = {
        "order_id",
        "order_datetime",
        "order_status",
    }

    missing = required - set(orders[0].keys())

    if missing:
        raise ValueError(
            f"Orders missing fields: {missing}"
        )

    return orders


def load_order_items():
    items = read_csv(ORDER_ITEMS_FILE)

    required = {
        "order_item_id",
        "order_id",
        "product_id",
        "requested_quantity",
    }

    missing = required - set(items[0].keys())

    if missing:
        raise ValueError(
            f"Order items missing fields: {missing}"
        )

    return items


def load_inventory():
    inventory = read_csv(INVENTORY_FILE)

    required = {
        "inventory_id",
        "product_id",
        "location_id",
        "quantity",
    }

    missing = required - set(inventory[0].keys())

    if missing:
        raise ValueError(
            f"Inventory missing fields: {missing}"
        )

    return inventory


def load_locations():
    locations = read_csv(LOCATIONS_FILE)

    required = {
        "location_id",
        "hall_id",
        "zone_nr",
        "storage_type",
        "picking_method",
        "position",
        "level",
        "side",
    }

    missing = required - set(locations[0].keys())

    if missing:
        raise ValueError(
            f"Locations missing fields: {missing}"
        )

    return locations


# ============================================================
# INDEXES
# ============================================================

def build_location_index(locations):
    return {
        row["location_id"]: row
        for row in locations
    }


def build_inventory_index(inventory):
    """
    product_id -> inventory records

    A product may exist at multiple warehouse locations.
    """
    index = {}

    for row in inventory:
        product_id = row["product_id"]

        index.setdefault(
            product_id,
            []
        ).append(row)

    return index


def build_order_index(orders):
    return {
        row["order_id"]: row
        for row in orders
    }


# ============================================================
# TIMELINE HELPERS
# ============================================================

def parse_order_datetime(order):
    try:
        return datetime.fromisoformat(
            order["order_datetime"]
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"Invalid order_datetime for "
            f"{order.get('order_id', 'UNKNOWN')}"
        ) from exc


# ============================================================
# CONTAINER LOGIC
# ============================================================

def choose_container_type(
    picking_method,
    quantity,
    order_weight_kg,
):
    """
    Simplified operational container rule.

    BOX:
        small picking quantities

    CART:
        cart-based picking

    PALLET:
        pallet/forklift/stapler handling
        or very heavy picks
    """

    if order_weight_kg >= 2000:
        return "PALLET"

    if picking_method in {
        "FORKLIFT",
        "STAPLER",
    }:
        return "PALLET"

    if picking_method in {
        "PICKING_CART",
        "VERTICAL_LIFT",
    }:
        if quantity <= 20:
            return "BOX"

        return "CART"

    return "BOX"


# ============================================================
# INVENTORY LOCATION SELECTION
# ============================================================

def choose_inventory_record(
    inventory_records,
    location_index,
    remaining_quantity,
):
    """
    Choose an inventory location that can satisfy the pick.

    Prefer a location with enough stock.
    Otherwise use the largest available quantity.
    """

    candidates = []

    for record in inventory_records:
        location_id = record["location_id"]

        if location_id not in location_index:
            continue

        available = int(
            float(record["quantity"])
        )

        if available <= 0:
            continue

        candidates.append(
            (
                record,
                available,
            )
        )

    if not candidates:
        return None

    sufficient = [
        item
        for item in candidates
        if item[1] >= remaining_quantity
    ]

    if sufficient:
        return random.choice(
            sufficient
        )[0]

    candidates.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    return candidates[0][0]


# ============================================================
# PICK GENERATION
# ============================================================

def generate_picking(
    order_items,
    inventory_index,
    location_index,
    order_index,
):
    """
    Generate one or more picking records per order item.

    If the required quantity cannot be fulfilled from one
    inventory location, the pick is split across locations.
    """

    picking_records = []

    pick_number = PICK_ID_START

    # Operational clock per order. This keeps every pick chronologically
    # connected to the order that created the work.
    order_pick_clock = {}

    # Copy available inventory quantities so that picks
    # consume stock during the simulation.
    remaining_inventory = {}

    for product_id, records in inventory_index.items():
        remaining_inventory[product_id] = {}

        for record in records:
            remaining_inventory[
                product_id
            ][record["inventory_id"]] = int(
                float(record["quantity"])
            )

    for item in order_items:

        product_id = item["product_id"]
        requested_quantity = int(
            item["requested_quantity"]
        )

        remaining_quantity = (
            requested_quantity
        )

        records = inventory_index.get(
            product_id,
            []
        )

        while remaining_quantity > 0:

            candidates = []

            for record in records:

                inventory_id = (
                    record["inventory_id"]
                )

                available = remaining_inventory[
                    product_id
                ].get(
                    inventory_id,
                    0,
                )

                if available <= 0:
                    continue

                location_id = (
                    record["location_id"]
                )

                if location_id not in location_index:
                    continue

                candidates.append(
                    (
                        record,
                        available,
                    )
                )

            if not candidates:
                break

            sufficient = [
                pair
                for pair in candidates
                if pair[1] >= remaining_quantity
            ]

            if sufficient:
                record, available = random.choice(
                    sufficient
                )
            else:
                record, available = max(
                    candidates,
                    key=lambda x: x[1]
                )

            location = location_index[
                record["location_id"]
            ]

            picked_quantity = min(
                remaining_quantity,
                available,
            )

            picking_method = (
                location["picking_method"]
            )

            # Use the order's total weight only as a
            # coarse operational signal. Exact item weight
            # is already stored in order_items.
            item_total_weight = float(
                item.get(
                    "total_weight_kg",
                    0,
                )
            )

            container_type = (
                choose_container_type(
                    picking_method,
                    picked_quantity,
                    item_total_weight,
                )
            )

            pick_id = (
                f"PICK-{pick_number:08d}"
            )

            pick_number += 1

            order = order_index.get(
                item["order_id"]
            )

            if order is None:
                raise ValueError(
                    f"Order {item['order_id']} "
                    "not found for picking."
                )

            if item["order_id"] not in order_pick_clock:
                order_pick_clock[item["order_id"]] = (
                    parse_order_datetime(order)
                    + timedelta(
                        minutes=random.randint(
                            *PICKING_START_DELAY_MINUTES
                        )
                    )
                )
            else:
                order_pick_clock[item["order_id"]] += timedelta(
                    minutes=random.randint(
                        *PICKING_STEP_MINUTES
                    )
                )

            pick_datetime = order_pick_clock[
                item["order_id"]
            ]

            picking_records.append(
                {
                    "picking_id": pick_id,
                    "order_item_id": item[
                        "order_item_id"
                    ],
                    "order_id": item[
                        "order_id"
                    ],
                    "product_id": product_id,
                    "inventory_id": record[
                        "inventory_id"
                    ],
                    "location_id": record[
                        "location_id"
                    ],
                    "hall_id": location[
                        "hall_id"
                    ],
                    "zone_nr": location[
                        "zone_nr"
                    ],
                    "picking_method": picking_method,
                    "storage_type": location[
                        "storage_type"
                    ],
                    "picked_quantity": picked_quantity,
                    "container_type": container_type,
                    "container_id": (
                        f"{container_type}-"
                        f"{pick_id}"
                    ),
                    "location_scan": True,
                    "container_scan": True,
                    "pick_status": "PICKED",
                    "pick_datetime": (
                        pick_datetime.isoformat(
                            timespec="seconds"
                        )
                    ),
                }
            )

            remaining_inventory[
                product_id
            ][
                record["inventory_id"]
            ] -= picked_quantity

            remaining_quantity -= picked_quantity

    return picking_records


# ============================================================
# VALIDATION
# ============================================================

def validate_picking(
    picking_records,
    orders,
    order_items,
    inventory,
    location_index,
):
    order_item_lookup = {
        row["order_item_id"]: row
        for row in order_items
    }

    order_lookup = {
        row["order_id"]: row
        for row in orders
    }

    inventory_ids = {
        row["inventory_id"]
        for row in inventory
    }

    picking_ids = [
        row["picking_id"]
        for row in picking_records
    ]

    assert len(picking_ids) == len(
        set(picking_ids)
    ), "Duplicate picking_id values."

    picked_by_item = {}
    last_pick_datetime_by_order = {}

    for pick in picking_records:

        assert (
            pick["order_item_id"]
            in order_item_lookup
        ), (
            f"Unknown order_item_id: "
            f"{pick['order_item_id']}"
        )

        assert (
            pick["inventory_id"]
            in inventory_ids
        ), (
            f"Unknown inventory_id: "
            f"{pick['inventory_id']}"
        )

        assert (
            pick["location_id"]
            in location_index
        ), (
            f"Unknown location_id: "
            f"{pick['location_id']}"
        )

        assert (
            pick["picking_method"]
            in PICKING_METHODS
        ), (
            f"Invalid picking method: "
            f"{pick['picking_method']}"
        )

        assert (
            pick["container_type"]
            in CONTAINER_TYPES
        ), (
            f"Invalid container type: "
            f"{pick['container_type']}"
        )

        assert (
            pick["picked_quantity"] > 0
        ), (
            f"Invalid picked quantity: "
            f"{pick['picking_id']}"
        )

        assert (
            pick["location_scan"]
            is True
        )

        assert (
            pick["container_scan"]
            is True
        )

        try:
            pick_datetime = datetime.fromisoformat(
                pick["pick_datetime"]
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid pick_datetime for "
                f"{pick['picking_id']}"
            ) from exc

        order = order_lookup.get(
            pick["order_id"]
        )

        assert order is not None, (
            f"Unknown order_id: {pick['order_id']}"
        )

        order_datetime = datetime.fromisoformat(
            order["order_datetime"]
        )

        assert pick_datetime >= order_datetime, (
            f"Pick occurs before order for "
            f"{pick['picking_id']}"
        )

        previous_pick = last_pick_datetime_by_order.get(
            pick["order_id"]
        )

        if previous_pick is not None:
            assert pick_datetime > previous_pick, (
                f"Picking timestamps are not strictly chronological "
                f"for order {pick['order_id']}"
            )

        last_pick_datetime_by_order[pick["order_id"]] = pick_datetime

        order_item_id = pick[
            "order_item_id"
        ]

        picked_by_item[
            order_item_id
        ] = (
            picked_by_item.get(
                order_item_id,
                0,
            )
            + int(
                pick[
                    "picked_quantity"
                ]
            )
        )

    incomplete = 0

    for item in order_items:

        requested = int(
            item["requested_quantity"]
        )

        picked = picked_by_item.get(
            item["order_item_id"],
            0,
        )

        if picked != requested:
            incomplete += 1

    print(
        f"Order items not fully picked: "
        f"{incomplete:,}"
    )

    if incomplete > 0:
        raise ValueError(
            f"Picking validation failed: "
            f"{incomplete:,} order items are not fully picked."
        )

    print(
        "Picking validation passed."
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    picking_records,
):
    total_picks = len(
        picking_records
    )

    total_quantity = sum(
        int(
            row["picked_quantity"]
        )
        for row in picking_records
    )

    print()
    print("Warehouse Picking Summary")
    print("=========================")

    print(
        f"Picking records:       "
        f"{total_picks:,}"
    )

    print(
        f"Picked quantity:       "
        f"{total_quantity:,}"
    )

    print()

    method_counts = {}

    for row in picking_records:
        method = row[
            "picking_method"
        ]

        method_counts[method] = (
            method_counts.get(
                method,
                0,
            )
            + 1
        )

    print("Picking Method")
    print("--------------")

    for method in PICKING_METHODS:
        print(
            f"{method:<18}"
            f"{method_counts.get(method, 0):,}"
        )

    print()
    print("Container Type")
    print("--------------")

    container_counts = {}

    for row in picking_records:
        container = row[
            "container_type"
        ]

        container_counts[container] = (
            container_counts.get(
                container,
                0,
            )
            + 1
        )

    for container in CONTAINER_TYPES:
        print(
            f"{container:<18}"
            f"{container_counts.get(container, 0):,}"
        )


# ============================================================
# EXPORT
# ============================================================

def export_picking(
    picking_records,
):
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "picking_id",
        "order_item_id",
        "order_id",
        "product_id",
        "inventory_id",
        "location_id",
        "hall_id",
        "zone_nr",
        "picking_method",
        "storage_type",
        "picked_quantity",
        "container_type",
        "container_id",
        "location_scan",
        "container_scan",
        "pick_status",
        "pick_datetime",
    ]

    with PICKING_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(
            picking_records
        )

    print()
    print(
        "Picking export complete:"
    )

    print(
        PICKING_FILE
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("Warehouse Picking Generator")
    print("===========================")

    print()
    print("Loading orders...")

    orders = load_orders()

    print(
        f"Orders loaded: "
        f"{len(orders):,}"
    )

    print()
    print("Loading order items...")

    order_items = load_order_items()

    print(
        f"Order items loaded: "
        f"{len(order_items):,}"
    )

    print()
    print("Loading inventory...")

    inventory = load_inventory()

    print(
        f"Inventory records loaded: "
        f"{len(inventory):,}"
    )

    print()
    print("Loading locations...")

    locations = load_locations()

    print(
        f"Locations loaded: "
        f"{len(locations):,}"
    )

    print()
    print("Building indexes...")

    order_index = build_order_index(
        orders
    )

    inventory_index = (
        build_inventory_index(
            inventory
        )
    )

    location_index = (
        build_location_index(
            locations
        )
    )

    print(
        f"Products in inventory index: "
        f"{len(inventory_index):,}"
    )

    print()
    print("Generating picking records...")

    picking_records = generate_picking(
        order_items=order_items,
        inventory_index=inventory_index,
        location_index=location_index,
        order_index=order_index,
    )

    print(
        f"Picking records generated: "
        f"{len(picking_records):,}"
    )

    print()
    print("Validating picking...")

    validate_picking(
        picking_records=picking_records,
        orders=orders,
        order_items=order_items,
        inventory=inventory,
        location_index=location_index,
    )

    print_summary(
        picking_records
    )

    export_picking(
        picking_records
    )


if __name__ == "__main__":
    main()
