from pathlib import Path
import csv
import random
from datetime import datetime, timedelta

from working_time import (
    add_working_duration,
    is_open,
    load_capacity_by_date,
    next_working_datetime,
)


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


# ============================================================
# PACKING RULES
# ============================================================

SMALL_ARTICLE_MIN = 1
SMALL_ARTICLE_MAX = 4

LARGE_ARTICLE_MIN = 5

LARGE_PACKAGE_MAX_WEIGHT_KG = 30.0

# Synthetic package categories. Actual dimensions for boxes 201/202/203
# will be added after physical measurement.
PACKAGE_TYPES = [
    "BOX_201",
    "BOX_202",
    "BOX_203",
    "PALLET",
]


# ============================================================
# PACKING STATIONS
# ============================================================

# Hall 1:
# 5 Klein Packen stations

SMALL_PACKING_STATIONS_HALL_1 = [
    f"H1-KP-{i:02d}"
    for i in range(1, 6)
]


# Hall 1:
# 9 Groß Packen / pallet stations

LARGE_PACKING_STATIONS_HALL_1 = [
    f"H1-GP-{i:02d}"
    for i in range(1, 10)
]


# Hall 3:
# 2 Groß Packen stations

LARGE_PACKING_STATIONS_HALL_3 = [
    f"H3-GP-{i:02d}"
    for i in range(1, 3)
]


# ============================================================
# STATUS
# ============================================================

PACKING_STATUSES = [
    "PACKED",
]


# ============================================================
# OPERATIONAL TIMELINE
# ============================================================

PACKING_START_DELAY_MINUTES = (
    5,
    30,
)

PACKING_DURATION_MINUTES = (
    3,
    20,
)

PALLET_EXTRA_DURATION_MINUTES = (
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


def write_csv(
    file_path,
    rows,
    fieldnames,
):
    """
    Write rows to CSV.
    """

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

        writer.writerows(
            rows
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
            "orders.csv is empty."
        )

    required = {
        "order_id",
        "order_datetime",
        "requested_delivery_datetime",
        "total_items",
        "total_weight_kg",
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
            "order_items.csv is empty."
        )

    required = {
        "order_item_id",
        "order_id",
        "product_id",
        "requested_quantity",
        "total_weight_kg",
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
# LOAD PICKING
# ============================================================

def load_picking():

    picking = read_csv(
        PICKING_FILE
    )

    if not picking:

        raise ValueError(
            "picking.csv is empty."
        )

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

    missing = (
        required
        - set(picking[0].keys())
    )

    if missing:

        raise ValueError(
            f"Picking missing fields: {missing}"
        )

    return picking


# ============================================================
# INDEXES
# ============================================================

def build_order_index(
    orders,
):

    return {
        row["order_id"]: row
        for row in orders
    }


def build_order_item_index(
    order_items,
):
    """
    Build:

        order_id -> order items
    """

    index = {}

    for item in order_items:

        index.setdefault(
            item["order_id"],
            [],
        ).append(
            item
        )

    return index


def build_picking_index(
    picking,
):
    """
    Build:

        order_id -> picking records
    """

    index = {}

    for pick in picking:

        index.setdefault(
            pick["order_id"],
            [],
        ).append(
            pick
        )

    return index


def build_latest_pick_index(
    picking,
):
    """
    Build:

        order_id -> latest pick datetime
    """

    latest_pick = {}

    for pick in picking:

        order_id = pick[
            "order_id"
        ]

        pick_datetime = datetime.fromisoformat(
            pick[
                "pick_datetime"
            ]
        )

        previous = latest_pick.get(
            order_id
        )

        if (
            previous is None
            or pick_datetime > previous
        ):

            latest_pick[
                order_id
            ] = pick_datetime

    return latest_pick


def build_delivery_deadline_index(
    orders,
):
    """
    Build:

        order_id -> requested delivery datetime
    """

    return {
        order["order_id"]: datetime.fromisoformat(
            order[
                "requested_delivery_datetime"
            ]
        )
        for order in orders
    }


# ============================================================
# PACKING RULES
# ============================================================

def determine_packing_type(
    article_count,
    order_weight_kg,
):
    """
    Packing rules:

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


def determine_packing_area(
    packing_type,
):
    """
    Map packing type to operational area.
    """

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

def build_station_profiles():
    """
    Build synthetic station capacity profiles.

    The values represent relative processing capacity, not measured
    real-world performance. They intentionally create realistic
    operational variation between stations instead of assigning an
    identical number of orders to every station.
    """

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
    """Return stations that can process the packing type."""

    if packing_type == "SMALL_PACKAGE":
        return SMALL_PACKING_STATIONS_HALL_1

    if packing_type == "LARGE_PACKAGE":
        return (
            LARGE_PACKING_STATIONS_HALL_1
            + LARGE_PACKING_STATIONS_HALL_3
        )

    if packing_type == "PALLET_SHIPMENT":
        return LARGE_PACKING_STATIONS_HALL_1

    raise ValueError(
        f"Unknown packing type: {packing_type}"
    )


def assign_station(
    packing_type,
    station_profiles,
):
    """
    Assign a packing station using station capacity.

    Assignment is weighted by the synthetic station capacity profile.
    This creates controlled workload variation while keeping the
    distribution operationally plausible.
    """

    stations = get_eligible_stations(
        packing_type
    )

    weights = [
        station_profiles[station]["capacity_factor"]
        for station in stations
    ]

    return random.choices(
        stations,
        weights=weights,
        k=1,
    )[0]


def determine_package_type(
    packing_type,
    article_count,
    order_weight_kg,
    total_quantity,
):
    """
    Determine synthetic package size/type.

    BOX_201 = small box
    BOX_202 = medium box
    BOX_203 = large box
    PALLET  = pallet shipment

    Actual box dimensions are intentionally not invented here.
    """

    if packing_type == "PALLET_SHIPMENT":
        return "PALLET"

    if packing_type == "SMALL_PACKAGE":
        if (
            order_weight_kg <= 8
            and article_count <= 2
            and total_quantity <= 12
        ):
            return "BOX_201"

        if (
            order_weight_kg <= 18
            and article_count <= 3
        ):
            return "BOX_202"

        return "BOX_203"

    if packing_type == "LARGE_PACKAGE":
        if (
            order_weight_kg <= 15
            and total_quantity <= 40
        ):
            return "BOX_202"

        return "BOX_203"

    raise ValueError(
        f"Unknown packing type: {packing_type}"
    )


def calculate_workload_units(
    article_count,
    total_quantity,
    order_weight_kg,
    container_count,
    packing_type,
):
    """
    Calculate a synthetic packing workload score.

    This is not a measured physical unit. It is an analytical workload
    metric used to compare stations fairly when orders differ in size,
    quantity and complexity.
    """

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

    return round(
        max(workload, 1.0),
        2,
    )


# ============================================================
# CONTAINER SCAN
# ============================================================

def determine_packing_container(
    picks,
):
    """
    Determine the primary picking container.

    If an order has multiple containers,
    the first container is used as the primary
    scanned container.

    The total number of containers is retained.
    """

    containers = []

    container_types = {}

    for pick in picks:

        container_id = str(
            pick[
                "container_id"
            ]
        ).strip()

        if not container_id:

            continue

        if container_id not in containers:

            containers.append(
                container_id
            )

        container_types[
            container_id
        ] = str(
            pick[
                "container_type"
            ]
        ).strip().upper()

    if not containers:

        raise ValueError(
            "Order has no picking container."
        )

    primary_container = (
        containers[0]
    )

    primary_container_type = (
        container_types[
            primary_container
        ]
    )

    return (
        primary_container,
        containers,
        primary_container_type,
    )


# ============================================================
# COMPLETENESS CHECK
# ============================================================

def verify_order_completeness(
    order_items,
    picks,
):
    """
    Verify that all requested quantities were picked.

    Returns:

        (
            complete,
            missing_items
        )
    """

    requested_by_item = {}

    for item in order_items:

        order_item_id = item[
            "order_item_id"
        ]

        requested_by_item[
            order_item_id
        ] = int(
            float(
                item[
                    "requested_quantity"
                ]
            )
        )

    picked_by_item = {}

    for pick in picks:

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
                float(
                    pick[
                        "picked_quantity"
                    ]
                )
            )
        )

    missing_items = []

    for (
        order_item_id,
        requested_quantity,
    ) in requested_by_item.items():

        picked_quantity = (
            picked_by_item.get(
                order_item_id,
                0,
            )
        )

        if (
            picked_quantity
            < requested_quantity
        ):

            missing_items.append(
                order_item_id
            )

    return (
        len(
            missing_items
        ) == 0,
        missing_items,
    )


# ============================================================
# PACKING TIMELINE
# ============================================================

def generate_packing_timeline(
    latest_pick_datetime,
    requested_delivery_datetime,
    packing_type,
    article_count,
    total_quantity,
    order_weight_kg,
    container_count,
    station_capacity_factor,
):
    """
    Generate a PROVISIONAL packing timeline.

    Start = latest pick + a small delay. Duration depends on the
    order and the station speed. The real timestamps (working
    hours, waiting for a busy station) are set afterwards by
    schedule_packing(), which needs all orders at once.

    The delivery deadline is no longer enforced here: if picking
    and packing are slow, the order is late, and shipping reports
    it. requested_delivery_datetime is kept in the signature so
    existing calls keep working.
    """

    base_duration = random.randint(
        *PACKING_DURATION_MINUTES
    )

    complexity_minutes = (
        article_count * 0.8
        + total_quantity * 0.02
        + order_weight_kg * 0.03
        + container_count * 1.5
    )

    if packing_type == "LARGE_PACKAGE":
        complexity_minutes += 4

    elif packing_type == "PALLET_SHIPMENT":
        complexity_minutes += random.randint(
            *PALLET_EXTRA_DURATION_MINUTES
        )

    duration_minutes = (
        base_duration
        + complexity_minutes
    ) / max(
        station_capacity_factor,
        0.50,
    )

    duration_minutes = max(
        2.0,
        min(
            duration_minutes,
            90.0,
        ),
    )

    start = (
        latest_pick_datetime
        + timedelta(
            minutes=random.randint(
                *PACKING_START_DELAY_MINUTES
            )
        )
    )

    return (
        start,
        start + timedelta(
            seconds=int(duration_minutes * 60)
        ),
    )


# ============================================================
# WORKING TIME + STATION QUEUE
# ============================================================

_CAPACITY_BY_DATE = None


def get_capacity_by_date():
    """Working days from calendar.csv (loaded once)."""

    global _CAPACITY_BY_DATE

    if _CAPACITY_BY_DATE is None:
        _CAPACITY_BY_DATE = load_capacity_by_date()

    return _CAPACITY_BY_DATE


def schedule_packing(packing_records):
    """
    Phase 2 of packing generation.

    Every station packs one order at a time. Orders are handled in
    the order they become ready (latest pick + delay, moved into
    working time). If the station is still busy, the order waits.
    Working time (shifts, weekends, holidays) does not count as
    packing time.

    Modifies packing_started_at / packing_completed_at in place.
    """

    capacity_by_date = get_capacity_by_date()

    jobs = []

    for record in packing_records:
        provisional_start = datetime.fromisoformat(
            record["packing_started_at"]
        )
        provisional_end = datetime.fromisoformat(
            record["packing_completed_at"]
        )

        jobs.append(
            (
                next_working_datetime(
                    provisional_start,
                    capacity_by_date,
                ),
                record["packing_id"],
                record,
                provisional_end - provisional_start,
            )
        )

    jobs.sort(
        key=lambda job: (job[0], job[1])
    )

    station_free_at = {}

    for ready_at, _, record, duration in jobs:
        station = record["packing_station"]

        start = next_working_datetime(
            max(
                ready_at,
                station_free_at.get(
                    station,
                    ready_at,
                ),
            ),
            capacity_by_date,
        )

        end = add_working_duration(
            start,
            duration,
            capacity_by_date,
        )

        station_free_at[station] = end

        record["packing_started_at"] = start.isoformat(
            timespec="seconds"
        )
        record["packing_completed_at"] = end.isoformat(
            timespec="seconds"
        )

    return packing_records


# ============================================================
# PACKING GENERATION
# ============================================================

def generate_packing_records(
    orders,
    order_items,
    picking,
):
    """
    Generate one packing record per order.

    Workflow:

        Order
          ↓
        Order Items
          ↓
        Picking
          ↓
        Container Scan
          ↓
        Completeness Check
          ↓
        Packing Type
          ↓
        Packing Station
          ↓
        Packed
    """

    order_index = (
        build_order_index(
            orders
        )
    )

    order_item_index = (
        build_order_item_index(
            order_items
        )
    )

    picking_index = (
        build_picking_index(
            picking
        )
    )

    station_profiles = build_station_profiles()

    packing_records = []

    packing_id = PACKING_ID_START

    for order_id, order in (
        order_index.items()
    ):

        items = (
            order_item_index.get(
                order_id,
                [],
            )
        )

        picks = (
            picking_index.get(
                order_id,
                [],
            )
        )

        if not items:

            raise ValueError(
                f"Order {order_id} "
                "has no order items."
            )

        if not picks:

            raise ValueError(
                f"Order {order_id} "
                "has no picking records."
            )

        # ----------------------------------------------------
        # Article count.
        #
        # Article count = number of order lines.
        # ----------------------------------------------------

        article_count = len(
            items
        )

        # ----------------------------------------------------
        # Total requested quantity.
        # ----------------------------------------------------

        total_quantity = sum(
            int(
                float(
                    item[
                        "requested_quantity"
                    ]
                )
            )
            for item in items
        )

        # ----------------------------------------------------
        # Order weight.
        # ----------------------------------------------------

        order_weight_kg = round(
            float(
                order[
                    "total_weight_kg"
                ]
            ),
            3,
        )

        # ----------------------------------------------------
        # Total picked quantity.
        # ----------------------------------------------------

        picked_quantity = sum(
            int(
                float(
                    pick[
                        "picked_quantity"
                    ]
                )
            )
            for pick in picks
        )

        expected_quantity = (
            total_quantity
        )

        # ----------------------------------------------------
        # Completeness check.
        # ----------------------------------------------------

        (
            order_complete,
            missing_items,
        ) = verify_order_completeness(
            order_items=items,
            picks=picks,
        )

        if not order_complete:

            raise ValueError(
                f"Order {order_id} "
                "is not fully picked. "
                f"Missing items: "
                f"{missing_items[:10]}"
            )

        if (
            picked_quantity
            != expected_quantity
        ):

            raise ValueError(
                f"Quantity mismatch for "
                f"{order_id}: "
                f"expected {expected_quantity}, "
                f"picked {picked_quantity}"
            )

        # ----------------------------------------------------
        # Packing type.
        # ----------------------------------------------------

        packing_type = (
            determine_packing_type(
                article_count=article_count,
                order_weight_kg=order_weight_kg,
            )
        )

        # ----------------------------------------------------
        # Packing area.
        # ----------------------------------------------------

        packing_area = (
            determine_packing_area(
                packing_type
            )
        )

        # ----------------------------------------------------
        # Packing station.
        # ----------------------------------------------------

        station = assign_station(
            packing_type=packing_type,
            station_profiles=station_profiles,
        )

        station_capacity_factor = station_profiles[
            station
        ][
            "capacity_factor"
        ]

        package_type = determine_package_type(
            packing_type=packing_type,
            article_count=article_count,
            order_weight_kg=order_weight_kg,
            total_quantity=total_quantity,
        )

        # ----------------------------------------------------
        # Container scan.
        # ----------------------------------------------------

        (
            primary_container,
            containers,
            container_type,
        ) = determine_packing_container(
            picks
        )

        workload_units = calculate_workload_units(
            article_count=article_count,
            total_quantity=total_quantity,
            order_weight_kg=order_weight_kg,
            container_count=len(containers),
            packing_type=packing_type,
        )

        container_scan = True

        # ----------------------------------------------------
        # Latest pick.
        # ----------------------------------------------------

        pick_datetimes = [
            datetime.fromisoformat(
                pick[
                    "pick_datetime"
                ]
            )
            for pick in picks
        ]

        latest_pick_datetime = max(
            pick_datetimes
        )

        # ----------------------------------------------------
        # Requested delivery deadline.
        # ----------------------------------------------------

        requested_delivery_datetime = (
            datetime.fromisoformat(
                order[
                    "requested_delivery_datetime"
                ]
            )
        )

        # ----------------------------------------------------
        # Generate safe packing timeline.
        # ----------------------------------------------------

        (
            packing_started_at,
            packing_completed_at,
        ) = generate_packing_timeline(
            latest_pick_datetime=(
                latest_pick_datetime
            ),
            requested_delivery_datetime=(
                requested_delivery_datetime
            ),
            packing_type=packing_type,
            article_count=article_count,
            total_quantity=total_quantity,
            order_weight_kg=order_weight_kg,
            container_count=len(containers),
            station_capacity_factor=station_capacity_factor,
        )

        # ----------------------------------------------------
        # Create packing record.
        # ----------------------------------------------------

        packing_records.append(
            {
                "packing_id": (
                    f"PACK-{packing_id:06d}"
                ),
                "order_id": (
                    order_id
                ),
                "packing_type": (
                    packing_type
                ),
                "packing_area": (
                    packing_area
                ),
                "packing_station": (
                    station
                ),
                "station_capacity_factor": (
                    station_capacity_factor
                ),
                "package_type": (
                    package_type
                ),
                "workload_units": (
                    workload_units
                ),
                "container_id": (
                    primary_container
                ),
                "container_type": (
                    container_type
                ),
                "container_count": (
                    len(containers)
                ),
                "article_count": (
                    article_count
                ),
                "total_quantity": (
                    total_quantity
                ),
                "order_weight_kg": (
                    order_weight_kg
                ),
                "container_scan": (
                    str(
                        container_scan
                    ).upper()
                ),
                "order_complete": (
                    str(
                        order_complete
                    ).upper()
                ),
                "packing_status": (
                    "PACKED"
                ),
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

        # ----------------------------------------------------
        # Progress.
        # ----------------------------------------------------

        if (
            len(packing_records) % 5_000
            == 0
        ):

            print(
                f"  Generated "
                f"{len(packing_records):,} / "
                f"{len(orders):,} packing records..."
            )

    return schedule_packing(
        packing_records
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_packing(
    packing_records,
    orders,
    order_items,
    picking,
):
    """
    Validate packing records.

    Uses pre-built indexes to avoid repeatedly
    scanning the complete picking dataset.
    """

    print()
    print(
        "Validating packing..."
    )

    # --------------------------------------------------------
    # Build indexes once.
    # --------------------------------------------------------

    order_ids = {
        order[
            "order_id"
        ]
        for order in orders
    }

    item_order_ids = {
        item[
            "order_id"
        ]
        for item in order_items
    }

    picking_order_ids = {
        pick[
            "order_id"
        ]
        for pick in picking
    }

    packing_order_ids = {
        row[
            "order_id"
        ]
        for row in packing_records
    }

    order_index = (
        build_order_index(
            orders
        )
    )

    picking_index = (
        build_picking_index(
            picking
        )
    )

    latest_pick_index = (
        build_latest_pick_index(
            picking
        )
    )

    delivery_deadline_index = (
        build_delivery_deadline_index(
            orders
        )
    )

    # --------------------------------------------------------
    # Record count.
    # --------------------------------------------------------

    assert (
        len(packing_records)
        == len(orders)
    ), (
        "Packing record count does not "
        "match order count."
    )

    # --------------------------------------------------------
    # Order coverage.
    # --------------------------------------------------------

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
        "Some orders are missing "
        "order items."
    )

    assert (
        picking_order_ids
        == order_ids
    ), (
        "Some orders are missing "
        "picking records."
    )

    # --------------------------------------------------------
    # One packing record per order.
    # --------------------------------------------------------

    assert (
        len(packing_order_ids)
        == len(packing_records)
    ), (
        "Duplicate packing records detected."
    )

    packing_after_deadline = 0

    # --------------------------------------------------------
    # Validate every packing record.
    # --------------------------------------------------------

    for row in packing_records:

        order_id = row[
            "order_id"
        ]

        order = order_index.get(
            order_id
        )

        assert (
            order is not None
        ), (
            f"Unknown order: "
            f"{order_id}"
        )

        article_count = int(
            row[
                "article_count"
            ]
        )

        total_quantity = int(
            row[
                "total_quantity"
            ]
        )

        weight = float(
            row[
                "order_weight_kg"
            ]
        )

        # ----------------------------------------------------
        # Basic validation.
        # ----------------------------------------------------

        assert (
            article_count > 0
        ), (
            f"Invalid article count "
            f"for {order_id}"
        )

        assert (
            total_quantity > 0
        ), (
            f"Invalid quantity "
            f"for {order_id}"
        )

        assert (
            weight > 0
        ), (
            f"Invalid weight "
            f"for {order_id}"
        )

        # ----------------------------------------------------
        # Container.
        # ----------------------------------------------------

        assert (
            row[
                "container_scan"
            ]
            == "TRUE"
        ), (
            f"Container was not scanned "
            f"for {order_id}"
        )

        assert (
            row[
                "container_id"
            ].strip()
        ), (
            f"Missing container ID "
            f"for {order_id}"
        )

        assert (
            int(
                row[
                    "container_count"
                ]
            )
            > 0
        ), (
            f"Invalid container count "
            f"for {order_id}"
        )

        # ----------------------------------------------------
        # Completeness.
        # ----------------------------------------------------

        assert (
            row[
                "order_complete"
            ]
            == "TRUE"
        ), (
            f"Order is incomplete "
            f"for {order_id}"
        )

        # ----------------------------------------------------
        # Packing classification.
        # ----------------------------------------------------

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
                f"{order_id}"
            )

        elif weight <= 30:

            assert (
                packing_type
                == "LARGE_PACKAGE"
            ), (
                f"Invalid large-package "
                f"classification for "
                f"{order_id}"
            )

        else:

            assert (
                packing_type
                == "PALLET_SHIPMENT"
            ), (
                f"Invalid pallet classification "
                f"for {order_id}"
            )

        # ----------------------------------------------------
        # Package type and workload.
        # ----------------------------------------------------

        package_type = row[
            "package_type"
        ]

        assert package_type in PACKAGE_TYPES, (
            f"Invalid package type for {order_id}: "
            f"{package_type}"
        )

        if packing_type == "PALLET_SHIPMENT":
            assert package_type == "PALLET", (
                f"Invalid pallet package type for {order_id}"
            )
        else:
            assert package_type in {
                "BOX_201",
                "BOX_202",
                "BOX_203",
            }, (
                f"Invalid box package type for {order_id}"
            )

        assert float(
            row["station_capacity_factor"]
        ) > 0, (
            f"Invalid station capacity factor for {order_id}"
        )

        assert float(
            row["workload_units"]
        ) > 0, (
            f"Invalid workload units for {order_id}"
        )

        # ----------------------------------------------------
        # Packing area and station.
        # ----------------------------------------------------

        if (
            packing_type
            == "SMALL_PACKAGE"
        ):

            assert (
                row[
                    "packing_area"
                ]
                == "KLEIN_PACKEN"
            )

            assert (
                row[
                    "packing_station"
                ]
                in SMALL_PACKING_STATIONS_HALL_1
            )

        elif (
            packing_type
            == "LARGE_PACKAGE"
        ):

            assert (
                row[
                    "packing_area"
                ]
                == "GROSS_PACKEN"
            )

            assert (
                row[
                    "packing_station"
                ]
                in (
                    LARGE_PACKING_STATIONS_HALL_1
                    + LARGE_PACKING_STATIONS_HALL_3
                )
            )

        elif (
            packing_type
            == "PALLET_SHIPMENT"
        ):

            assert (
                row[
                    "packing_area"
                ]
                == "PALLET_PACKING"
            )

            assert (
                row[
                    "packing_station"
                ]
                in LARGE_PACKING_STATIONS_HALL_1
            )

        # ----------------------------------------------------
        # Status.
        # ----------------------------------------------------

        assert (
            row[
                "packing_status"
            ]
            in PACKING_STATUSES
        ), (
            f"Invalid packing status "
            f"for {order_id}"
        )

        # ----------------------------------------------------
        # Timestamps.
        # ----------------------------------------------------

        packing_started_at = (
            datetime.fromisoformat(
                row[
                    "packing_started_at"
                ]
            )
        )

        packing_completed_at = (
            datetime.fromisoformat(
                row[
                    "packing_completed_at"
                ]
            )
        )

        assert (
            packing_completed_at
            > packing_started_at
        ), (
            f"Invalid packing timestamps "
            f"for {order_id}"
        )

        # ----------------------------------------------------
        # Delivery deadline.
        # ----------------------------------------------------

        requested_delivery_datetime = (
            delivery_deadline_index[
                order_id
            ]
        )

        # Lateness is allowed (queue / backlog); only count it.
        if packing_completed_at >= requested_delivery_datetime:
            packing_after_deadline += 1

        assert is_open(
            packing_started_at
        ), (
            f"Packing starts outside working hours "
            f"for {order_id}"
        )

        # ----------------------------------------------------
        # Packing starts after picking.
        # ----------------------------------------------------

        latest_pick_datetime = (
            latest_pick_index[
                order_id
            ]
        )

        assert (
            packing_started_at
            >= latest_pick_datetime
        ), (
            f"Packing starts before "
            f"picking is complete for "
            f"{order_id}"
        )

        # ----------------------------------------------------
        # Picking exists.
        # ----------------------------------------------------

        assert (
            order_id
            in picking_index
        ), (
            f"No picking records "
            f"for {order_id}"
        )

        assert (
            len(
                picking_index[
                    order_id
                ]
            )
            > 0
        )

    print(
        f"Packing completed after delivery deadline: "
        f"{packing_after_deadline:,}"
    )

    print(
        "Packing validation passed."
    )


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

        if (
            packing_type
            == "SMALL_PACKAGE"
        ):

            small += 1

        elif (
            packing_type
            == "LARGE_PACKAGE"
        ):

            large += 1

        elif (
            packing_type
            == "PALLET_SHIPMENT"
        ):

            pallet += 1

    print()
    print(
        "Warehouse Packing Summary"
    )
    print(
        "========================="
    )

    print(
        f"Packing records:       "
        f"{len(packing_records):,}"
    )

    print()
    print(
        "Packing Type"
    )
    print(
        "------------"
    )

    print(
        f"SMALL_PACKAGE      "
        f"{small:,}"
    )

    print(
        f"LARGE_PACKAGE      "
        f"{large:,}"
    )

    print(
        f"PALLET_SHIPMENT    "
        f"{pallet:,}"
    )

    # --------------------------------------------------------
    # Station workload summary.
    # --------------------------------------------------------

    station_counts = {}
    station_workload = {}
    station_weight = {}

    for row in packing_records:

        station = row[
            "packing_station"
        ]

        station_counts[station] = (
            station_counts.get(
                station,
                0,
            ) + 1
        )

        station_workload[station] = (
            station_workload.get(
                station,
                0.0,
            ) + float(
                row[
                    "workload_units"
                ]
            )
        )

        station_weight[station] = (
            station_weight.get(
                station,
                0.0,
            ) + float(
                row[
                    "order_weight_kg"
                ]
            )
        )

    print()
    print(
        "Packing Stations"
    )
    print(
        "----------------"
    )

    for station in sorted(
        station_counts
    ):

        print(
            f"{station:<18} "
            f"orders={station_counts[station]:,}  "
            f"workload={station_workload[station]:,.1f}  "
            f"weight={station_weight[station]:,.0f} kg"
        )

    print()
    print(
        "Package Types"
    )
    print(
        "-------------"
    )

    package_counts = {}

    for row in packing_records:

        package_type = row[
            "package_type"
        ]

        package_counts[package_type] = (
            package_counts.get(
                package_type,
                0,
            ) + 1
        )

    for package_type in sorted(
        package_counts
    ):

        print(
            f"{package_type:<18} "
            f"{package_counts[package_type]:,}"
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
    print(
        "Warehouse Packing Generator"
    )
    print(
        "==========================="
    )

    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    print()
    print(
        "Loading orders..."
    )

    orders = load_orders()

    print(
        f"Orders loaded: "
        f"{len(orders):,}"
    )

    # --------------------------------------------------------
    # Order items
    # --------------------------------------------------------

    print()
    print(
        "Loading order items..."
    )

    order_items = load_order_items()

    print(
        f"Order items loaded: "
        f"{len(order_items):,}"
    )

    # --------------------------------------------------------
    # Picking
    # --------------------------------------------------------

    print()
    print(
        "Loading picking..."
    )

    picking = load_picking()

    print(
        f"Picking records loaded: "
        f"{len(picking):,}"
    )

    # --------------------------------------------------------
    # Generate packing.
    # --------------------------------------------------------

    print()
    print(
        "Generating packing records..."
    )

    packing_records = (
        generate_packing_records(
            orders=orders,
            order_items=order_items,
            picking=picking,
        )
    )

    print(
        f"Packing records generated: "
        f"{len(packing_records):,}"
    )

    # --------------------------------------------------------
    # Validate.
    # --------------------------------------------------------

    validate_packing(
        packing_records=packing_records,
        orders=orders,
        order_items=order_items,
        picking=picking,
    )

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    print_packing_summary(
        packing_records
    )

    # --------------------------------------------------------
    # Export.
    # --------------------------------------------------------

    export_packing(
        packing_records
    )

    print()
    print(
        "Packing generation completed successfully."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()