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


# ============================================================
# PACKING RULES
# ============================================================

SMALL_ARTICLE_MIN = 1
SMALL_ARTICLE_MAX = 4

LARGE_ARTICLE_MIN = 5

LARGE_PACKAGE_MAX_WEIGHT_KG = 30.0


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

def assign_station(
    packing_type,
    station_counters,
):
    """
    Round-robin station assignment.

    SMALL_PACKAGE:
        Hall 1 Klein Packen

    LARGE_PACKAGE:
        Hall 1 + Hall 3 Groß Packen

    PALLET_SHIPMENT:
        Hall 1 large / pallet stations
    """

    if packing_type == "SMALL_PACKAGE":

        stations = (
            SMALL_PACKING_STATIONS_HALL_1
        )

        key = "SMALL"

    elif packing_type == "LARGE_PACKAGE":

        stations = (
            LARGE_PACKING_STATIONS_HALL_1
            + LARGE_PACKING_STATIONS_HALL_3
        )

        key = "LARGE"

    elif packing_type == "PALLET_SHIPMENT":

        stations = (
            LARGE_PACKING_STATIONS_HALL_1
        )

        key = "PALLET"

    else:

        raise ValueError(
            f"Unknown packing type: {packing_type}"
        )

    counter = station_counters[
        key
    ]

    station = stations[
        counter % len(stations)
    ]

    station_counters[
        key
    ] += 1

    return station


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
):
    """
    Generate a packing timeline.

    Normal orders use the configured operational delay and
    duration.

    Tight-deadline orders use a compressed synthetic timeline:
    packing starts immediately after the latest pick and the
    packing duration is reduced to fit strictly before the
    delivery deadline.

    This is necessary because the dataset contains historical
    orders where the latest pick can be very close to the
    requested delivery deadline.
    """

    # --------------------------------------------------------
    # Validate the available window.
    # --------------------------------------------------------

    available_seconds = (
        requested_delivery_datetime
        - latest_pick_datetime
    ).total_seconds()

    if available_seconds <= 0:
        raise ValueError(
            f"Invalid packing window. "
            f"Latest pick: "
            f"{latest_pick_datetime.isoformat()}, "
            f"Delivery deadline: "
            f"{requested_delivery_datetime.isoformat()}, "
            f"Available seconds: "
            f"{available_seconds:.0f}"
        )

    # --------------------------------------------------------
    # Generate the normal packing duration.
    # --------------------------------------------------------

    normal_duration_minutes = random.randint(
        *PACKING_DURATION_MINUTES
    )

    if (
        packing_type
        == "PALLET_SHIPMENT"
    ):

        normal_duration_minutes += random.randint(
            *PALLET_EXTRA_DURATION_MINUTES
        )

    normal_duration_seconds = (
        normal_duration_minutes * 60
    )

    # --------------------------------------------------------
    # Normal operational timeline.
    # --------------------------------------------------------

    normal_delay_minutes = random.randint(
        *PACKING_START_DELAY_MINUTES
    )

    normal_start = (
        latest_pick_datetime
        + timedelta(
            minutes=normal_delay_minutes
        )
    )

    normal_completion = (
        normal_start
        + timedelta(
            seconds=normal_duration_seconds
        )
    )

    if (
        normal_completion
        < requested_delivery_datetime
    ):

        return (
            normal_start,
            normal_completion,
        )

    # --------------------------------------------------------
    # Tight-deadline timeline.
    #
    # We must not move packing before the latest pick.
    # Instead, compress the packing operation.
    #
    # Example:
    #
    # latest pick     03:46:23
    # deadline        03:47:23
    #
    # available       60 seconds
    #
    # packing starts  03:46:23
    # packing ends    03:47:22
    # --------------------------------------------------------

    compressed_start = (
        latest_pick_datetime
    )

    # Always leave at least one second before the delivery
    # deadline because validation requires:
    #
    # packing_completed_at < requested_delivery_datetime
    #
    max_duration_seconds = int(
        available_seconds
    ) - 1

    if max_duration_seconds < 1:
        raise ValueError(
            f"No valid time remains for packing before "
            f"delivery deadline. "
            f"Latest pick: "
            f"{latest_pick_datetime.isoformat()}, "
            f"Delivery deadline: "
            f"{requested_delivery_datetime.isoformat()}, "
            f"Available seconds: "
            f"{available_seconds:.0f}"
        )

    # Use the normal duration whenever possible.
    # Otherwise compress it to the available window.
    compressed_duration_seconds = min(
        normal_duration_seconds,
        max_duration_seconds,
    )

    compressed_completion = (
        compressed_start
        + timedelta(
            seconds=compressed_duration_seconds
        )
    )

    # --------------------------------------------------------
    # Final safety checks.
    # --------------------------------------------------------

    if (
        compressed_completion
        <= compressed_start
    ):
        raise ValueError(
            "Packing duration must be positive."
        )

    if (
        compressed_completion
        >= requested_delivery_datetime
    ):
        raise ValueError(
            f"Packing timeline could not be resolved. "
            f"Packing completion: "
            f"{compressed_completion.isoformat()}, "
            f"Delivery deadline: "
            f"{requested_delivery_datetime.isoformat()}"
        )

    return (
        compressed_start,
        compressed_completion,
    )


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

    station_counters = {
        "SMALL": 0,
        "LARGE": 0,
        "PALLET": 0,
    }

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
            station_counters=(
                station_counters
            ),
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

        assert (
            packing_completed_at
            < requested_delivery_datetime
        ), (
            f"Packing finishes after "
            f"delivery deadline for "
            f"{order_id}"
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
    # Station utilization.
    # --------------------------------------------------------

    station_counts = {}

    for row in packing_records:

        station = row[
            "packing_station"
        ]

        station_counts[
            station
        ] = (
            station_counts.get(
                station,
                0,
            )
            + 1
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