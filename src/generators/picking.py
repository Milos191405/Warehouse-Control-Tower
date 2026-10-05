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

def build_location_index(
    locations,
):

    return {
        row["location_id"]: row
        for row in locations
    }


def build_inventory_index(
    inventory,
):
    """
    Build:

        product_id -> inventory records

    A product may exist at multiple warehouse locations.
    """

    index = {}

    for row in inventory:

        product_id = row[
            "product_id"
        ]

        index.setdefault(
            product_id,
            [],
        ).append(
            row
        )

    return index


def build_order_index(
    orders,
):

    return {
        row["order_id"]: row
        for row in orders
    }


# ============================================================
# TIMELINE HELPERS
# ============================================================

def parse_order_datetime(
    order,
):

    try:

        return datetime.fromisoformat(
            order[
                "order_datetime"
            ]
        )

    except (
        KeyError,
        ValueError,
    ) as exc:

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

    The inventory snapshot represents the warehouse state
    used to determine where a product can be picked from.

    Prefer a location with enough quantity.

    Otherwise choose the location with the largest
    reference quantity.
    """

    candidates = []

    for record in inventory_records:

        location_id = record[
            "location_id"
        ]

        if (
            location_id
            not in location_index
        ):

            continue

        try:

            available = int(
                float(
                    record[
                        "quantity"
                    ]
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            continue

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
        pair
        for pair in candidates
        if pair[1] >= requested_quantity
    ]

    if sufficient:

        return random.choice(
            sufficient
        )[0]

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

    One order item may generate multiple picking records when
    the requested quantity is represented across multiple
    inventory locations.

    Inventory is NOT consumed globally because this dataset is
    a historical simulation using the inventory snapshot as a
    warehouse-location reference.

    Picking timestamps are assigned per order after all picking
    records for that order are known. This guarantees:

        order_datetime
            <= first pick
            < subsequent picks
            < requested_delivery_datetime
    """

    picking_records = []
    pick_number = PICK_ID_START

    # --------------------------------------------------------
    # Group order items by order.
    # --------------------------------------------------------

    order_items_by_order = {}

    for item in order_items:
        order_items_by_order.setdefault(
            item["order_id"],
            [],
        ).append(item)

    # --------------------------------------------------------
    # Process orders.
    # --------------------------------------------------------

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
        except (
            KeyError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"Invalid requested_delivery_datetime for "
                f"{order_id}"
            ) from exc

        if requested_delivery_datetime <= order_datetime:
            raise ValueError(
                f"Delivery deadline is not after order creation "
                f"for {order_id}: "
                f"order={order_datetime.isoformat()}, "
                f"deadline={requested_delivery_datetime.isoformat()}"
            )

        order_records = []

        # ----------------------------------------------------
        # Generate picking records without timestamps first.
        # ----------------------------------------------------

        for item in items:

            product_id = item["product_id"]

            requested_quantity = int(
                item["requested_quantity"]
            )

            if requested_quantity <= 0:
                raise ValueError(
                    f"Invalid requested quantity for "
                    f"{item['order_item_id']}"
                )

            remaining_quantity = requested_quantity

            records = inventory_index.get(
                product_id,
                [],
            )

            if not records:
                raise ValueError(
                    f"No inventory location found "
                    f"for product {product_id}"
                )

            used_inventory_ids = set()

            while remaining_quantity > 0:

                available_records = [
                    record
                    for record in records
                    if (
                        record["location_id"]
                        in location_index
                    )
                    and int(
                        float(
                            record["quantity"]
                        )
                    ) > 0
                ]

                if not available_records:
                    raise ValueError(
                        f"No valid inventory location "
                        f"available for product "
                        f"{product_id}"
                    )

                sufficient = [
                    record
                    for record in available_records
                    if int(
                        float(
                            record["quantity"]
                        )
                    ) >= remaining_quantity
                ]

                if sufficient:

                    record = random.choice(
                        sufficient
                    )

                else:

                    unused_records = [
                        record
                        for record in available_records
                        if (
                            record["inventory_id"]
                            not in used_inventory_ids
                        )
                    ]

                    if unused_records:

                        record = max(
                            unused_records,
                            key=lambda row: int(
                                float(
                                    row["quantity"]
                                )
                            ),
                        )

                    else:

                        record = max(
                            available_records,
                            key=lambda row: int(
                                float(
                                    row["quantity"]
                                )
                            ),
                        )

                inventory_quantity = int(
                    float(
                        record["quantity"]
                    )
                )

                picked_quantity = min(
                    remaining_quantity,
                    inventory_quantity,
                )

                location = location_index[
                    record["location_id"]
                ]

                picking_method = location[
                    "picking_method"
                ]

                item_total_weight = float(
                    item.get(
                        "total_weight_kg",
                        0,
                    )
                )

                container_type = choose_container_type(
                    picking_method=picking_method,
                    quantity=picked_quantity,
                    order_weight_kg=item_total_weight,
                )

                pick_id = (
                    f"PICK-{pick_number:08d}"
                )

                pick_number += 1

                order_records.append(
                    {
                        "picking_id": pick_id,
                        "order_item_id": item[
                            "order_item_id"
                        ],
                        "order_id": order_id,
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
                            f"{container_type}-{pick_id}"
                        ),
                        "location_scan": True,
                        "container_scan": True,
                        "pick_status": "PICKED",
                        "pick_datetime": None,
                    }
                )

                remaining_quantity -= picked_quantity

                used_inventory_ids.add(
                    record["inventory_id"]
                )

        if not order_records:
            raise ValueError(
                f"No picking records generated for {order_id}"
            )

        # ----------------------------------------------------
        # Timeline.
        #
        # We create the whole order timeline only after all
        # picking records are known. This fixes the previous
        # situation where a long order could run past its
        # delivery deadline.
        # ----------------------------------------------------

        record_count = len(
            order_records
        )

        total_window_seconds = (
            requested_delivery_datetime
            - order_datetime
        ).total_seconds()

        if total_window_seconds <= 0:
            raise ValueError(
                f"Invalid operational window for "
                f"{order_id}"
            )

        # Keep one minute of safety before delivery when possible.
        buffer_seconds = min(
            60,
            max(
                1,
                int(
                    total_window_seconds * 0.05
                ),
            ),
        )

        latest_allowed_pick = (
            requested_delivery_datetime
            - timedelta(
                seconds=buffer_seconds
            )
        )

        usable_seconds = (
            latest_allowed_pick
            - order_datetime
        ).total_seconds()

        minimum_step_seconds = (
            PICKING_STEP_MINUTES[0] * 60
        )

        # ----------------------------------------------------
        # Timeline strategy
        #
        # The previous version required every pick transition
        # to be at least 5 minutes. That is not always possible
        # for an order with many picking records and a short
        # delivery window.
        #
        # For a synthetic historical dataset, the correct
        # solution is to compress the operational timeline:
        #
        #   normal order  ->  5-20 minute gaps
        #   tight order   ->  evenly distributed gaps
        #
        # We only require strictly chronological timestamps.
        # We never move picking before the order or after the
        # delivery deadline.
        # ----------------------------------------------------

        if record_count == 1:

            maximum_start_delay = max(
                0,
                int(usable_seconds),
            )

            start_delay_seconds = min(
                random.randint(
                    PICKING_START_DELAY_MINUTES[0] * 60,
                    PICKING_START_DELAY_MINUTES[1] * 60,
                ),
                maximum_start_delay,
            )

            first_pick_datetime = (
                order_datetime
                + timedelta(
                    seconds=start_delay_seconds
                )
            )

            timestamps = [
                first_pick_datetime
            ]

        else:

            # Use the normal start delay only when enough time
            # remains for normal 5-minute transitions.
            normal_start_delay = random.randint(
                PICKING_START_DELAY_MINUTES[0] * 60,
                PICKING_START_DELAY_MINUTES[1] * 60,
            )

            normal_required_seconds = (
                (record_count - 1)
                * minimum_step_seconds
            )

            if usable_seconds >= (
                normal_start_delay
                + normal_required_seconds
            ):

                # Normal operational timeline.
                start_delay_seconds = (
                    normal_start_delay
                )

                first_pick_datetime = (
                    order_datetime
                    + timedelta(
                        seconds=start_delay_seconds
                    )
                )

                available_for_steps = (
                    latest_allowed_pick
                    - first_pick_datetime
                ).total_seconds()

                timestamps = [
                    first_pick_datetime
                ]

                remaining_seconds = (
                    available_for_steps
                )

                for index in range(
                    1,
                    record_count,
                ):

                    picks_remaining_after_current = (
                        record_count
                        - index
                        - 1
                    )

                    minimum_future_seconds = (
                        picks_remaining_after_current
                        * minimum_step_seconds
                    )

                    maximum_step_seconds = (
                        remaining_seconds
                        - minimum_future_seconds
                    )

                    step_upper_bound = min(
                        maximum_step_seconds,
                        PICKING_STEP_MINUTES[1] * 60,
                    )

                    step_seconds = random.randint(
                        minimum_step_seconds,
                        max(
                            minimum_step_seconds,
                            int(step_upper_bound),
                        ),
                    )

                    timestamps.append(
                        timestamps[-1]
                        + timedelta(
                            seconds=step_seconds
                        )
                    )

                    remaining_seconds -= (
                        step_seconds
                    )

            else:

                # ------------------------------------------------
                # Tight deadline.
                #
                # Spread all picks evenly between order creation
                # and the latest safe picking timestamp.
                #
                # This is intentionally allowed to use intervals
                # shorter than 5 minutes. Otherwise some valid
                # orders could never be represented.
                # ------------------------------------------------

                first_pick_datetime = (
                    order_datetime
                    + timedelta(
                        seconds=min(
                            60,
                            max(
                                1,
                                int(
                                    usable_seconds * 0.05
                                ),
                            ),
                        )
                    )
                )

                available_for_steps = (
                    latest_allowed_pick
                    - first_pick_datetime
                ).total_seconds()

                if available_for_steps <= (
                    record_count - 1
                ):
                    raise ValueError(
                        f"Insufficient time even for a "
                        f"compressed picking timeline for "
                        f"{order_id}. "
                        f"Records={record_count}, "
                        f"available_seconds="
                        f"{available_for_steps:.0f}"
                    )

                # Leave at least one second between picks.
                step_seconds = (
                    available_for_steps
                    / (
                        record_count - 1
                    )
                )

                timestamps = [
                    first_pick_datetime
                    + timedelta(
                        seconds=(
                            index
                            * step_seconds
                        )
                    )
                    for index in range(
                        record_count
                    )
                ]

        # ----------------------------------------------------
        # Final timestamp validation.
        # ----------------------------------------------------

        previous_timestamp = None

        for index, record in enumerate(
            order_records
        ):

            pick_datetime = timestamps[
                index
            ]

            if (
                pick_datetime
                < order_datetime
            ):
                raise ValueError(
                    f"Pick occurs before order creation "
                    f"for {order_id}"
                )

            if (
                previous_timestamp is not None
                and pick_datetime
                <= previous_timestamp
            ):
                raise ValueError(
                    f"Picking timestamps are not strictly "
                    f"chronological for {order_id}"
                )

            if (
                pick_datetime
                >= requested_delivery_datetime
            ):
                raise ValueError(
                    f"Pick occurs at/after delivery deadline "
                    f"for {order_id}: "
                    f"pick={pick_datetime.isoformat()}, "
                    f"deadline="
                    f"{requested_delivery_datetime.isoformat()}"
                )

            record[
                "pick_datetime"
            ] = pick_datetime.isoformat(
                timespec="seconds"
            )

            previous_timestamp = (
                pick_datetime
            )

        picking_records.extend(
            order_records
        )

        # ----------------------------------------------------
        # Progress.
        # ----------------------------------------------------

        if (
            len(picking_records) // 5_000
            > (
                len(picking_records)
                - len(order_records)
            ) // 5_000
        ):
            print(
                f"  Generated "
                f"{len(picking_records):,} "
                f"picking records..."
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
    """
    Validate picking records.

    Every order item must be completely picked.
    """

    if not picking_records:

        raise ValueError(
            "No picking records generated."
        )

    order_item_lookup = {
        row[
            "order_item_id"
        ]: row
        for row in order_items
    }

    order_lookup = {
        row[
            "order_id"
        ]: row
        for row in orders
    }

    inventory_ids = {
        row[
            "inventory_id"
        ]
        for row in inventory
    }

    picking_ids = [
        row[
            "picking_id"
        ]
        for row in picking_records
    ]

    # --------------------------------------------------------
    # Unique picking IDs.
    # --------------------------------------------------------

    assert len(
        picking_ids
    ) == len(
        set(picking_ids)
    ), (
        "Duplicate picking_id values."
    )

    picked_by_item = {}

    last_pick_datetime_by_order = {}

    # --------------------------------------------------------
    # Validate every picking record.
    # --------------------------------------------------------

    for pick in picking_records:

        order_item_id = pick[
            "order_item_id"
        ]

        order_id = pick[
            "order_id"
        ]

        # ----------------------------------------------------
        # References.
        # ----------------------------------------------------

        assert (
            order_item_id
            in order_item_lookup
        ), (
            f"Unknown order_item_id: "
            f"{order_item_id}"
        )

        assert (
            pick[
                "inventory_id"
            ]
            in inventory_ids
        ), (
            f"Unknown inventory_id: "
            f"{pick['inventory_id']}"
        )

        assert (
            pick[
                "location_id"
            ]
            in location_index
        ), (
            f"Unknown location_id: "
            f"{pick['location_id']}"
        )

        # ----------------------------------------------------
        # Picking method.
        # ----------------------------------------------------

        assert (
            pick[
                "picking_method"
            ]
            in PICKING_METHODS
        ), (
            f"Invalid picking method: "
            f"{pick['picking_method']}"
        )

        # ----------------------------------------------------
        # Container.
        # ----------------------------------------------------

        assert (
            pick[
                "container_type"
            ]
            in CONTAINER_TYPES
        ), (
            f"Invalid container type: "
            f"{pick['container_type']}"
        )

        # ----------------------------------------------------
        # Quantity.
        # ----------------------------------------------------

        assert (
            int(
                pick[
                    "picked_quantity"
                ]
            ) > 0
        ), (
            f"Invalid picked quantity: "
            f"{pick['picking_id']}"
        )

        # ----------------------------------------------------
        # Scans.
        # ----------------------------------------------------

        assert (
            pick[
                "location_scan"
            ] is True
        ), (
            f"Location scan missing: "
            f"{pick['picking_id']}"
        )

        assert (
            pick[
                "container_scan"
            ] is True
        ), (
            f"Container scan missing: "
            f"{pick['picking_id']}"
        )

        # ----------------------------------------------------
        # Status.
        # ----------------------------------------------------

        assert (
            pick[
                "pick_status"
            ]
            in PICK_STATUSES
        ), (
            f"Invalid pick status: "
            f"{pick['picking_id']}"
        )

        # ----------------------------------------------------
        # Timestamp.
        # ----------------------------------------------------

        try:

            pick_datetime = (
                datetime.fromisoformat(
                    pick[
                        "pick_datetime"
                    ]
                )
            )

        except (
            KeyError,
            ValueError,
        ) as exc:

            raise ValueError(
                f"Invalid pick_datetime for "
                f"{pick['picking_id']}"
            ) from exc

        # ----------------------------------------------------
        # Order reference.
        # ----------------------------------------------------

        order = order_lookup.get(
            order_id
        )

        assert (
            order is not None
        ), (
            f"Unknown order_id: "
            f"{order_id}"
        )

        order_datetime = (
            datetime.fromisoformat(
                order[
                    "order_datetime"
                ]
            )
        )

        # Pick must occur after order creation.
        assert (
            pick_datetime
            >= order_datetime
        ), (
            f"Pick occurs before order: "
            f"{pick['picking_id']}"
        )

        # Pick must also occur before the requested delivery
        # deadline. Packing depends on this upstream guarantee.
        try:
            requested_delivery_datetime = datetime.fromisoformat(
                order["requested_delivery_datetime"]
            )
        except (
            KeyError,
            ValueError,
        ) as exc:
            raise ValueError(
                f"Invalid requested_delivery_datetime for "
                f"{order_id}"
            ) from exc

        assert (
            pick_datetime
            < requested_delivery_datetime
        ), (
            f"Pick occurs at/after delivery deadline: "
            f"{pick['picking_id']}"
        )

        # ----------------------------------------------------
        # Chronological order picks.
        # ----------------------------------------------------

        previous_pick = (
            last_pick_datetime_by_order.get(
                order_id
            )
        )

        if previous_pick is not None:

            assert (
                pick_datetime
                > previous_pick
            ), (
                "Picking timestamps are not "
                "strictly chronological for "
                f"order {order_id}"
            )

        last_pick_datetime_by_order[
            order_id
        ] = pick_datetime

        # ----------------------------------------------------
        # Aggregate picked quantity.
        # ----------------------------------------------------

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

    # ========================================================
    # COMPLETE PICK VALIDATION
    # ========================================================

    incomplete = 0

    for item in order_items:

        requested = int(
            item[
                "requested_quantity"
            ]
        )

        picked = picked_by_item.get(
            item[
                "order_item_id"
            ],
            0,
        )

        if picked != requested:

            incomplete += 1

    print()
    print(
        f"Order items not fully picked: "
        f"{incomplete:,}"
    )

    if incomplete > 0:

        raise ValueError(
            "Picking validation failed: "
            f"{incomplete:,} order items "
            "are not fully picked."
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
    """
    Print picking summary.
    """

    total_picks = len(
        picking_records
    )

    total_quantity = sum(
        int(
            row[
                "picked_quantity"
            ]
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

    # --------------------------------------------------------
    # Picking methods.
    # --------------------------------------------------------

    print()
    print("Picking Method")
    print("--------------")

    method_counts = {}

    for row in picking_records:

        method = row[
            "picking_method"
        ]

        method_counts[
            method
        ] = (
            method_counts.get(
                method,
                0,
            )
            + 1
        )

    for method in PICKING_METHODS:

        print(
            f"{method:<18}"
            f"{method_counts.get(method, 0):,}"
        )

    # --------------------------------------------------------
    # Container types.
    # --------------------------------------------------------

    print()
    print("Container Type")
    print("--------------")

    container_counts = {}

    for row in picking_records:

        container = row[
            "container_type"
        ]

        container_counts[
            container
        ] = (
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
    """
    Export picking records to CSV.
    """

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

    # --------------------------------------------------------
    # Orders
    # --------------------------------------------------------

    print()
    print("Loading orders...")

    orders = load_orders()

    print(
        f"Orders loaded: "
        f"{len(orders):,}"
    )

    # --------------------------------------------------------
    # Order items
    # --------------------------------------------------------

    print()
    print("Loading order items...")

    order_items = load_order_items()

    print(
        f"Order items loaded: "
        f"{len(order_items):,}"
    )

    # --------------------------------------------------------
    # Inventory
    # --------------------------------------------------------

    print()
    print("Loading inventory...")

    inventory = load_inventory()

    print(
        f"Inventory records loaded: "
        f"{len(inventory):,}"
    )

    # --------------------------------------------------------
    # Locations
    # --------------------------------------------------------

    print()
    print("Loading locations...")

    locations = load_locations()

    print(
        f"Locations loaded: "
        f"{len(locations):,}"
    )

    # --------------------------------------------------------
    # Indexes
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Picking
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print()
    print("Validating picking...")

    validate_picking(
        picking_records=picking_records,
        orders=orders,
        order_items=order_items,
        inventory=inventory,
        location_index=location_index,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(
        picking_records
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    export_picking(
        picking_records
    )

    print()
    print(
        "Picking generation completed successfully."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()