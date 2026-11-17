from pathlib import Path
import csv
import os
import random
from datetime import datetime, timedelta

from working_time import (
    add_working_duration,
    load_capacity_by_date,
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = Path(
    os.getenv("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed")
)

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


# ============================================================
# PACKING RULES (<= 30 kg BOXES 201/202/203, > 30 kg PALLET)
# ============================================================

SMALL_ARTICLE_MIN = 1
SMALL_ARTICLE_MAX = 4
SMALL_PACKAGE_MAX_WEIGHT_KG = 10.0

MAX_BOX_WEIGHT_KG = 30.0

BOX_PACKAGE_TYPES = [
    "BOX_201",
    "BOX_202",
    "BOX_203",
]

PACKAGE_TYPES = BOX_PACKAGE_TYPES + [
    "PALLET",
]


# ============================================================
# PACKING STATIONS
# ============================================================

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


# ============================================================
# STATUS & TIMELINE
# ============================================================

PACKING_STATUSES = [
    "PACKED",
]

PACKING_START_DELAY_MINUTES = (5, 30)
PACKING_DURATION_MINUTES = (3, 20)
PALLET_EXTRA_DURATION_MINUTES = (5, 20)


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(file_path):
    if not file_path.exists():
        raise FileNotFoundError(f"Required file not found: {file_path}")

    with file_path.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def write_csv(file_path, rows, fieldnames):
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ============================================================
# LOADERS
# ============================================================

def load_orders():
    orders = read_csv(ORDERS_FILE)
    if not orders:
        raise ValueError("orders.csv is empty.")

    required = {
        "order_id",
        "order_datetime",
        "requested_delivery_datetime",
        "total_items",
        "total_weight_kg",
    }
    missing = required - set(orders[0].keys())
    if missing:
        raise ValueError(f"Orders missing fields: {missing}")

    return orders


def load_order_items():
    items = read_csv(ORDER_ITEMS_FILE)
    if not items:
        raise ValueError("order_items.csv is empty.")

    required = {
        "order_item_id",
        "order_id",
        "product_id",
        "requested_quantity",
        "total_weight_kg",
    }
    missing = required - set(items[0].keys())
    if missing:
        raise ValueError(f"Order items missing fields: {missing}")

    return items


def load_picking():
    picking = read_csv(PICKING_FILE)
    if not picking:
        raise ValueError("picking.csv is empty.")

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
        "pick_datetime",
    }
    missing = required - set(picking[0].keys())
    if missing:
        raise ValueError(f"Picking missing fields: {missing}")

    return picking


# ============================================================
# INDEXES
# ============================================================

def build_order_index(orders):
    return {row["order_id"]: row for row in orders}


def build_order_item_index(order_items):
    index = {}
    for item in order_items:
        index.setdefault(item["order_id"], []).append(item)
    return index


def build_picking_index(picking):
    index = {}
    for pick in picking:
        index.setdefault(pick["order_id"], []).append(pick)
    return index


def build_latest_pick_index(picking):
    latest_pick = {}
    for pick in picking:
        order_id = pick["order_id"]
        pick_datetime = datetime.fromisoformat(pick["pick_datetime"])
        previous = latest_pick.get(order_id)
        if previous is None or pick_datetime > previous:
            latest_pick[order_id] = pick_datetime
    return latest_pick


# ============================================================
# PACKING RULES
# ============================================================

def determine_packing_type(article_count, order_weight_kg):
    """
    Packing classification rules:
      - <= 30.0 kg: boxes (BOX_201, BOX_202, BOX_203)
          * SMALL_PACKAGE (Kleinpacken): 1-4 lines AND <= 10.0 kg
          * LARGE_PACKAGE (Großpacken):  <= 30.0 kg (remaining orders up to 30 kg)
      - > 30.0 kg: PALLET_SHIPMENT (Pallet)
    """
    if article_count < SMALL_ARTICLE_MIN:
        raise ValueError("Article count must be greater than zero.")

    if order_weight_kg > MAX_BOX_WEIGHT_KG:
        return "PALLET_SHIPMENT"

    if (
        article_count <= SMALL_ARTICLE_MAX
        and order_weight_kg <= SMALL_PACKAGE_MAX_WEIGHT_KG
    ):
        return "SMALL_PACKAGE"

    return "LARGE_PACKAGE"


def determine_packing_area(packing_type):
    if packing_type == "SMALL_PACKAGE":
        return "KLEIN_PACKEN"
    if packing_type == "LARGE_PACKAGE":
        return "GROSS_PACKEN"
    if packing_type == "PALLET_SHIPMENT":
        return "PALLET_PACKING"
    raise ValueError(f"Unknown packing type: {packing_type}")


# ============================================================
# STATION ASSIGNMENT
# ============================================================

def build_station_profiles():
    profiles = {}

    kp_capacity = {
        "H1-KP-01": 1.05,
        "H1-KP-02": 0.95,
        "H1-KP-03": 1.00,
        "H1-KP-04": 1.10,
        "H1-KP-05": 0.90,
    }

    gp_h1_capacity = {
        "H1-GP-01": 1.05,
        "H1-GP-02": 0.95,
        "H1-GP-03": 1.00,
        "H1-GP-04": 1.10,
        "H1-GP-05": 0.92,
        "H1-GP-06": 1.03,
        "H1-GP-07": 0.97,
        "H1-GP-08": 1.08,
        "H1-GP-09": 0.90,
    }

    gp_h3_capacity = {
        "H3-GP-01": 0.95,
        "H3-GP-02": 1.05,
    }

    for station, factor in kp_capacity.items():
        profiles[station] = {
            "capacity_factor": factor,
            "nominal_capacity_per_hour": 24.0 * factor,
        }

    for station, factor in gp_h1_capacity.items():
        profiles[station] = {
            "capacity_factor": factor,
            "nominal_capacity_per_hour": 10.0 * factor,
        }

    for station, factor in gp_h3_capacity.items():
        profiles[station] = {
            "capacity_factor": factor,
            "nominal_capacity_per_hour": 9.0 * factor,
        }

    return profiles


def get_eligible_stations(packing_type):
    if packing_type == "SMALL_PACKAGE":
        return SMALL_PACKING_STATIONS_HALL_1
    if packing_type == "LARGE_PACKAGE":
        return LARGE_PACKING_STATIONS_HALL_1 + LARGE_PACKING_STATIONS_HALL_3
    if packing_type == "PALLET_SHIPMENT":
        return LARGE_PACKING_STATIONS_HALL_1
    raise ValueError(f"Unknown packing type: {packing_type}")


def assign_station(packing_type, station_profiles):
    stations = get_eligible_stations(packing_type)
    weights = [station_profiles[station]["capacity_factor"] for station in stations]
    return random.choices(stations, weights=weights, k=1)[0]


def determine_package_type(
    packing_type,
    article_count,
    order_weight_kg,
    total_quantity,
):
    if packing_type == "PALLET_SHIPMENT":
        return "PALLET"

    if packing_type == "SMALL_PACKAGE":
        if order_weight_kg <= 3.5 and article_count <= 2 and total_quantity <= 8:
            return "BOX_201"
        if order_weight_kg <= 7.5 and article_count <= 3:
            return "BOX_202"
        return "BOX_203"

    if packing_type == "LARGE_PACKAGE":
        if order_weight_kg <= 16.0 and total_quantity <= 30:
            return "BOX_202"
        return "BOX_203"

    raise ValueError(f"Unknown packing type: {packing_type}")


def calculate_workload_units(
    article_count,
    total_quantity,
    order_weight_kg,
    container_count,
    packing_type,
):
    workload = (
        article_count * 1.5
        + total_quantity * 0.08
        + order_weight_kg * 0.12
        + container_count * 2.0
    )

    if packing_type == "LARGE_PACKAGE":
        workload *= 1.20
    elif packing_type == "PALLET_SHIPMENT":
        workload *= 1.75

    return round(max(workload, 1.0), 2)


# ============================================================
# CONTAINER SCAN & COMPLETENESS CHECK
# ============================================================

def determine_packing_container(picks):
    containers = []
    container_types = {}

    for pick in picks:
        container_id = str(pick["container_id"]).strip()
        if not container_id:
            continue
        if container_id not in containers:
            containers.append(container_id)
        container_types[container_id] = str(pick["container_type"]).strip().upper()

    if not containers:
        raise ValueError("Order has no picking container.")

    primary_container = containers[0]
    primary_container_type = container_types[primary_container]

    return primary_container, containers, primary_container_type


def verify_order_completeness(order_items, picks):
    requested_by_item = {
        item["order_item_id"]: int(float(item["requested_quantity"]))
        for item in order_items
    }

    picked_by_item = {}
    for pick in picks:
        order_item_id = pick["order_item_id"]
        picked_by_item[order_item_id] = (
            picked_by_item.get(order_item_id, 0)
            + int(float(pick["picked_quantity"]))
        )

    missing_items = [
        order_item_id
        for order_item_id, requested_qty in requested_by_item.items()
        if picked_by_item.get(order_item_id, 0) < requested_qty
    ]

    return len(missing_items) == 0, missing_items


# ============================================================
# PACKING TIMELINE (SHIFT & CALENDAR AWARE)
# ============================================================

def generate_packing_timeline(
    latest_pick_datetime,
    packing_type,
    article_count,
    total_quantity,
    order_weight_kg,
    container_count,
    station_capacity_factor,
    capacity_by_date,
):
    base_duration = random.randint(*PACKING_DURATION_MINUTES)

    complexity_minutes = (
        article_count * 0.8
        + total_quantity * 0.02
        + order_weight_kg * 0.03
        + container_count * 1.5
    )

    if packing_type == "LARGE_PACKAGE":
        complexity_minutes += 4
    elif packing_type == "PALLET_SHIPMENT":
        complexity_minutes += random.randint(*PALLET_EXTRA_DURATION_MINUTES)

    duration_minutes = (base_duration + complexity_minutes) / max(
        station_capacity_factor, 0.50
    )
    duration_minutes = max(2.0, min(duration_minutes, 90.0))
    duration_seconds = int(round(duration_minutes * 60))

    start_delay_minutes = random.randint(*PACKING_START_DELAY_MINUTES)

    packing_started_at = add_working_duration(
        latest_pick_datetime,
        timedelta(minutes=start_delay_minutes),
        capacity_by_date,
    )

    packing_completed_at = add_working_duration(
        packing_started_at,
        timedelta(seconds=duration_seconds),
        capacity_by_date,
    )

    if packing_completed_at <= packing_started_at:
        raise ValueError("Packing completion must be strictly after packing start.")

    return packing_started_at, packing_completed_at


# ============================================================
# PACKING GENERATION
# ============================================================

def generate_packing_records(orders, order_items, picking):
    order_index = build_order_index(orders)
    order_item_index = build_order_item_index(order_items)
    picking_index = build_picking_index(picking)
    station_profiles = build_station_profiles()
    capacity_by_date = load_capacity_by_date()

    packing_records = []
    packing_id = PACKING_ID_START

    for order_id, order in order_index.items():
        items = order_item_index.get(order_id, [])
        picks = picking_index.get(order_id, [])

        if not items:
            raise ValueError(f"Order {order_id} has no order items.")
        if not picks:
            raise ValueError(f"Order {order_id} has no picking records.")

        article_count = len(items)
        total_quantity = sum(
            int(float(item["requested_quantity"])) for item in items
        )
        order_weight_kg = round(float(order["total_weight_kg"]), 3)
        picked_quantity = sum(
            int(float(pick["picked_quantity"])) for pick in picks
        )

        order_complete, missing_items = verify_order_completeness(
            order_items=items,
            picks=picks,
        )

        if not order_complete:
            raise ValueError(
                f"Order {order_id} is not fully picked. "
                f"Missing items: {missing_items[:10]}"
            )

        if picked_quantity != total_quantity:
            raise ValueError(
                f"Quantity mismatch for {order_id}: "
                f"expected {total_quantity}, picked {picked_quantity}"
            )

        packing_type = determine_packing_type(
            article_count=article_count,
            order_weight_kg=order_weight_kg,
        )
        packing_area = determine_packing_area(packing_type)
        station = assign_station(
            packing_type=packing_type,
            station_profiles=station_profiles,
        )
        station_capacity_factor = station_profiles[station]["capacity_factor"]

        package_type = determine_package_type(
            packing_type=packing_type,
            article_count=article_count,
            order_weight_kg=order_weight_kg,
            total_quantity=total_quantity,
        )

        primary_container, containers, container_type = determine_packing_container(picks)

        workload_units = calculate_workload_units(
            article_count=article_count,
            total_quantity=total_quantity,
            order_weight_kg=order_weight_kg,
            container_count=len(containers),
            packing_type=packing_type,
        )

        latest_pick_datetime = max(
            datetime.fromisoformat(pick["pick_datetime"]) for pick in picks
        )

        packing_started_at, packing_completed_at = generate_packing_timeline(
            latest_pick_datetime=latest_pick_datetime,
            packing_type=packing_type,
            article_count=article_count,
            total_quantity=total_quantity,
            order_weight_kg=order_weight_kg,
            container_count=len(containers),
            station_capacity_factor=station_capacity_factor,
            capacity_by_date=capacity_by_date,
        )

        packing_records.append(
            {
                "packing_id": f"PACK-{packing_id:06d}",
                "order_id": order_id,
                "packing_type": packing_type,
                "packing_area": packing_area,
                "packing_station": station,
                "station_capacity_factor": station_capacity_factor,
                "package_type": package_type,
                "workload_units": workload_units,
                "container_id": primary_container,
                "container_type": container_type,
                "container_count": len(containers),
                "article_count": article_count,
                "total_quantity": total_quantity,
                "order_weight_kg": order_weight_kg,
                "container_scan": "TRUE",
                "order_complete": "TRUE",
                "packing_status": "PACKED",
                "packing_started_at": packing_started_at.isoformat(timespec="seconds"),
                "packing_completed_at": packing_completed_at.isoformat(timespec="seconds"),
            }
        )

        packing_id += 1

        if len(packing_records) % 5_000 == 0:
            print(
                f"  Generated {len(packing_records):,} / "
                f"{len(orders):,} packing records..."
            )

    return packing_records


# ============================================================
# VALIDATION
# ============================================================

def validate_packing(packing_records, orders, order_items, picking):
    print()
    print("Validating packing...")

    order_ids = {order["order_id"] for order in orders}
    item_order_ids = {item["order_id"] for item in order_items}
    picking_order_ids = {pick["order_id"] for pick in picking}
    packing_order_ids = {row["order_id"] for row in packing_records}

    order_index = build_order_index(orders)
    picking_index = build_picking_index(picking)
    latest_pick_index = build_latest_pick_index(picking)

    assert len(packing_records) == len(orders)
    assert packing_order_ids == order_ids
    assert item_order_ids == order_ids
    assert picking_order_ids == order_ids
    assert len(packing_order_ids) == len(packing_records)

    packed_after_deadline = 0

    for row in packing_records:
        order_id = row["order_id"]
        order = order_index.get(order_id)
        assert order is not None

        article_count = int(row["article_count"])
        total_quantity = int(row["total_quantity"])
        weight = float(row["order_weight_kg"])

        assert article_count > 0
        assert total_quantity > 0
        assert weight > 0
        assert row["container_scan"] == "TRUE"
        assert row["container_id"].strip()
        assert int(row["container_count"]) > 0
        assert row["order_complete"] == "TRUE"

        packing_type = row["packing_type"]
        expected_packing_type = determine_packing_type(article_count, weight)
        assert packing_type == expected_packing_type, (
            f"Invalid packing classification for {order_id}: {packing_type}"
        )

        package_type = row["package_type"]
        assert package_type in PACKAGE_TYPES
        if weight > MAX_BOX_WEIGHT_KG:
            assert packing_type == "PALLET_SHIPMENT"
            assert package_type == "PALLET"
        else:
            assert packing_type in {"SMALL_PACKAGE", "LARGE_PACKAGE"}
            assert package_type in BOX_PACKAGE_TYPES

        assert float(row["station_capacity_factor"]) > 0
        assert float(row["workload_units"]) > 0

        if packing_type == "SMALL_PACKAGE":
            assert row["packing_area"] == "KLEIN_PACKEN"
            assert row["packing_station"] in SMALL_PACKING_STATIONS_HALL_1
        elif packing_type == "LARGE_PACKAGE":
            assert row["packing_area"] == "GROSS_PACKEN"
            assert row["packing_station"] in (
                LARGE_PACKING_STATIONS_HALL_1 + LARGE_PACKING_STATIONS_HALL_3
            )
        elif packing_type == "PALLET_SHIPMENT":
            assert row["packing_area"] == "PALLET_PACKING"
            assert row["packing_station"] in LARGE_PACKING_STATIONS_HALL_1

        assert row["packing_status"] in PACKING_STATUSES

        packing_started_at = datetime.fromisoformat(row["packing_started_at"])
        packing_completed_at = datetime.fromisoformat(row["packing_completed_at"])
        assert packing_completed_at > packing_started_at

        latest_pick_datetime = latest_pick_index[order_id]
        assert packing_started_at >= latest_pick_datetime

        requested_delivery_datetime = datetime.fromisoformat(
            order["requested_delivery_datetime"]
        )
        if packing_completed_at >= requested_delivery_datetime:
            packed_after_deadline += 1

        assert order_id in picking_index and len(picking_index[order_id]) > 0

    print(f"Orders packed at/after delivery deadline: {packed_after_deadline:,}")
    print("Packing validation passed.")


# ============================================================
# SUMMARY & EXPORT
# ============================================================

def print_packing_summary(packing_records):
    small = sum(r["packing_type"] == "SMALL_PACKAGE" for r in packing_records)
    large = sum(r["packing_type"] == "LARGE_PACKAGE" for r in packing_records)
    pallet = sum(r["packing_type"] == "PALLET_SHIPMENT" for r in packing_records)

    print()
    print("Warehouse Packing Summary")
    print("=========================")
    print(f"Packing records:       {len(packing_records):,}")
    print()
    print("Packing Type")
    print("------------")
    print(f"SMALL_PACKAGE          {small:,}")
    print(f"LARGE_PACKAGE          {large:,}")
    print(f"PALLET_SHIPMENT        {pallet:,}")

    station_counts = {}
    station_workload = {}
    station_weight = {}

    for row in packing_records:
        station = row["packing_station"]
        station_counts[station] = station_counts.get(station, 0) + 1
        station_workload[station] = station_workload.get(station, 0.0) + float(
            row["workload_units"]
        )
        station_weight[station] = station_weight.get(station, 0.0) + float(
            row["order_weight_kg"]
        )

    print()
    print("Packing Stations")
    print("----------------")
    for station in sorted(station_counts):
        print(
            f"{station:<18} "
            f"orders={station_counts[station]:,}  "
            f"workload={station_workload[station]:,.1f}  "
            f"weight={station_weight[station]:,.0f} kg"
        )

    print()
    print("Package Types")
    print("-------------")
    package_counts = {}
    for row in packing_records:
        pt = row["package_type"]
        package_counts[pt] = package_counts.get(pt, 0) + 1
    for pt in sorted(package_counts):
        print(f"{pt:<18} {package_counts[pt]:,}")


def export_packing(packing_records):
    fieldnames = [
        "packing_id",
        "order_id",
        "packing_type",
        "packing_area",
        "packing_station",
        "station_capacity_factor",
        "package_type",
        "workload_units",
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

    write_csv(PACKING_FILE, packing_records, fieldnames)
    print()
    print("Packing export complete:")
    print(PACKING_FILE)


def main():
    print()
    print("Warehouse Packing Generator")
    print("===========================")

    print("\nLoading orders...")
    orders = load_orders()
    print(f"Orders loaded: {len(orders):,}")

    print("\nLoading order items...")
    order_items = load_order_items()
    print(f"Order items loaded: {len(order_items):,}")

    print("\nLoading picking...")
    picking = load_picking()
    print(f"Picking records loaded: {len(picking):,}")

    print("\nGenerating packing records...")
    packing_records = generate_packing_records(
        orders=orders,
        order_items=order_items,
        picking=picking,
    )
    print(f"Packing records generated: {len(packing_records):,}")

    validate_packing(
        packing_records=packing_records,
        orders=orders,
        order_items=order_items,
        picking=picking,
    )

    print_packing_summary(packing_records)
    export_packing(packing_records)
    print("\nPacking generation completed successfully.")


if __name__ == "__main__":
    main()