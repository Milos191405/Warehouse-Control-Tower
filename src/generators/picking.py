from pathlib import Path
import csv
import os
import random
from datetime import datetime, timedelta

from working_time import (
    load_capacity_by_date,
    snap_timestamps,
)
from capacity_queue import apply_hall_capacity


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = Path(
    os.getenv("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed")
)

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


# ============================================================
# OPERATIONAL TIMELINE
# ============================================================

PICKING_START_DELAY_MINUTES = (
    15,
    90,
)

PICKING_STEP_MINUTES = (
    5,
    20,
)


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(file_path):
    """
    Read CSV and return a list of dictionaries.
    """
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

    with file_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        return list(
            csv.DictReader(file)
        )


# ============================================================
# LOAD ORDERS
# ============================================================

def load_orders():
    orders = read_csv(
        ORDERS_FILE
    )

    if not orders:
        raise ValueError(
            "Orders file is empty."
        )

    required = {
        "order_id",
        "order_datetime",
        "order_status",
    }

    missing = (
        required
        - set(orders[0].keys())
    )

    if missing:
        raise ValueError(
            f"Orders missing fields: {missing}"
        )

    return orders


# ============================================================
# LOAD ORDER ITEMS
# ============================================================

def load_order_items():
    items = read_csv(
        ORDER_ITEMS_FILE
    )

    if not items:
        raise ValueError(
            "Order items file is empty."
        )

    required = {
        "order_item_id",
        "order_id",
        "product_id",
        "requested_quantity",
    }

    missing = (
        required
        - set(items[0].keys())
    )

    if missing:
        raise ValueError(
            f"Order items missing fields: {missing}"
        )

    return items


# ============================================================
# LOAD INVENTORY
# ============================================================

def load_inventory():
    inventory = read_csv(
        INVENTORY_FILE
    )

    if not inventory:
        raise ValueError(
            "Inventory file is empty."
        )

    required = {
        "inventory_id",
        "product_id",
        "location_id",
        "quantity",
    }

    missing = (
        required
        - set(inventory[0].keys())
    )

    if missing:
        raise ValueError(
            f"Inventory missing fields: {missing}"
        )

    return inventory


# ============================================================
# LOAD LOCATIONS
# ============================================================

def load_locations():
    locations = read_csv(
        LOCATIONS_FILE
    )

    if not locations:
        raise ValueError(
            "Locations file is empty."
        )

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

    missing = (
        required
        - set(locations[0].keys())
    )

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
    Build:

        product_id -> inventory records

    A product may exist at multiple warehouse locations.
    """
    index = {}

    for row in inventory:
        product_id = row["product_id"]
        index.setdefault(
            product_id,
            [],
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
            "Invalid order_datetime for "
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

    PALLET:
        very heavy picks
        forklift
        stapler

    CART:
        cart-based picking with larger quantities

    BOX:
        smaller picks
        vertical lift / cart picking
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
    requested_quantity,
):
    """
    Choose a valid inventory location.

    IMPORTANT:
    This function does NOT modify inventory.
    """
    candidates = []

    for record in inventory_records:
        location_id = record["location_id"]

        if location_id not in location_index:
            continue

        try:
            available = int(float(record["quantity"]))
        except (ValueError, TypeError):
            continue

        if available <= 0:
            continue

        candidates.append((record, available))

    if not candidates:
        return None

    sufficient = [
        pair
        for pair in candidates
        if pair[1] >= requested_quantity
    ]

    if sufficient:
        return random.choice(sufficient)[0]

    candidates.sort(
        key=lambda pair: pair[1],
        reverse=True,
    )

    return candidates[0][0]


# ============================================================
# PICKING GENERATION
# ============================================================

def generate_picking(
    order_items,
    inventory_index,
    location_index,
    order_index,
):
    """
    Generate picking records.
    """
    picking_records = []
    pick_number = PICK_ID_START

    order_items_by_order = {}

    for item in order_items:
        order_items_by_order.setdefault(
            item["order_id"],
            [],
        ).append(item)

    for order_id, items in order_items_by_order.items():
        order = order_index.get(order_id)

        if order is None:
            raise ValueError(
                f"Order {order_id} not found for picking."
            )

        order_datetime = parse_order_datetime(order)

        try:
            requested_delivery_datetime = datetime.fromisoformat(
                order["requested_delivery_datetime"]
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid requested_delivery_datetime for {order_id}"
            ) from exc

        if requested_delivery_datetime <= order_datetime:
            raise ValueError(
                f"Delivery deadline is not after order creation "
                f"for {order_id}: "
                f"order={order_datetime.isoformat()}, "
                f"deadline={requested_delivery_datetime.isoformat()}"
            )

        order_records = []
        stock_remaining = {}

        order_product_ids = {item["product_id"] for item in items}

        for product_id in order_product_ids:
            for record in inventory_index.get(product_id, []):
                inventory_id = record.get("inventory_id")
                try:
                    raw_quantity = float(record.get("quantity", 0))
                    if not raw_quantity.is_integer():
                        raise ValueError
                    qty = int(raw_quantity)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Invalid inventory quantity for {inventory_id}: "
                        f"{record.get('quantity')!r}"
                    )
                if qty < 0:
                    raise ValueError(
                        f"Negative opening inventory quantity for {inventory_id}."
                    )
                stock_remaining[inventory_id] = qty

        # Generate picking records without timestamps first.
        for item in items:
            product_id = item["product_id"]
            requested_quantity = int(item["requested_quantity"])

            if requested_quantity <= 0:
                raise ValueError(
                    f"Invalid requested quantity for {item['order_item_id']}"
                )

            remaining_quantity = requested_quantity
            records = inventory_index.get(product_id, [])

            if not records:
                raise ValueError(
                    f"No inventory location found for product {product_id}"
                )

            valid_records = [
                record for record in records
                if record.get("location_id") in location_index
            ]

            if not valid_records:
                raise ValueError(
                    f"No valid inventory location found for product {product_id}"
                )

            while remaining_quantity > 0:
                available_records = [
                    record for record in valid_records
                    if stock_remaining.get(record.get("inventory_id"), 0) > 0
                ]

                if not available_records:
                    break

                sufficient = [
                    record for record in available_records
                    if stock_remaining[record["inventory_id"]] >= remaining_quantity
                ]

                if sufficient:
                    record = random.choice(sufficient)
                else:
                    record = max(
                        available_records,
                        key=lambda row: stock_remaining[row["inventory_id"]],
                    )

                inventory_quantity = stock_remaining[record["inventory_id"]]

                picked_quantity = min(
                    remaining_quantity,
                    inventory_quantity,
                )

                location = location_index[record["location_id"]]
                picking_method = location["picking_method"]

                item_total_weight = float(
                    item.get("total_weight_kg", 0)
                )

                container_type = choose_container_type(
                    picking_method=picking_method,
                    quantity=picked_quantity,
                    order_weight_kg=item_total_weight,
                )

                pick_id = f"PICK-{pick_number:08d}"
                pick_number += 1

                order_records.append(
                    {
                        "picking_id": pick_id,
                        "order_item_id": item["order_item_id"],
                        "order_id": order_id,
                        "product_id": product_id,
                        "inventory_id": record["inventory_id"],
                        "location_id": record["location_id"],
                        "hall_id": location["hall_id"],
                        "zone_nr": location["zone_nr"],
                        "picking_method": picking_method,
                        "storage_type": location["storage_type"],
                        "picked_quantity": picked_quantity,
                        "container_type": container_type,
                        "container_id": f"{container_type}-{pick_id}",
                        "location_scan": True,
                        "container_scan": True,
                        "pick_status": "PICKED",
                        "pick_datetime": None,
                    }
                )

                remaining_quantity -= picked_quantity
                stock_remaining[record["inventory_id"]] -= picked_quantity

                if stock_remaining[record["inventory_id"]] < 0:
                    raise AssertionError(
                        f"Inventory became negative for {record['inventory_id']}."
                    )

        if not order_records:
            raise ValueError(
                f"No picking records generated for {order_id}"
            )

        # Timeline calculation
        record_count = len(order_records)

        total_window_seconds = (
            requested_delivery_datetime
            - order_datetime
        ).total_seconds()

        if total_window_seconds <= 0:
            raise ValueError(
                f"Invalid operational window for {order_id}"
            )

        buffer_seconds = min(
            60,
            max(1, int(total_window_seconds * 0.05)),
        )

        latest_allowed_pick = (
            requested_delivery_datetime
            - timedelta(seconds=buffer_seconds)
        )

        usable_seconds = (
            latest_allowed_pick
            - order_datetime
        ).total_seconds()

        minimum_step_seconds = PICKING_STEP_MINUTES[0] * 60

        if record_count == 1:
            maximum_start_delay = max(0, int(usable_seconds))

            start_delay_seconds = min(
                random.randint(
                    PICKING_START_DELAY_MINUTES[0] * 60,
                    PICKING_START_DELAY_MINUTES[1] * 60,
                ),
                maximum_start_delay,
            )

            first_pick_datetime = (
                order_datetime
                + timedelta(seconds=start_delay_seconds)
            )

            timestamps = [first_pick_datetime]

        else:
            normal_start_delay = random.randint(
                PICKING_START_DELAY_MINUTES[0] * 60,
                PICKING_START_DELAY_MINUTES[1] * 60,
            )

            normal_required_seconds = (
                (record_count - 1) * minimum_step_seconds
            )

            if usable_seconds >= (
                normal_start_delay + normal_required_seconds
            ):
                start_delay_seconds = normal_start_delay

                first_pick_datetime = (
                    order_datetime
                    + timedelta(seconds=start_delay_seconds)
                )

                available_for_steps = (
                    latest_allowed_pick
                    - first_pick_datetime
                ).total_seconds()

                timestamps = [first_pick_datetime]
                remaining_seconds = available_for_steps

                for index in range(1, record_count):
                    picks_remaining_after_current = (
                        record_count - index - 1
                    )

                    minimum_future_seconds = (
                        picks_remaining_after_current * minimum_step_seconds
                    )

                    maximum_step_seconds = (
                        remaining_seconds - minimum_future_seconds
                    )

                    step_upper_bound = min(
                        maximum_step_seconds,
                        PICKING_STEP_MINUTES[1] * 60,
                    )

                    step_seconds = random.randint(
                        minimum_step_seconds,
                        max(minimum_step_seconds, int(step_upper_bound)),
                    )

                    timestamps.append(
                        timestamps[-1] + timedelta(seconds=step_seconds)
                    )

                    remaining_seconds -= step_seconds

            else:
                first_pick_datetime = (
                    order_datetime
                    + timedelta(
                        seconds=min(
                            60,
                            max(1, int(usable_seconds * 0.05)),
                        )
                    )
                )

                available_for_steps = (
                    latest_allowed_pick
                    - first_pick_datetime
                ).total_seconds()

                if available_for_steps <= (record_count - 1):
                    raise ValueError(
                        f"Insufficient time even for a "
                        f"compressed picking timeline for {order_id}. "
                        f"Records={record_count}, "
                        f"available_seconds={available_for_steps:.0f}"
                    )

                step_seconds = (
                    available_for_steps / (record_count - 1)
                )

                timestamps = [
                    first_pick_datetime
                    + timedelta(seconds=(index * step_seconds))
                    for index in range(record_count)
                ]

        # Final timestamp validation
        previous_timestamp = None

        for index, record in enumerate(order_records):
            pick_datetime = timestamps[index]

            if pick_datetime < order_datetime:
                raise ValueError(
                    f"Pick occurs before order creation for {order_id}"
                )

            if (
                previous_timestamp is not None
                and pick_datetime <= previous_timestamp
            ):
                raise ValueError(
                    f"Picking timestamps are not strictly chronological for {order_id}"
                )

            if pick_datetime >= requested_delivery_datetime:
                raise ValueError(
                    f"Pick occurs at/after delivery deadline "
                    f"for {order_id}: "
                    f"pick={pick_datetime.isoformat()}, "
                    f"deadline={requested_delivery_datetime.isoformat()}"
                )

            record["pick_datetime"] = pick_datetime.isoformat(
                timespec="seconds"
            )

            previous_timestamp = pick_datetime

        picking_records.extend(order_records)

        if (
            len(picking_records) // 5_000
            > (len(picking_records) - len(order_records)) // 5_000
        ):
            print(
                f"  Generated {len(picking_records):,} picking records..."
            )

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
    if not picking_records:
        raise ValueError("No picking records generated.")

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

    assert len(picking_ids) == len(set(picking_ids)), (
        "Duplicate picking_id values."
    )

    picked_by_item = {}
    last_pick_datetime_by_order = {}
    picks_after_deadline = 0

    for pick in picking_records:
        order_item_id = pick["order_item_id"]
        order_id = pick["order_id"]

        assert order_item_id in order_item_lookup, (
            f"Unknown order_item_id: {order_item_id}"
        )

        assert pick["inventory_id"] in inventory_ids, (
            f"Unknown inventory_id: {pick['inventory_id']}"
        )

        assert pick["location_id"] in location_index, (
            f"Unknown location_id: {pick['location_id']}"
        )

        assert pick["picking_method"] in PICKING_METHODS, (
            f"Invalid picking method: {pick['picking_method']}"
        )

        assert pick["container_type"] in CONTAINER_TYPES, (
            f"Invalid container type: {pick['container_type']}"
        )

        assert int(pick["picked_quantity"]) > 0, (
            f"Invalid picked quantity: {pick['picking_id']}"
        )

        assert pick["location_scan"] is True, (
            f"Location scan missing: {pick['picking_id']}"
        )

        assert pick["container_scan"] is True, (
            f"Container scan missing: {pick['picking_id']}"
        )

        assert pick["pick_status"] in PICK_STATUSES, (
            f"Invalid pick status: {pick['picking_id']}"
        )

        try:
            pick_datetime = datetime.fromisoformat(pick["pick_datetime"])
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid pick_datetime for {pick['picking_id']}"
            ) from exc

        order = order_lookup.get(order_id)
        assert order is not None, f"Unknown order_id: {order_id}"

        order_datetime = datetime.fromisoformat(order["order_datetime"])
        assert pick_datetime >= order_datetime, (
            f"Pick occurs before order: {pick['picking_id']}"
        )

        try:
            requested_delivery_datetime = datetime.fromisoformat(
                order["requested_delivery_datetime"]
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid requested_delivery_datetime for {order_id}"
            ) from exc

        if pick_datetime >= requested_delivery_datetime:
            picks_after_deadline += 1

        previous_pick = last_pick_datetime_by_order.get(order_id)
        if previous_pick is not None:
            assert pick_datetime > previous_pick, (
                f"Picking timestamps are not strictly chronological for order {order_id}"
            )

        last_pick_datetime_by_order[order_id] = pick_datetime

        picked_by_item[order_item_id] = (
            picked_by_item.get(order_item_id, 0)
            + int(pick["picked_quantity"])
        )

    incomplete = 0
    for item in order_items:
        requested = int(item["requested_quantity"])
        picked = picked_by_item.get(item["order_item_id"], 0)

        if picked > requested:
            raise ValueError(
                f"Over-picking detected for {item['order_item_id']}: "
                f"requested={requested}, picked={picked}"
            )

        if picked < requested:
            incomplete += 1

    print()
    print(f"Order items not fully picked: {incomplete:,}")

    if incomplete > 0:
        print(
            "Some order items remain partially/unpicked; "
            "they must wait for replenishment."
        )

    opening_by_inventory = {
        row["inventory_id"]: int(float(row["quantity"]))
        for row in inventory
    }
    picked_by_order_inventory = {}
    for pick in picking_records:
        key = (pick["order_id"], pick["inventory_id"])
        picked_by_order_inventory[key] = (
            picked_by_order_inventory.get(key, 0)
            + int(pick["picked_quantity"])
        )
    for (order_id, inv_id), picked_qty in picked_by_order_inventory.items():
        opening_qty = opening_by_inventory.get(inv_id)
        if opening_qty is None or picked_qty > opening_qty:
            raise ValueError(
                f"Stock conservation failed for order {order_id}, "
                f"inventory {inv_id}: opening={opening_qty}, picked={picked_qty}"
            )

    print(f"Picks after delivery deadline: {picks_after_deadline:,}")
    print("Picking validation passed.")


# ============================================================
# SUMMARY
# ============================================================

def print_summary(picking_records):
    total_picks = len(picking_records)
    total_quantity = sum(int(row["picked_quantity"]) for row in picking_records)

    print()
    print("Warehouse Picking Summary")
    print("=========================")
    print(f"Picking records:       {total_picks:,}")
    print(f"Picked quantity:       {total_quantity:,}")

    print()
    print("Picking Method")
    print("--------------")

    method_counts = {}
    for row in picking_records:
        method = row["picking_method"]
        method_counts[method] = method_counts.get(method, 0) + 1

    for method in PICKING_METHODS:
        print(f"{method:<18}{method_counts.get(method, 0):,}")

    print()
    print("Container Type")
    print("--------------")

    container_counts = {}
    for row in picking_records:
        container = row["container_type"]
        container_counts[container] = container_counts.get(container, 0) + 1

    for container in CONTAINER_TYPES:
        print(f"{container:<18}{container_counts.get(container, 0):,}")


# ============================================================
# EXPORT
# ============================================================

def export_picking(picking_records):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

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

    with PICKING_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(picking_records)

    print()
    print("Picking export complete:")
    print(PICKING_FILE)


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("Warehouse Picking Generator")
    print("===========================")

    print("\nLoading orders...")
    orders = load_orders()
    print(f"Orders loaded: {len(orders):,}")

    print("\nLoading order items...")
    order_items = load_order_items()
    print(f"Order items loaded: {len(order_items):,}")

    print("\nLoading inventory...")
    inventory = load_inventory()
    print(f"Inventory records loaded: {len(inventory):,}")

    print("\nLoading locations...")
    locations = load_locations()
    print(f"Locations loaded: {len(locations):,}")

    print("\nBuilding indexes...")
    order_index = build_order_index(orders)
    inventory_index = build_inventory_index(inventory)
    location_index = build_location_index(locations)
    print(f"Products in inventory index: {len(inventory_index):,}")

    print("\nGenerating picking records...")
    picking_records = generate_picking(
        order_items=order_items,
        inventory_index=inventory_index,
        location_index=location_index,
        order_index=order_index,
    )
    print(f"Picking records generated: {len(picking_records):,}")

    picking_records = schedule_picks(picking_records, orders)

    print("\nValidating picking...")
    validate_picking(
        picking_records=picking_records,
        orders=orders,
        order_items=order_items,
        inventory=inventory,
        location_index=location_index,
    )

    print_summary(picking_records)
    export_picking(picking_records)

    print("\nPicking generation completed successfully.")


# ============================================================
# WORKING TIME + HALL CAPACITY
# ============================================================

def schedule_picks(picking_records, orders):
    """
    Phase 2 of picking generation.
    """
    capacity_by_date = load_capacity_by_date()

    order_metadata = {}
    for order in orders:
        order_id = order.get("order_id")
        deadline = order.get("requested_delivery_datetime")
        if not order_id or not deadline:
            raise ValueError(
                f"Order is missing order_id or requested_delivery_datetime: {order}"
            )
        try:
            parsed_deadline = datetime.fromisoformat(deadline)
        except ValueError as exc:
            raise ValueError(
                f"Invalid requested_delivery_datetime for {order_id}: {deadline!r}"
            ) from exc
        order_metadata[order_id] = {
            "deadline": parsed_deadline,
            "priority": (order.get("delivery_priority") or "NORMAL").strip().upper(),
        }

    by_order = {}
    for record in picking_records:
        by_order.setdefault(record["order_id"], []).append(record)

    for records in by_order.values():
        snapped = snap_timestamps(
            [datetime.fromisoformat(record["pick_datetime"]) for record in records],
            capacity_by_date,
        )
        for record, timestamp in zip(records, snapped):
            record["pick_datetime"] = timestamp.isoformat(timespec="seconds")

    return apply_hall_capacity(
        picking_records,
        capacity_by_date,
        order_metadata=order_metadata,
    )


if __name__ == "__main__":
    main()