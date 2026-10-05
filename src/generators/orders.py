from pathlib import Path
import csv
import random
import hashlib
from datetime import datetime, timedelta


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRODUCT_FILE = PROCESSED_DIR / "product_master.csv"
INVENTORY_FILE = PROCESSED_DIR / "inventory.csv"

ORDERS_FILE = PROCESSED_DIR / "orders.csv"
ORDER_ITEMS_FILE = PROCESSED_DIR / "order_items.csv"


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

NUMBER_OF_ORDERS = 50_000

MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 8

MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 100

DAYS_OF_HISTORY = 365

ORDER_ID_START = 1

CUSTOMER_COUNT = 500


# ============================================================
# SEASONALITY
# ============================================================

MONTH_DEMAND_MULTIPLIERS = {
    1: 0.90,
    2: 0.95,
    3: 1.00,
    4: 1.00,
    5: 1.00,
    6: 0.95,
    7: 0.80,
    8: 0.80,
    9: 1.00,
    10: 1.05,
    11: 1.25,
    12: 1.40,
}


WEEKDAY_DEMAND_MULTIPLIERS = {
    0: 1.00,  # Monday
    1: 1.00,  # Tuesday
    2: 1.00,  # Wednesday
    3: 1.00,  # Thursday
    4: 0.95,  # Friday
    5: 0.35,  # Saturday
    6: 0.35,  # Sunday
}


# ============================================================
# ORDER WEIGHT DISTRIBUTION
# ============================================================

ORDER_WEIGHT_CLASSES = [
    "SMALL",
    "MEDIUM",
    "HEAVY",
    "VERY_HEAVY",
]


ORDER_WEIGHT_CLASS_WEIGHTS = {
    "SMALL": 0.60,
    "MEDIUM": 0.25,
    "HEAVY": 0.10,
    "VERY_HEAVY": 0.05,
}


ORDER_WEIGHT_RANGES = {
    "SMALL": (1.0, 100.0),
    "MEDIUM": (100.0, 500.0),
    "HEAVY": (500.0, 2000.0),
    "VERY_HEAVY": (2000.0, 4500.0),
}


VERY_HEAVY_SUBRANGES = [
    (2000.0, 2999.9),
    (3000.0, 3999.9),
    (4000.0, 4500.0),
]


# ============================================================
# ORDER STATUS
# ============================================================

ORDER_STATUSES = [
    "CREATED",
    "RELEASED",
    "IN_PICKING",
    "PARTIALLY_PICKED",
    "PICKED",
    "READY_FOR_PACKING",
    "PACKED",
    "SHIPPED",
]


ORDER_STATUS_WEIGHTS = {
    "CREATED": 0.08,
    "RELEASED": 0.07,
    "IN_PICKING": 0.10,
    "PARTIALLY_PICKED": 0.08,
    "PICKED": 0.12,
    "READY_FOR_PACKING": 0.10,
    "PACKED": 0.15,
    "SHIPPED": 0.20,
}


# ============================================================
# DELIVERY PRIORITY
# ============================================================

DELIVERY_PRIORITIES = [
    "LOW",
    "NORMAL",
    "HIGH",
    "URGENT",
]


DELIVERY_PRIORITY_WEIGHTS = {
    "LOW": 0.20,
    "NORMAL": 0.60,
    "HIGH": 0.15,
    "URGENT": 0.05,
}


# ============================================================
# RANDOM SEED
# ============================================================

random.seed(RANDOM_SEED)


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

        reader = csv.DictReader(file)

        return list(reader)


# ============================================================
# PRODUCT WEIGHT
# ============================================================

def generate_synthetic_unit_weight(product):
    """
    Generate a deterministic synthetic logistics weight.

    ABB source weights are not modified.
    Because the current ABB source does not provide usable
    unit weights, synthetic logistics weights are generated.

    The same article number always produces the same weight.
    """

    article_number = str(
        product.get(
            "article_number",
            "",
        )
    ).strip()

    digest = hashlib.sha256(
        article_number.encode("utf-8")
    ).hexdigest()

    seed_value = int(
        digest[:16],
        16,
    )

    normalized = (
        seed_value
        / float(
            16**16 - 1
        )
    )

    minimum = 0.05
    maximum = 25.0

    weight = (
        minimum
        * (
            maximum / minimum
        ) ** normalized
    )

    return round(
        weight,
        3,
    )


def parse_source_weight(raw_weight):
    """
    Try to parse a source weight.

    Returns:
        float or None
    """

    if raw_weight is None:
        return None

    value = str(
        raw_weight
    ).strip()

    if not value:
        return None

    try:

        if "," in value and "." in value:

            if value.rfind(",") > value.rfind("."):

                value = (
                    value
                    .replace(".", "")
                    .replace(",", ".")
                )

            else:

                value = (
                    value
                    .replace(",", "")
                )

        elif "," in value:

            value = value.replace(
                ",",
                ".",
            )

        parsed = float(
            value
        )

        if parsed > 0:
            return parsed

    except (
        ValueError,
        TypeError,
    ):
        pass

    return None


def load_products():
    """
    Load product master and prepare logistics weights.

    Source product data is preserved.
    Synthetic weights are only used when no valid
    source weight is available.
    """

    products = read_csv(
        PRODUCT_FILE
    )

    if not products:

        raise ValueError(
            "Product master is empty."
        )

    required_fields = {
        "product_id",
        "article_number",
        "unit_weight_kg",
    }

    missing_fields = (
        required_fields
        - set(products[0].keys())
    )

    if missing_fields:

        raise ValueError(
            "Product master is missing fields: "
            f"{missing_fields}"
        )

    valid_products = []

    source_weight_count = 0
    synthetic_weight_count = 0
    invalid_weight_count = 0

    for product in products:

        product_id = str(
            product.get(
                "product_id",
                "",
            )
        ).strip()

        article_number = str(
            product.get(
                "article_number",
                "",
            )
        ).strip()

        if not product_id:
            continue

        if not article_number:
            continue

        source_weight = parse_source_weight(
            product.get(
                "unit_weight_kg",
                "",
            )
        )

        if source_weight is not None:

            product["unit_weight_kg"] = (
                round(
                    source_weight,
                    3,
                )
            )

            product["weight_source"] = (
                "ABB_SOURCE"
            )

            source_weight_count += 1

        else:

            if (
                product.get(
                    "unit_weight_kg",
                    "",
                )
            ):

                invalid_weight_count += 1

            synthetic_weight = (
                generate_synthetic_unit_weight(
                    product
                )
            )

            product["unit_weight_kg"] = (
                synthetic_weight
            )

            product["weight_source"] = (
                "SYNTHETIC"
            )

            synthetic_weight_count += 1

        valid_products.append(
            product
        )

    print()
    print("Product Weight Validation")
    print("=========================")

    print(
        f"Total products:       "
        f"{len(products):,}"
    )

    print(
        f"ABB source weights:   "
        f"{source_weight_count:,}"
    )

    print(
        f"Synthetic weights:    "
        f"{synthetic_weight_count:,}"
    )

    print(
        f"Invalid source weights: "
        f"{invalid_weight_count:,}"
    )

    if not valid_products:

        raise ValueError(
            "No valid products available."
        )

    return valid_products


# ============================================================
# INVENTORY
# ============================================================

def load_inventory():
    """
    Load inventory snapshot.

    IMPORTANT:

    The inventory snapshot is NOT consumed during historical
    order generation.

    It is only used to identify products that exist in the
    warehouse.
    """

    inventory = read_csv(
        INVENTORY_FILE
    )

    if not inventory:

        raise ValueError(
            "Inventory is empty."
        )

    required_fields = {
        "inventory_id",
        "product_id",
        "quantity",
    }

    missing_fields = (
        required_fields
        - set(inventory[0].keys())
    )

    if missing_fields:

        raise ValueError(
            "Inventory is missing fields: "
            f"{missing_fields}"
        )

    return inventory


def build_inventory_index(
    inventory,
):
    """
    Build product availability index.

    Multiple inventory records for the same product
    are aggregated.

    Result:

        product_id -> total reference quantity
    """

    inventory_index = {}

    for record in inventory:

        product_id = str(
            record[
                "product_id"
            ]
        ).strip()

        try:

            quantity = int(
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

        inventory_index[
            product_id
        ] = (
            inventory_index.get(
                product_id,
                0,
            )
            + quantity
        )

    return inventory_index


# ============================================================
# AVAILABLE PRODUCT POOL
# ============================================================

def build_available_product_pool(
    products,
    inventory_index,
):
    """
    Build the available product pool ONCE.

    This is important for performance.

    We do NOT filter 16k products for every order.
    """

    available_products = []

    for product in products:

        product_id = product[
            "product_id"
        ]

        quantity = inventory_index.get(
            product_id,
            0,
        )

        if quantity <= 0:
            continue

        unit_weight = float(
            product[
                "unit_weight_kg"
            ]
        )

        if unit_weight <= 0:
            continue

        available_products.append(
            product
        )

    if not available_products:

        raise ValueError(
            "No products with positive inventory "
            "are available."
        )

    return available_products


# ============================================================
# CUSTOMER GENERATION
# ============================================================

def generate_customer_id(
    number,
):
    return (
        f"CUST-{number:05d}"
    )


def generate_customers(
    count=CUSTOMER_COUNT,
):
    """
    Generate synthetic customers.
    """

    customers = []

    for number in range(
        1,
        count + 1,
    ):

        customer_type = random.choices(
            [
                "B2B",
                "B2C",
            ],
            weights=[
                0.80,
                0.20,
            ],
            k=1,
        )[0]

        customers.append(
            {
                "customer_id": (
                    generate_customer_id(
                        number
                    )
                ),
                "customer_type": (
                    customer_type
                ),
                "status": "ACTIVE",
            }
        )

    return customers


# ============================================================
# DELIVERY PRIORITY
# ============================================================

def generate_delivery_priority():
    """
    Generate delivery priority.
    """

    priorities = list(
        DELIVERY_PRIORITY_WEIGHTS.keys()
    )

    weights = [
        DELIVERY_PRIORITY_WEIGHTS[
            priority
        ]
        for priority in priorities
    ]

    return random.choices(
        priorities,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# ORDER STATUS
# ============================================================

def generate_order_status():
    """
    Generate order status.
    """

    statuses = list(
        ORDER_STATUS_WEIGHTS.keys()
    )

    weights = [
        ORDER_STATUS_WEIGHTS[
            status
        ]
        for status in statuses
    ]

    return random.choices(
        statuses,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# ORDER DATETIME
# ============================================================

def generate_order_datetime():
    """
    Generate order datetime over the last 365 days.

    Demand is affected by:

    - month
    - summer slowdown
    - November / December peak
    - weekday
    - weekend reduction
    """

    now = datetime.now()

    start_date = (
        now
        - timedelta(
            days=DAYS_OF_HISTORY
        )
    )

    days = []

    current_date = (
        start_date.date()
    )

    end_date = now.date()

    while current_date <= end_date:

        month_multiplier = (
            MONTH_DEMAND_MULTIPLIERS.get(
                current_date.month,
                1.0,
            )
        )

        weekday_multiplier = (
            WEEKDAY_DEMAND_MULTIPLIERS.get(
                current_date.weekday(),
                1.0,
            )
        )

        demand_weight = (
            month_multiplier
            * weekday_multiplier
        )

        days.append(
            (
                current_date,
                demand_weight,
            )
        )

        current_date += timedelta(
            days=1
        )

    selected_date = random.choices(
        days,
        weights=[
            weight
            for _, weight in days
        ],
        k=1,
    )[0][0]

    random_seconds = random.randint(
        0,
        (24 * 60 * 60) - 1,
    )

    return (
        datetime.combine(
            selected_date,
            datetime.min.time(),
        )
        + timedelta(
            seconds=random_seconds
        )
    )


# ============================================================
# WEIGHT CLASS
# ============================================================

def generate_weight_class():
    """
    Generate target order weight class.
    """

    classes = list(
        ORDER_WEIGHT_CLASS_WEIGHTS.keys()
    )

    weights = [
        ORDER_WEIGHT_CLASS_WEIGHTS[
            weight_class
        ]
        for weight_class in classes
    ]

    return random.choices(
        classes,
        weights=weights,
        k=1,
    )[0]


def generate_weight_target(
    weight_class,
):
    """
    Generate target order weight range.
    """

    if weight_class == "VERY_HEAVY":

        return random.choice(
            VERY_HEAVY_SUBRANGES
        )

    return ORDER_WEIGHT_RANGES[
        weight_class
    ]


# ============================================================
# PRODUCT SELECTION
# ============================================================

def choose_product_for_order(
    available_products,
    target_min_weight,
):
    """
    Choose one product.

    For heavy orders, sample only a small subset of products
    and prefer products with higher unit weight.

    IMPORTANT:

    We never scan all 16,926 products for every order.
    """

    if (
        target_min_weight >= 2000
    ):

        sample_size = min(
            100,
            len(
                available_products
            ),
        )

        candidates = random.sample(
            available_products,
            sample_size,
        )

        heavy_candidates = [
            product
            for product in candidates
            if float(
                product[
                    "unit_weight_kg"
                ]
            ) >= 5.0
        ]

        if heavy_candidates:

            return random.choice(
                heavy_candidates
            )

    return random.choice(
        available_products
    )


# ============================================================
# ORDER HEADER
# ============================================================

def generate_order(
    order_number,
    customer,
    weight_class,
):
    """
    Generate order header.
    """

    order_id = (
        f"ORD-{order_number:08d}"
    )

    order_datetime = (
        generate_order_datetime()
    )

    requested_delivery_datetime = (
        order_datetime
        + timedelta(
            hours=random.randint(
                48,
                120,
            )
        )
    )

    return {
        "order_id": order_id,
        "customer_id": (
            customer[
                "customer_id"
            ]
        ),
        "order_datetime": (
            order_datetime.isoformat(
                timespec="seconds"
            )
        ),
        "order_status": (
            generate_order_status()
        ),
        "delivery_priority": (
            generate_delivery_priority()
        ),
        "order_weight_class": (
            weight_class
        ),
        "requested_delivery_datetime": (
            requested_delivery_datetime.isoformat(
                timespec="seconds"
            )
        ),
        "total_items": 0,
        "total_weight_kg": 0.0,
    }


# ============================================================
# ORDER ITEM GENERATION
# ============================================================

def create_order_item(
    order,
    product,
    line_number,
    quantity,
):
    """
    Create one order item.
    """

    unit_weight = float(
        product[
            "unit_weight_kg"
        ]
    )

    total_weight = (
        quantity
        * unit_weight
    )

    return {
        "order_item_id": (
            f"{order['order_id']}"
            f"-ITEM-{line_number:02d}"
        ),
        "order_id": (
            order[
                "order_id"
            ]
        ),
        "line_number": (
            line_number
        ),
        "product_id": (
            product[
                "product_id"
            ]
        ),
        "requested_quantity": (
            quantity
        ),
        "unit_weight_kg": round(
            unit_weight,
            3,
        ),
        "weight_source": (
            product.get(
                "weight_source",
                "SYNTHETIC",
            )
        ),
        "total_weight_kg": round(
            total_weight,
            3,
        ),
        "picked_quantity": 0,
        "packed_quantity": 0,
        "shipped_quantity": 0,
        "item_status": "NOT_STARTED",
    }


def generate_order_items(
    order,
    available_products,
    inventory_index,
    product_index,
    target_min_weight,
    target_max_weight,
):
    """
    Generate order items efficiently.

    No 100-attempt loop.

    Each order gets between 1 and MAX_ITEMS_PER_ORDER
    unique products.

    Quantity is calculated directly from the remaining
    target weight.
    """

    items = []

    used_products = set()

    total_weight = 0.0

    # --------------------------------------------------------
    # Determine number of lines first.
    # --------------------------------------------------------

    if target_min_weight < 100:

        target_lines = random.randint(
            1,
            min(
                3,
                MAX_ITEMS_PER_ORDER,
            ),
        )

    elif target_min_weight < 500:

        target_lines = random.randint(
            1,
            min(
                5,
                MAX_ITEMS_PER_ORDER,
            ),
        )

    elif target_min_weight < 2000:

        target_lines = random.randint(
            2,
            min(
                6,
                MAX_ITEMS_PER_ORDER,
            ),
        )

    else:

        target_lines = random.randint(
            3,
            MAX_ITEMS_PER_ORDER,
        )

    # --------------------------------------------------------
    # Generate each line.
    # --------------------------------------------------------

    for line_number in range(
        1,
        target_lines + 1,
    ):

        remaining_weight = (
            target_max_weight
            - total_weight
        )

        if remaining_weight <= 0:
            break

        # ----------------------------------------------------
        # Select product.
        # ----------------------------------------------------

        product = None

        for _ in range(10):

            candidate = (
                choose_product_for_order(
                    available_products,
                    target_min_weight,
                )
            )

            candidate_id = candidate[
                "product_id"
            ]

            if candidate_id not in used_products:

                product = candidate
                break

        if product is None:
            break

        product_id = product[
            "product_id"
        ]

        unit_weight = float(
            product[
                "unit_weight_kg"
            ]
        )

        if unit_weight <= 0:
            continue

        # ----------------------------------------------------
        # Remaining lines after this one.
        # ----------------------------------------------------

        remaining_lines = (
            target_lines
            - line_number
        )

        # ----------------------------------------------------
        # For the final line, try to reach minimum target.
        # ----------------------------------------------------

        if (
            remaining_lines == 0
            and total_weight
            < target_min_weight
        ):

            required_weight = (
                target_min_weight
                - total_weight
            )

            quantity = max(
                1,
                int(
                    required_weight
                    / unit_weight
                ),
            )

        else:

            # Normal quantity generation.
            quantity = random.randint(
                MIN_QUANTITY_PER_ITEM,
                MAX_QUANTITY_PER_ITEM,
            )

        # ----------------------------------------------------
        # Heavy orders may require larger quantities.
        # ----------------------------------------------------

        if target_min_weight >= 2000:

            quantity = max(
                quantity,
                int(
                    (
                        target_min_weight
                        / max(
                            target_lines,
                            1,
                        )
                    )
                    / unit_weight
                ),
            )

        # ----------------------------------------------------
        # Never exceed maximum order weight.
        # ----------------------------------------------------

        max_quantity_by_weight = int(
            remaining_weight
            / unit_weight
        )

        if max_quantity_by_weight <= 0:
            continue

        quantity = min(
            quantity,
            max_quantity_by_weight,
        )

        # ----------------------------------------------------
        # Enforce quantity minimum.
        # ----------------------------------------------------

        if quantity < 1:
            continue

        item = create_order_item(
            order=order,
            product=product,
            line_number=line_number,
            quantity=quantity,
        )

        items.append(
            item
        )

        used_products.add(
            product_id
        )

        total_weight += float(
            item[
                "total_weight_kg"
            ]
        )

    # --------------------------------------------------------
    # Final correction:
    #
    # If the order is below the target minimum, add one
    # additional item if possible.
    # --------------------------------------------------------

    if (
        total_weight < target_min_weight
        and len(items)
        < MAX_ITEMS_PER_ORDER
    ):

        required_weight = (
            target_min_weight
            - total_weight
        )

        # Sample only a small number of products.
        sample_size = min(
            100,
            len(
                available_products
            ),
        )

        candidates = random.sample(
            available_products,
            sample_size,
        )

        candidates = [
            product
            for product in candidates
            if (
                product[
                    "product_id"
                ]
                not in used_products
            )
            and float(
                product[
                    "unit_weight_kg"
                ]
            ) > 0
        ]

        if candidates:

            # Pick a product whose unit weight is
            # reasonably close to the remaining target.
            product = min(
                candidates,
                key=lambda candidate: abs(
                    float(
                        candidate[
                            "unit_weight_kg"
                        ]
                    )
                    - required_weight
                ),
            )

            unit_weight = float(
                product[
                    "unit_weight_kg"
                ]
            )

            quantity = max(
                1,
                int(
                    required_weight
                    / unit_weight
                ),
            )

            quantity = min(
                quantity,
                MAX_QUANTITY_PER_ITEM,
            )

            item_weight = (
                quantity
                * unit_weight
            )

            if (
                total_weight
                + item_weight
                <= target_max_weight
            ):

                line_number = (
                    len(items) + 1
                )

                item = create_order_item(
                    order=order,
                    product=product,
                    line_number=line_number,
                    quantity=quantity,
                )

                items.append(
                    item
                )

    return items


# ============================================================
# GENERATE ORDERS
# ============================================================

def generate_orders(
    number_of_orders,
    customers,
    products,
    inventory_index,
):
    """
    Generate historical warehouse orders.

    Inventory is NOT consumed.

    The inventory snapshot only determines which products
    are available for the synthetic simulation.
    """

    # --------------------------------------------------------
    # IMPORTANT PERFORMANCE OPTIMIZATION:
    #
    # This is built ONCE.
    # --------------------------------------------------------

    available_products = (
        build_available_product_pool(
            products,
            inventory_index,
        )
    )

    product_index = {
        product[
            "product_id"
        ]: product
        for product in products
    }

    orders = []
    order_items = []

    for order_number in range(
        ORDER_ID_START,
        ORDER_ID_START
        + number_of_orders,
    ):

        weight_class = (
            generate_weight_class()
        )

        target_min_weight, target_max_weight = (
            generate_weight_target(
                weight_class
            )
        )

        customer = random.choice(
            customers
        )

        order = generate_order(
            order_number=order_number,
            customer=customer,
            weight_class=weight_class,
        )

        items = generate_order_items(
            order=order,
            available_products=(
                available_products
            ),
            inventory_index=(
                inventory_index
            ),
            product_index=(
                product_index
            ),
            target_min_weight=(
                target_min_weight
            ),
            target_max_weight=(
                target_max_weight
            ),
        )

        if not items:
            continue

        total_items = sum(
            int(
                item[
                    "requested_quantity"
                ]
            )
            for item in items
        )

        total_weight = sum(
            float(
                item[
                    "total_weight_kg"
                ]
            )
            for item in items
        )

        order[
            "total_items"
        ] = total_items

        order[
            "total_weight_kg"
        ] = round(
            total_weight,
            3,
        )

        orders.append(
            order
        )

        order_items.extend(
            items
        )

        # ----------------------------------------------------
        # Progress output.
        # ----------------------------------------------------

        if (
            order_number % 5_000
            == 0
        ):

            print(
                f"  Generated "
                f"{order_number:,} / "
                f"{number_of_orders:,} orders..."
            )

    return (
        orders,
        order_items,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_orders(
    orders,
    order_items,
    customers,
    inventory_index,
):
    """
    Validate generated orders and order items.
    """

    assert orders, (
        "No orders were generated."
    )

    assert order_items, (
        "No order items were generated."
    )

    customer_ids = {
        customer[
            "customer_id"
        ]
        for customer in customers
    }

    order_ids = [
        order[
            "order_id"
        ]
        for order in orders
    ]

    assert len(
        order_ids
    ) == len(
        set(order_ids)
    ), (
        "Duplicate order IDs detected."
    )

    order_item_ids = [
        item[
            "order_item_id"
        ]
        for item in order_items
    ]

    assert len(
        order_item_ids
    ) == len(
        set(order_item_ids)
    ), (
        "Duplicate order item IDs detected."
    )

    order_lookup = {
        order[
            "order_id"
        ]: order
        for order in orders
    }

    # --------------------------------------------------------
    # Validate orders.
    # --------------------------------------------------------

    for order in orders:

        order_id = order[
            "order_id"
        ]

        assert (
            order[
                "customer_id"
            ]
            in customer_ids
        ), (
            f"Unknown customer: "
            f"{order['customer_id']}"
        )

        assert (
            order[
                "order_status"
            ]
            in ORDER_STATUSES
        ), (
            f"Invalid order status "
            f"for {order_id}"
        )

        assert (
            order[
                "delivery_priority"
            ]
            in DELIVERY_PRIORITIES
        ), (
            f"Invalid delivery priority "
            f"for {order_id}"
        )

        assert (
            order[
                "order_weight_class"
            ]
            in ORDER_WEIGHT_CLASSES
        ), (
            f"Invalid weight class "
            f"for {order_id}"
        )

        assert (
            float(
                order[
                    "total_weight_kg"
                ]
            )
            > 0
        ), (
            f"Invalid order weight "
            f"for {order_id}"
        )

        assert (
            int(
                order[
                    "total_items"
                ]
            )
            > 0
        ), (
            f"Invalid total items "
            f"for {order_id}"
        )

        order_datetime = (
            datetime.fromisoformat(
                order[
                    "order_datetime"
                ]
            )
        )

        delivery_datetime = (
            datetime.fromisoformat(
                order[
                    "requested_delivery_datetime"
                ]
            )
        )

        assert (
            delivery_datetime
            > order_datetime
        ), (
            f"Requested delivery datetime "
            f"is invalid for {order_id}"
        )

    # --------------------------------------------------------
    # Validate items.
    # --------------------------------------------------------

    order_product_pairs = set()

    for item in order_items:

        order_id = item[
            "order_id"
        ]

        product_id = item[
            "product_id"
        ]

        assert (
            order_id in order_lookup
        ), (
            f"Unknown order "
            f"{order_id}"
        )

        assert (
            product_id
            in inventory_index
        ), (
            f"Product {product_id} "
            f"not present in inventory."
        )

        pair = (
            order_id,
            product_id,
        )

        assert (
            pair
            not in order_product_pairs
        ), (
            f"Duplicate product "
            f"{product_id} in order "
            f"{order_id}"
        )

        order_product_pairs.add(
            pair
        )

        quantity = int(
            item[
                "requested_quantity"
            ]
        )

        assert (
            quantity > 0
        ), (
            f"Invalid quantity "
            f"for {item['order_item_id']}"
        )

        unit_weight = float(
            item[
                "unit_weight_kg"
            ]
        )

        total_weight = float(
            item[
                "total_weight_kg"
            ]
        )

        calculated_weight = (
            quantity
            * unit_weight
        )

        assert abs(
            calculated_weight
            - total_weight
        ) < 0.01, (
            f"Weight mismatch "
            f"for {item['order_item_id']}"
        )

        assert (
            item[
                "picked_quantity"
            ]
            == 0
        )

        assert (
            item[
                "packed_quantity"
            ]
            == 0
        )

        assert (
            item[
                "shipped_quantity"
            ]
            == 0
        )

        assert (
            item[
                "item_status"
            ]
            == "NOT_STARTED"
        )

    # --------------------------------------------------------
    # Validate totals.
    # --------------------------------------------------------

    calculated_quantity = {}
    calculated_weight = {}

    for item in order_items:

        order_id = item[
            "order_id"
        ]

        calculated_quantity[
            order_id
        ] = (
            calculated_quantity.get(
                order_id,
                0,
            )
            + int(
                item[
                    "requested_quantity"
                ]
            )
        )

        calculated_weight[
            order_id
        ] = (
            calculated_weight.get(
                order_id,
                0.0,
            )
            + float(
                item[
                    "total_weight_kg"
                ]
            )
        )

    for order in orders:

        order_id = order[
            "order_id"
        ]

        expected_quantity = (
            calculated_quantity[
                order_id
            ]
        )

        expected_weight = (
            calculated_weight[
                order_id
            ]
        )

        assert (
            int(
                order[
                    "total_items"
                ]
            )
            == expected_quantity
        ), (
            f"Quantity total mismatch "
            f"for {order_id}"
        )

        assert abs(
            float(
                order[
                    "total_weight_kg"
                ]
            )
            - expected_weight
        ) < 0.01, (
            f"Weight total mismatch "
            f"for {order_id}"
        )

    print(
        "Order validation passed."
    )


# ============================================================
# SUMMARY
# ============================================================

def print_order_summary(
    orders,
    order_items,
):
    """
    Print order generation summary.
    """

    total_orders = len(
        orders
    )

    total_order_items = len(
        order_items
    )

    total_requested_quantity = sum(
        int(
            item[
                "requested_quantity"
            ]
        )
        for item in order_items
    )

    total_weight = sum(
        float(
            order[
                "total_weight_kg"
            ]
        )
        for order in orders
    )

    average_weight = (
        total_weight
        / total_orders
        if total_orders
        else 0
    )

    average_items = (
        total_order_items
        / total_orders
        if total_orders
        else 0
    )

    min_weight = min(
        float(
            order[
                "total_weight_kg"
            ]
        )
        for order in orders
    )

    max_weight = max(
        float(
            order[
                "total_weight_kg"
            ]
        )
        for order in orders
    )

    print()
    print("Warehouse Order Summary")
    print("=======================")

    print(
        f"Orders generated:       "
        f"{total_orders:,}"
    )

    print(
        f"Order items generated:  "
        f"{total_order_items:,}"
    )

    print(
        f"Requested quantity:     "
        f"{total_requested_quantity:,}"
    )

    print(
        f"Total order weight:     "
        f"{total_weight:,.1f} kg"
    )

    print(
        f"Average order weight:   "
        f"{average_weight:,.1f} kg"
    )

    print(
        f"Minimum order weight:   "
        f"{min_weight:,.1f} kg"
    )

    print(
        f"Maximum order weight:   "
        f"{max_weight:,.1f} kg"
    )

    print(
        f"Avg items per order:    "
        f"{average_items:.2f}"
    )


def print_weight_summary(
    orders,
):
    """
    Print order weight distribution.
    """

    under_100 = 0
    between_100_500 = 0
    between_500_2000 = 0
    above_2000 = 0

    two_to_three = 0
    three_to_four = 0
    four_plus = 0

    for order in orders:

        weight = float(
            order[
                "total_weight_kg"
            ]
        )

        if weight < 100:

            under_100 += 1

        elif weight < 500:

            between_100_500 += 1

        elif weight < 2000:

            between_500_2000 += 1

        else:

            above_2000 += 1

            if weight < 3000:

                two_to_three += 1

            elif weight < 4000:

                three_to_four += 1

            else:

                four_plus += 1

    total = len(
        orders
    )

    print()
    print("Order Weight Distribution")
    print("==========================")

    print(
        f"Under 100 kg:       "
        f"{under_100:,} "
        f"({under_100 / total * 100:.1f}%)"
    )

    print(
        f"100 - 500 kg:       "
        f"{between_100_500:,} "
        f"({between_100_500 / total * 100:.1f}%)"
    )

    print(
        f"500 - 2,000 kg:     "
        f"{between_500_2000:,} "
        f"({between_500_2000 / total * 100:.1f}%)"
    )

    print(
        f"2,000+ kg:          "
        f"{above_2000:,} "
        f"({above_2000 / total * 100:.1f}%)"
    )

    print()
    print("Heavy Order Detail")
    print("==================")

    print(
        f"2,000 - 2,999 kg:   "
        f"{two_to_three:,}"
    )

    print(
        f"3,000 - 3,999 kg:   "
        f"{three_to_four:,}"
    )

    print(
        f"4,000+ kg:          "
        f"{four_plus:,}"
    )


# ============================================================
# EXPORT ORDERS
# ============================================================

def export_orders(
    orders,
    output_file=ORDERS_FILE,
):
    """
    Export order headers.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "order_id",
        "customer_id",
        "order_datetime",
        "order_status",
        "delivery_priority",
        "order_weight_class",
        "requested_delivery_datetime",
        "total_items",
        "total_weight_kg",
    ]

    with output_file.open(
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
            orders
        )

    print()
    print(
        "Orders export complete:"
    )

    print(
        output_file
    )


# ============================================================
# EXPORT ORDER ITEMS
# ============================================================

def export_order_items(
    order_items,
    output_file=ORDER_ITEMS_FILE,
):
    """
    Export order items.
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "order_item_id",
        "order_id",
        "line_number",
        "product_id",
        "requested_quantity",
        "unit_weight_kg",
        "weight_source",
        "total_weight_kg",
        "picked_quantity",
        "packed_quantity",
        "shipped_quantity",
        "item_status",
    ]

    with output_file.open(
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
            order_items
        )

    print()
    print(
        "Order items export complete:"
    )

    print(
        output_file
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("Warehouse Order Generator")
    print("==========================")

    print()
    print("Loading products...")

    products = load_products()

    print(
        f"Products loaded: "
        f"{len(products):,}"
    )

    print()
    print("Loading inventory...")

    inventory = load_inventory()

    print(
        f"Inventory records loaded: "
        f"{len(inventory):,}"
    )

    print()
    print("Building inventory index...")

    inventory_index = (
        build_inventory_index(
            inventory
        )
    )

    print(
        f"Products with inventory: "
        f"{len(inventory_index):,}"
    )

    print()
    print("Generating customers...")

    customers = generate_customers()

    print(
        f"Customers generated: "
        f"{len(customers):,}"
    )

    print()
    print("Generating orders...")

    orders, order_items = (
        generate_orders(
            number_of_orders=(
                NUMBER_OF_ORDERS
            ),
            customers=customers,
            products=products,
            inventory_index=(
                inventory_index
            ),
        )
    )

    print()
    print("Validating orders...")

    validate_orders(
        orders=orders,
        order_items=order_items,
        customers=customers,
        inventory_index=(
            inventory_index
        ),
    )

    print_order_summary(
        orders,
        order_items,
    )

    print_weight_summary(
        orders
    )

    export_orders(
        orders
    )

    export_order_items(
        order_items
    )

    print()
    print("Order generation completed successfully.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
    