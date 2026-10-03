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
PICKING_FILE = PROCESSED_DIR / "picking.csv"

PACKING_FILE = PROCESSED_DIR / "packing.csv"


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

PACKING_ID_START = 1

SMALL_ARTICLE_MIN = 1
SMALL_ARTICLE_MAX = 4
LARGE_ARTICLE_MIN = 5
LARGE_PACKAGE_MAX_WEIGHT_KG = 30.0

SMALL_PACKING_STATIONS_HALL_1 = [
    f"H1-KP-{i:02d}"
    for i in range(1, 6)
]

LARGE_PACKING_STATIONS_HALL_1 = [
    f"H1-GP-{i:02d}"
    for i in range(1, 10)
]

LARGE_PACKING_STATIONS_HALL_3 = [
    f"H3-GP-{i:02d}"
    for i in range(1, 3)
]

PACKING_STATUSES = [
    "PACKED",
]


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


def write_csv(file_path, rows, fieldnames):
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with file_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# LOAD DATA
# ============================================================

def load_orders():
    orders = read_csv(ORDERS_FILE)

    required = {
        "order_id",
        "order_status",
        "total_items",
        "total_weight_kg",
    }

    if not orders:
        raise ValueError("orders.csv is empty.")

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
        "total_weight_kg",
    }

    if not items:
        raise ValueError("order_items.csv is empty.")

    missing = required - set(items[0].keys())

    if missing:
        raise ValueError(
            f"Order items missing fields: {missing}"
        )

    return items


def load_picking():
    picking = read_csv(PICKING_FILE)

    required = {
        "picking_id",
        "order_id",
        "order_item_id",
        "product_id",
        "picked_quantity",
        "location_id",
        "picking_method",
        "container_type",
        "container_id",
        "location_scan",
        "container_scan",
    }

    if not picking:
        raise ValueError("picking.csv is empty.")

    missing = required - set(picking[0].keys())

    if missing:
        raise ValueError(
            f"Picking missing fields: {missing}"
        )

    return picking


# ============================================================
# INDEXES
# ============================================================

def build_order_index(orders):
    return {
        row["order_id"]: row
        for row in orders
    }


def build_order_item_index(order_items):
    index = {}

    for item in order_items:
        index.setdefault(
            item["order_id"],
            []
        ).append(item)

    return index


def build_picking_index(picking):
    index = {}

    for pick in picking:
        index.setdefault(
            pick["order_id"],
            []
        ).append(pick)

    return index


# ============================================================
# PACKING RULES
# ============================================================

def determine_packing_type(
    article_count,
    order_weight_kg,
):
    """
    Current simplified packing rules:

    1-4 articles:
        SMALL_PACKAGE

    5+ articles and <= 30 kg:
        LARGE_PACKAGE

    > 30 kg:
        PALLET_SHIPMENT
    """

    if article_count < SMALL_ARTICLE_MIN:
        raise ValueError(
            "Article count must be greater than zero."
        )

    if article_count <= SMALL_ARTICLE_MAX:
        return "SMALL_PACKAGE"

    if order_weight_kg <= LARGE_PACKAGE_MAX_WEIGHT_KG:
        return "LARGE_PACKAGE"

    return "PALLET_SHIPMENT"


def determine_packing_area(packing_type):
    if packing_type == "SMALL_PACKAGE":
        return "KLEIN_PACKEN"

    if packing_type == "LARGE_PACKAGE":
        return "GROSS_PACKEN"

    if packing_type == "PALLET_SHIPMENT":
        return "PALLET_PACKING"

    raise ValueError(
        f"Unknown packing type: {packing_type}"
    )


# ============================================================
# STATION ASSIGNMENT
# ============================================================

def assign_station(
    packing_type,
    station_counters,
):
    """
    Round-robin assignment.

    Small packages:
        Hall 1 Klein Packen

    Large packages:
        Hall 1 / Hall 3 Groß Packen

    Pallet shipments:
        Hall 1 large / pallet stations
    """

    if packing_type == "SMALL_PACKAGE":
        stations = SMALL_PACKING_STATIONS_HALL_1
        key = "SMALL"

    elif packing_type == "LARGE_PACKAGE":
        stations = (
            LARGE_PACKING_STATIONS_HALL_1
            + LARGE_PACKING_STATIONS_HALL_3
        )
        key = "LARGE"

    elif packing_type == "PALLET_SHIPMENT":
        stations = LARGE_PACKING_STATIONS_HALL_1
        key = "PALLET"

    else:
        raise ValueError(
            f"Unknown packing type: {packing_type}"
        )

    counter = station_counters[key]

    station = stations[
        counter % len(stations)
    ]

    station_counters[key] += 1

    return station


# ============================================================
# CONTAINER SCAN
# ============================================================

def determine_packing_container(picks):
    """
    The packing process scans the picking container.

    If an order contains multiple picking containers, the first
    container is used as the primary scanned container for this
    simplified packing simulation. The full container count is
    retained separately.
    """

    containers = []

    for pick in picks:
        container_id = str(
            pick["container_id"]
        ).strip()

        if container_id and container_id not in containers:
            containers.append(container_id)

    if not containers:
        raise ValueError(
            "Order has no picking container."
        )

    first_container = containers[0]

    container_type = "UNKNOWN"

    for pick in picks:
        if str(pick["container_id"]).strip() == first_container:
            container_type = str(
                pick["container_type"]
            ).strip().upper()
            break

    return first_container, containers, container_type


# ============================================================
# COMPLETENESS CHECK
# ============================================================

def verify_order_completeness(
    order_items,
    picks,
):
    requested_by_item = {}

    for item in order_items:
        order_item_id = item["order_item_id"]

        requested_by_item[order_item_id] = (
            int(float(item["requested_quantity"]))
        )

    picked_by_item = {}

    for pick in picks:
        order_item_id = pick["order_item_id"]

        picked_by_item[order_item_id] = (
            picked_by_item.get(
                order_item_id,
                0,
            )
            + int(float(pick["picked_quantity"]))
        )

    missing_items = []

    for order_item_id, requested_quantity in (
        requested_by_item.items()
    ):
        picked_quantity = picked_by_item.get(
            order_item_id,
            0,
        )

        if picked_quantity < requested_quantity:
            missing_items.append(
                order_item_id
            )

    return (
        len(missing_items) == 0,
        missing_items,
    )


# ============================================================
# PACKING GENERATION
# ============================================================

def generate_packing_records(
    orders,
    order_items,
    picking,
):
    order_index = build_order_index(
        orders
    )

    order_item_index = build_order_item_index(
        order_items
    )

    picking_index = build_picking_index(
        picking
    )

    station_counters = {
        "SMALL": 0,
        "LARGE": 0,
        "PALLET": 0,
    }

    packing_records = []

    packing_id = PACKING_ID_START

    for order_id, order in order_index.items():

        items = order_item_index.get(
            order_id,
            [],
        )

        picks = picking_index.get(
            order_id,
            [],
        )

        if not items:
            raise ValueError(
                f"Order {order_id} has no order items."
            )

        if not picks:
            raise ValueError(
                f"Order {order_id} has no picking records."
            )

        article_count = len(items)

        total_quantity = sum(
            int(float(
                item["requested_quantity"]
            ))
            for item in items
        )

        order_weight_kg = round(
            float(
                order["total_weight_kg"]
            ),
            3,
        )

        picked_quantity = sum(
            int(float(
                pick["picked_quantity"]
            ))
            for pick in picks
        )

        expected_quantity = total_quantity

        order_complete, missing_items = (
            verify_order_completeness(
                items,
                picks,
            )
        )

        if not order_complete:
            raise ValueError(
                f"Order {order_id} is not fully picked. "
                f"Missing items: {missing_items[:10]}"
            )

        if picked_quantity != expected_quantity:
            raise ValueError(
                f"Quantity mismatch for {order_id}: "
                f"expected {expected_quantity}, "
                f"picked {picked_quantity}"
            )

        packing_type = determine_packing_type(
            article_count=article_count,
            order_weight_kg=order_weight_kg,
        )

        packing_area = determine_packing_area(
            packing_type
        )

        station = assign_station(
            packing_type=packing_type,
            station_counters=station_counters,
        )

        primary_container, containers, container_type = (
            determine_packing_container(
                picks
            )
        )

        container_scan = True

        # Synthetic operational timestamps.
        # These are intentionally generated here because the current
        # picking output does not provide a dedicated packing timestamp.
        base_time = datetime.now()

        packing_started_at = (
            base_time
            + timedelta(
                minutes=random.randint(1, 30)
            )
        )

        packing_duration_minutes = random.randint(
            3,
            20,
        )

        if packing_type == "PALLET_SHIPMENT":
            packing_duration_minutes += random.randint(
                5,
                20,
            )

        packing_completed_at = (
            packing_started_at
            + timedelta(
                minutes=packing_duration_minutes
            )
        )

        packing_records.append(
            {
                "packing_id": (
                    f"PACK-{packing_id:06d}"
                ),
                "order_id": order_id,
                "packing_type": packing_type,
                "packing_area": packing_area,
                "packing_station": station,
                "container_id": primary_container,
                "container_type": container_type,
                "container_count": len(containers),
                "article_count": article_count,
                "total_quantity": total_quantity,
                "order_weight_kg": order_weight_kg,
                "container_scan": str(
                    container_scan
                ).upper(),
                "order_complete": str(
                    order_complete
                ).upper(),
                "packing_status": "PACKED",
                "packing_started_at": (
                    packing_started_at.isoformat(
                        timespec="seconds"
                    )
                ),
                "packing_completed_at": (
                    packing_completed_at.isoformat(
                        timespec="seconds"
                    )
                ),
            }
        )

        packing_id += 1

    return packing_records


# ============================================================
# VALIDATION
# ============================================================

def validate_packing(
    packing_records,
    orders,
    order_items,
    picking,
):
    print()
    print("Validating packing...")

    order_ids = {
        order["order_id"]
        for order in orders
    }

    item_order_ids = {
        item["order_id"]
        for item in order_items
    }

    picking_order_ids = {
        pick["order_id"]
        for pick in picking
    }

    packing_order_ids = {
        row["order_id"]
        for row in packing_records
    }

    assert (
        len(packing_records)
        == len(orders)
    ), (
        "Packing record count does not "
        "match order count."
    )

    assert (
        packing_order_ids
        == order_ids
    ), (
        "Packing orders do not match "
        "orders."
    )

    assert (
        item_order_ids
        == order_ids
    ), (
        "Some orders are missing order items."
    )

    assert (
        picking_order_ids
        == order_ids
    ), (
        "Some orders are missing picking records."
    )

    assert len(
        packing_order_ids
    ) == len(
        packing_records
    ), (
        "Duplicate packing records detected."
    )

    for row in packing_records:

        article_count = int(
            row["article_count"]
        )

        total_quantity = int(
            row["total_quantity"]
        )

        weight = float(
            row["order_weight_kg"]
        )

        assert article_count > 0, (
            f"Invalid article count "
            f"for {row['order_id']}"
        )

        assert total_quantity > 0, (
            f"Invalid quantity "
            f"for {row['order_id']}"
        )

        assert weight > 0, (
            f"Invalid weight "
            f"for {row['order_id']}"
        )

        assert row["container_scan"] == "TRUE", (
            f"Container was not scanned "
            f"for {row['order_id']}"
        )

        assert row["order_complete"] == "TRUE", (
            f"Order is incomplete "
            f"for {row['order_id']}"
        )

        packing_type = row[
            "packing_type"
        ]

        if article_count <= 4:
            assert (
                packing_type
                == "SMALL_PACKAGE"
            ), (
                f"Invalid small-package "
                f"classification for "
                f"{row['order_id']}"
            )

        elif weight <= 30:
            assert (
                packing_type
                == "LARGE_PACKAGE"
            ), (
                f"Invalid large-package "
                f"classification for "
                f"{row['order_id']}"
            )

        else:
            assert (
                packing_type
                == "PALLET_SHIPMENT"
            ), (
                f"Invalid pallet classification "
                f"for {row['order_id']}"
            )

        if packing_type == "SMALL_PACKAGE":
            assert row[
                "packing_area"
            ] == "KLEIN_PACKEN"

        elif packing_type == "LARGE_PACKAGE":
            assert row[
                "packing_area"
            ] == "GROSS_PACKEN"

        elif packing_type == "PALLET_SHIPMENT":
            assert row[
                "packing_area"
            ] == "PALLET_PACKING"

        assert row[
            "packing_status"
        ] == "PACKED"

        assert row[
            "container_id"
        ].strip()

        assert row[
            "packing_station"
        ].strip()

    print("Packing validation passed.")


# ============================================================
# SUMMARY
# ============================================================

def print_packing_summary(
    packing_records,
):
    small = 0
    large = 0
    pallet = 0

    for row in packing_records:
        packing_type = row[
            "packing_type"
        ]

        if packing_type == "SMALL_PACKAGE":
            small += 1

        elif packing_type == "LARGE_PACKAGE":
            large += 1

        elif packing_type == "PALLET_SHIPMENT":
            pallet += 1

    print()
    print("Warehouse Packing Summary")
    print("=========================")
    print(
        f"Packing records:       "
        f"{len(packing_records):,}"
    )

    print()
    print("Packing Type")
    print("------------")
    print(
        f"SMALL_PACKAGE      {small:,}"
    )
    print(
        f"LARGE_PACKAGE      {large:,}"
    )
    print(
        f"PALLET_SHIPMENT    {pallet:,}"
    )

    station_counts = {}

    for row in packing_records:
        station = row[
            "packing_station"
        ]

        station_counts[station] = (
            station_counts.get(
                station,
                0,
            )
            + 1
        )

    print()
    print("Packing Stations")
    print("----------------")

    for station in sorted(
        station_counts
    ):
        print(
            f"{station:<18} "
            f"{station_counts[station]:,}"
        )


# ============================================================
# EXPORT
# ============================================================

def export_packing(
    packing_records,
):
    fieldnames = [
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
    ]

    write_csv(
        PACKING_FILE,
        packing_records,
        fieldnames,
    )

    print()
    print(
        "Packing export complete:"
    )
    print(
        PACKING_FILE
    )


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("Warehouse Packing Generator")
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
    print("Loading picking...")

    picking = load_picking()

    print(
        f"Picking records loaded: "
        f"{len(picking):,}"
    )

    print()
    print("Generating packing records...")

    packing_records = generate_packing_records(
        orders=orders,
        order_items=order_items,
        picking=picking,
    )

    print(
        f"Packing records generated: "
        f"{len(packing_records):,}"
    )

    validate_packing(
        packing_records=packing_records,
        orders=orders,
        order_items=order_items,
        picking=picking,
    )

    print_packing_summary(
        packing_records
    )

    export_packing(
        packing_records
    )


if __name__ == "__main__":
    main()
