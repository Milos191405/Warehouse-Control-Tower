from pathlib import Path
import csv
import random
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

NUMBER_OF_ORDERS = 25_000

MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 8

MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 100

DAYS_OF_HISTORY = 180

ORDER_ID_START = 1

CUSTOMER_COUNT = 500


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


# Target weight ranges in kg.
#
# The generator does NOT simply assign this weight.
# It selects real products and quantities until the
# calculated order weight reaches the target range.

ORDER_WEIGHT_RANGES = {
    "SMALL": (1.0, 100.0),
    "MEDIUM": (100.0, 500.0),
    "HEAVY": (500.0, 2000.0),
    "VERY_HEAVY": (2000.0, 4500.0),
}

# Heavy-order sub-ranges. These are used to make sure the
# synthetic dataset contains visible 2t, 3t and 4t+ orders.
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


def generate_delivery_priority():
    """Generate a synthetic delivery priority."""

    return random.choices(
        DELIVERY_PRIORITIES,
        weights=[
            DELIVERY_PRIORITY_WEIGHTS[priority]
            for priority in DELIVERY_PRIORITIES
        ],
        k=1,
    )[0]


# ============================================================
# RANDOM GENERATOR
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
# LOAD PRODUCTS
# ============================================================


def generate_synthetic_unit_weight(product):
    """
    Generate a deterministic synthetic logistics weight for a product.

    ABB product master values are kept untouched. If the source product
    does not contain a unit weight, the warehouse simulation assigns a
    synthetic weight so that order and shipping analytics can still be
    generated.

    The value is deterministic for the same article number, so rerunning
    the generator with the same product master produces the same weight.
    """

    import hashlib
    import math

    article_number = str(
        product.get("article_number", "")
    ).strip()

    digest = hashlib.sha256(
        article_number.encode("utf-8")
    ).hexdigest()

    seed_value = int(digest[:16], 16)
    normalized = seed_value / float(16**16 - 1)

    # Log-style distribution from approximately 0.05 kg to 25 kg.
    # This creates many small products and a smaller number of heavier
    # products, which is more useful for warehouse simulation than a
    # uniform distribution.
    minimum = 0.05
    maximum = 25.0

    weight = minimum * (
        maximum / minimum
    ) ** normalized

    return round(weight, 3)


def load_products():
    """
    Load product master and prepare logistics weights.

    The ABB product master remains unchanged. When unit_weight_kg is
    missing in the source data, a deterministic synthetic logistics
    weight is generated for the warehouse simulation.
    """

    products = read_csv(PRODUCT_FILE)

    if not products:
        raise ValueError(
            "Product master is empty."
        )

    required_fields = {
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
    real_weight_count = 0
    synthetic_weight_count = 0
    invalid_weight_count = 0

    for product in products:

        product_id = str(
            product.get("article_number", "")
        ).strip()

        if not product_id:
            continue

        raw_weight = product.get(
            "unit_weight_kg",
            "",
        )

        weight = None

        if raw_weight is not None:
            raw_weight = str(
                raw_weight
            ).strip()

        if raw_weight:
            normalized = raw_weight

            if (
                "," in normalized
                and "." in normalized
            ):
                if normalized.rfind(",") > normalized.rfind("."):
                    normalized = (
                        normalized
                        .replace(".", "")
                        .replace(",", ".")
                    )
                else:
                    normalized = normalized.replace(
                        ",", ""
                    )

            elif "," in normalized:
                normalized = normalized.replace(
                    ",", "."
                )

            try:
                parsed_weight = float(
                    normalized
                )

                if parsed_weight > 0:
                    weight = parsed_weight
                    real_weight_count += 1

            except (
                ValueError,
                TypeError,
            ):
                invalid_weight_count += 1

        # ABB source has no unit weights in the current product master.
        # Use a clearly synthetic logistics weight instead of inventing
        # a value inside the ABB source file.
        if weight is None:
            weight = generate_synthetic_unit_weight(
                product
            )
            synthetic_weight_count += 1

        product["unit_weight_kg"] = weight
        product["weight_source"] = (
            "ABB_SOURCE"
            if raw_weight
            and weight == float(raw_weight.replace(",", "."))
            else "SYNTHETIC"
        )

        valid_products.append(product)

    print()
    print("Product Weight Validation")
    print("=========================")

    print(
        f"Total products:       "
        f"{len(products):,}"
    )

    print(
        f"ABB source weights:    "
        f"{real_weight_count:,}"
    )

    print(
        f"Synthetic weights:     "
        f"{synthetic_weight_count:,}"
    )

    print(
        f"Invalid source weights: "
        f"{invalid_weight_count:,}"
    )

    if not valid_products:
        raise ValueError(
            "No products available for order generation."
        )

    return valid_products

# ============================================================
# LOAD INVENTORY
# ============================================================


def load_inventory():
    """
    Load warehouse inventory.
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


# ============================================================
# INVENTORY INDEX
# ============================================================


def build_inventory_index(
    inventory,
):
    """
    Build:

        product_id -> available quantity

    Quantities from multiple locations are aggregated.
    """

    inventory_index = {}

    for record in inventory:

        product_id = record[
            "product_id"
        ]

        quantity = int(
            float(
                record["quantity"]
            )
        )

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
# PRODUCT INDEX
# ============================================================


def build_product_index(
    products,
):
    """
    Build:

        product_id -> product
    """

    return {
        product["product_id"]: product
        for product in products
    }


# ============================================================
# CUSTOMER GENERATION
# ============================================================


def generate_customer_id(
    number,
):
    return f"CUST-{number:05d}"


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

        customers.append(
            {
                "customer_id": (
                    generate_customer_id(
                        number
                    )
                ),
                "customer_type": random.choice(
                    [
                        "B2B",
                        "B2B",
                        "B2B",
                        "B2C",
                    ]
                ),
                "status": "ACTIVE",
            }
        )

    return customers


# ============================================================
# DATE GENERATION
# ============================================================


def generate_order_datetime():
    """
    Generate random order timestamp
    within the configured history.
    """

    now = datetime.now()

    start_date = (
        now
        - timedelta(
            days=DAYS_OF_HISTORY
        )
    )

    total_seconds = int(
        (
            now
            - start_date
        ).total_seconds()
    )

    random_seconds = random.randint(
        0,
        total_seconds,
    )

    return (
        start_date
        + timedelta(
            seconds=random_seconds
        )
    )


# ============================================================
# ORDER STATUS
# ============================================================


def generate_order_status():
    """
    Generate order status.
    """

    weights = [
        ORDER_STATUS_WEIGHTS[status]
        for status in ORDER_STATUSES
    ]

    return random.choices(
        ORDER_STATUSES,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# WEIGHT CLASS
# ============================================================


def generate_weight_class():
    """
    Select target order weight class.
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


def generate_weight_target(weight_class):
    """
    Generate a target weight range.

    VERY_HEAVY orders are explicitly split across
    2t, 3t and 4t+ ranges.
    """

    if weight_class == "VERY_HEAVY":
        return random.choice(
            VERY_HEAVY_SUBRANGES
        )

    return ORDER_WEIGHT_RANGES[
        weight_class
    ]


# ============================================================
# PRODUCT POOL
# ============================================================


def build_available_product_pool(
    products,
    inventory_index,
):
    """
    Return products that:

        1. exist in inventory
        2. have positive inventory
        3. have valid unit weight
    """

    available = []

    for product in products:

        product_id = product["product_id"]

        if product_id not in inventory_index:
            continue

        if (
            inventory_index[product_id]
            <= 0
        ):
            continue

        weight = float(
            product["unit_weight_kg"]
        )

        if weight <= 0:
            continue

        available.append(
            product
        )

    if not available:
        raise ValueError(
            "No products available "
            "for order generation."
        )

    return available


# ============================================================
# ORDER HEADER
# ============================================================


def generate_order(
    order_number,
    customer,
    weight_class,
):
    """
    Generate one order header.
    """

    order_id = (
        f"ORD-{order_number:08d}"
    )

    order_datetime = (
        generate_order_datetime()
    )

    return {
        "order_id": order_id,
        "customer_id": customer[
            "customer_id"
        ],
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
            (
                order_datetime
                + timedelta(
                    hours=random.randint(48, 120)
                )
            ).isoformat(timespec="seconds")
        ),
        "total_items": 0,
        "total_weight_kg": 0.0,
    }


# ============================================================
# ORDER ITEM GENERATION
# ============================================================


def choose_product_for_order(
    available_products,
    target_min_weight,
):
    """
    Choose a product.

    For very heavy orders, favor heavier products so the
    generator can reliably reach 2t, 3t and 4t+ ranges.
    """

    if target_min_weight >= 2000:
        candidates = [
            product
            for product in available_products
            if float(product["unit_weight_kg"]) >= 5.0
        ]

        if candidates:
            return random.choice(candidates)

    return random.choice(
        available_products
    )


def calculate_item_weight(
    quantity,
    unit_weight_kg,
):
    """
    Calculate total weight of an order item.
    """

    return (
        quantity
        * unit_weight_kg
    )


def generate_order_items(
    order,
    available_products,
    inventory_index,
    product_index,
    target_min_weight,
    target_max_weight,
):
    """
    Generate order items until the calculated
    order weight reaches the target range.

    Weight is always calculated from:

        quantity * product unit weight

    The unit weight is taken from the ABB source when available;
    otherwise it is a clearly marked synthetic logistics weight.
    """

    items = []

    used_products = set()

    total_weight = 0.0

    max_attempts = 100

    attempts = 0

    while attempts < max_attempts:

        attempts += 1

        # ----------------------------------------------------
        # Stop if target weight has been reached.
        # ----------------------------------------------------

        if total_weight >= target_min_weight:

            # For small and medium orders we usually stop
            # once the target range is reached.
            #
            # For very heavy orders we allow the same logic
            # but still cap the order at the configured range.

            if total_weight <= target_max_weight:
                break

        # ----------------------------------------------------
        # Maximum number of lines.
        # ----------------------------------------------------

        if len(items) >= MAX_ITEMS_PER_ORDER:
            break

        # ----------------------------------------------------
        # Select product.
        # ----------------------------------------------------

        # Refresh the product pool because previous orders
        # reserve inventory as generation progresses.
        current_products = [
            p
            for p in available_products
            if inventory_index.get(
                p["product_id"],
                0,
            ) > 0
        ]

        if not current_products:
            break

        product = choose_product_for_order(
            current_products,
            target_min_weight,
        )

        product_id = (
            product["product_id"]
        )

        if product_id in used_products:
            continue

        available_quantity = int(
            inventory_index[
                product_id
            ]
        )

        if available_quantity <= 0:
            continue

        unit_weight = float(
            product["unit_weight_kg"]
        )

        if unit_weight <= 0:
            continue

        # ----------------------------------------------------
        # Remaining target weight.
        # ----------------------------------------------------

        remaining_weight = (
            target_max_weight
            - total_weight
        )

        if remaining_weight <= 0:
            break

        # ----------------------------------------------------
        # Maximum quantity that fits into
        # remaining target weight.
        # ----------------------------------------------------

        quantity_by_weight = int(
            remaining_weight
            / unit_weight
        )

        if quantity_by_weight < 1:
            continue

        quantity_cap = (
            1000
            if target_min_weight >= 2000
            else MAX_QUANTITY_PER_ITEM
        )

        max_quantity = min(
            quantity_cap,
            available_quantity,
            quantity_by_weight,
        )

        if max_quantity < MIN_QUANTITY_PER_ITEM:
            continue

        quantity = random.randint(
            MIN_QUANTITY_PER_ITEM,
            max_quantity,
        )

        item_weight = (
            calculate_item_weight(
                quantity,
                unit_weight,
            )
        )

        # ----------------------------------------------------
        # Safety check.
        # ----------------------------------------------------

        if (
            total_weight
            + item_weight
            > target_max_weight
        ):
            continue

        line_number = (
            len(items) + 1
        )

        item = {
            "order_item_id": (
                f"{order['order_id']}"
                f"-ITEM-{line_number:02d}"
            ),
            "order_id": order[
                "order_id"
            ],
            "line_number": line_number,
            "product_id": product_id,
            "requested_quantity": quantity,
            "unit_weight_kg": round(
                unit_weight,
                3,
            ),
            "weight_source": product.get(
                "weight_source",
                "SYNTHETIC",
            ),
            "total_weight_kg": round(
                item_weight,
                3,
            ),
            "picked_quantity": 0,
            "packed_quantity": 0,
            "shipped_quantity": 0,
            "item_status": "NOT_STARTED",
        }

        items.append(item)

        used_products.add(
            product_id
        )

        total_weight += item_weight

    # --------------------------------------------------------
    # If the generated order is below the target minimum,
    # return what we have. The validation will identify
    # extremely unusual cases.
    # --------------------------------------------------------

    return items


# ============================================================
# GENERATE ALL ORDERS
# ============================================================


def generate_orders(
    number_of_orders,
    customers,
    products,
    inventory_index,
):
    """
    Generate orders and order items.

    Each order receives a target weight class.
    Actual weight is calculated from real products.
    """

    available_products = (
        build_available_product_pool(
            products,
            inventory_index,
        )
    )

    product_index = (
        build_product_index(
            products
        )
    )

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
            product_index=product_index,
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

        order["total_items"] = (
            total_items
        )

        order["total_weight_kg"] = round(
            total_weight,
            3,
        )

        # Reserve inventory for this order so that later orders
        # cannot request the same stock again.
        for item in items:
            product_id = item["product_id"]
            requested_quantity = int(
                item["requested_quantity"]
            )

            inventory_index[product_id] = (
                inventory_index.get(product_id, 0)
                - requested_quantity
            )

        orders.append(order)

        order_items.extend(
            items
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
    original_inventory_index=None,
):
    """
    Validate generated orders.
    """

    customer_ids = {
        customer["customer_id"]
        for customer in customers
    }

    order_ids = [
        order["order_id"]
        for order in orders
    ]

    assert len(
        order_ids
    ) == len(
        set(order_ids)
    ), (
        "Duplicate order_id values detected."
    )

    order_item_ids = [
        item["order_item_id"]
        for item in order_items
    ]

    assert len(
        order_item_ids
    ) == len(
        set(order_item_ids)
    ), (
        "Duplicate order_item_id values detected."
    )

    order_lookup = {
        order["order_id"]: order
        for order in orders
    }

    # --------------------------------------------------------
    # Validate order headers
    # --------------------------------------------------------

    for order in orders:

        assert (
            order["customer_id"]
            in customer_ids
        ), (
            f"Unknown customer_id: "
            f"{order['customer_id']}"
        )

        assert (
            order["order_status"]
            in ORDER_STATUSES
        ), (
            f"Invalid order status: "
            f"{order['order_status']}"
        )

        assert (
            order["delivery_priority"]
            in DELIVERY_PRIORITIES
        ), (
            f"Invalid delivery priority: "
            f"{order['delivery_priority']}"
        )

        assert (
            order["order_weight_class"]
            in ORDER_WEIGHT_CLASSES
        ), (
            f"Invalid weight class: "
            f"{order['order_weight_class']}"
        )

        assert (
            float(
                order[
                    "total_weight_kg"
                ]
            ) > 0
        ), (
            f"Invalid total weight "
            f"for {order['order_id']}"
        )

        assert (
            int(
                order[
                    "total_items"
                ]
            ) > 0
        ), (
            f"Invalid total items "
            f"for {order['order_id']}"
        )

        order_datetime = datetime.fromisoformat(
            order["order_datetime"]
        )
        requested_delivery_datetime = datetime.fromisoformat(
            order["requested_delivery_datetime"]
        )

        assert requested_delivery_datetime > order_datetime, (
            f"Requested delivery datetime must be after "
            f"order datetime for {order['order_id']}"
        )

    # --------------------------------------------------------
    # Validate order items
    # --------------------------------------------------------

    order_line_pairs = set()

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
            f"Unknown order_id: "
            f"{order_id}"
        )

        assert (
            product_id in inventory_index
        ), (
            f"Product {product_id} "
            f"does not exist in inventory."
        )

        pair = (
            order_id,
            product_id,
        )

        assert pair not in order_line_pairs, (
            "Duplicate product in order: "
            f"{pair}"
        )

        order_line_pairs.add(
            pair
        )

        requested_quantity = int(
            item[
                "requested_quantity"
            ]
        )

        validation_inventory = (
            original_inventory_index
            if original_inventory_index is not None
            else inventory_index
        )

        available_quantity = int(
            validation_inventory[
                product_id
            ]
        )

        assert (
            requested_quantity
            <= available_quantity
        ), (
            f"Requested quantity exceeds "
            f"inventory for product "
            f"{product_id}"
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
            requested_quantity
            * unit_weight
        )

        assert abs(
            total_weight
            - calculated_weight
        ) < 0.01, (
            f"Weight calculation mismatch "
            f"for {item['order_item_id']}"
        )

        assert (
            item["picked_quantity"]
            == 0
        )

        assert (
            item["packed_quantity"]
            == 0
        )

        assert (
            item["shipped_quantity"]
            == 0
        )

        assert (
            item["item_status"]
            == "NOT_STARTED"
        )

    # --------------------------------------------------------
    # Validate order totals
    # --------------------------------------------------------

    calculated_items = {}

    calculated_weights = {}

    for item in order_items:

        order_id = item[
            "order_id"
        ]

        calculated_items[
            order_id
        ] = (
            calculated_items.get(
                order_id,
                0,
            )
            + int(
                item[
                    "requested_quantity"
                ]
            )
        )

        calculated_weights[
            order_id
        ] = (
            calculated_weights.get(
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

        expected_items = (
            calculated_items[
                order_id
            ]
        )

        expected_weight = (
            calculated_weights[
                order_id
            ]
        )

        assert (
            int(
                order[
                    "total_items"
                ]
            )
            == expected_items
        ), (
            f"Item total mismatch "
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

    assert orders, "No orders were generated."

    assert order_items, "No order items were generated."

    if original_inventory_index is not None:
        for product_id, remaining_quantity in inventory_index.items():
            assert remaining_quantity >= 0, (
                f"Inventory reservation went below zero for "
                f"product {product_id}: {remaining_quantity}"
            )

        print(
            "Inventory reservation check passed."
        )

    if original_inventory_index is not None:
        requested_by_product = {}

        for item in order_items:
            product_id = item["product_id"]
            requested_by_product[product_id] = (
                requested_by_product.get(
                    product_id,
                    0,
                )
                + int(
                    item["requested_quantity"]
                )
            )

        for product_id, requested_quantity in requested_by_product.items():
            original_quantity = original_inventory_index.get(
                product_id,
                0,
            )

            assert requested_quantity <= original_quantity, (
                f"Global requested quantity exceeds inventory "
                f"for product {product_id}: "
                f"{requested_quantity} > {original_quantity}"
            )

    print(
        "Order validation passed."
    )


# ============================================================
# WEIGHT SUMMARY
# ============================================================


def print_weight_summary(
    orders,
):
    """
    Print distribution of generated order weights.
    """

    small = 0
    medium = 0
    heavy = 0
    very_heavy = 0
    two_to_three_tons = 0
    three_to_four_tons = 0
    four_plus_tons = 0

    for order in orders:

        weight = float(
            order[
                "total_weight_kg"
            ]
        )

        if weight < 100:
            small += 1

        elif weight < 500:
            medium += 1

        elif weight < 2000:
            heavy += 1

        else:
            very_heavy += 1

            if weight < 3000:
                two_to_three_tons += 1

            elif weight < 4000:
                three_to_four_tons += 1

            else:
                four_plus_tons += 1

    total = len(orders)

    print()
    print("Order Weight Distribution")
    print("==========================")

    print(
        f"Under 100 kg:       "
        f"{small:,} "
        f"({small / total * 100:.1f}%)"
    )

    print(
        f"100 - 500 kg:       "
        f"{medium:,} "
        f"({medium / total * 100:.1f}%)"
    )

    print(
        f"500 - 2,000 kg:     "
        f"{heavy:,} "
        f"({heavy / total * 100:.1f}%)"
    )

    print(
        f"2,000+ kg:          "
        f"{very_heavy:,} "
        f"({very_heavy / total * 100:.1f}%)"
    )

    print()
    print("Heavy Order Detail")
    print("==================")

    print(
        f"2,000 - 2,999 kg:    "
        f"{two_to_three_tons:,}"
    )

    print(
        f"3,000 - 3,999 kg:    "
        f"{three_to_four_tons:,}"
    )

    print(
        f"4,000+ kg:           "
        f"{four_plus_tons:,}"
    )


# ============================================================
# ORDER SUMMARY
# ============================================================


def print_order_summary(
    orders,
    order_items,
):
    """
    Print general order summary.
    """

    total_orders = len(
        orders
    )

    total_items = len(
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

    average_items_per_order = (
        total_items / total_orders
        if total_orders
        else 0
    )

    average_weight_per_order = (
        total_weight / total_orders
        if total_orders
        else 0
    )

    max_weight = max(
        float(
            order[
                "total_weight_kg"
            ]
        )
        for order in orders
    )

    min_weight = min(
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
        f"Orders:                 "
        f"{total_orders:,}"
    )

    print(
        f"Order items:            "
        f"{total_items:,}"
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
        f"{average_weight_per_order:,.1f} kg"
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
        f"{average_items_per_order:.2f}"
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

    original_inventory_index = (
        inventory_index.copy()
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
            inventory_index=inventory_index,
        )
    )

    print(
        f"Orders generated: "
        f"{len(orders):,}"
    )

    print(
        f"Order items generated: "
        f"{len(order_items):,}"
    )

    print()
    print("Validating orders...")

    validate_orders(
        orders=orders,
        order_items=order_items,
        customers=customers,
        inventory_index=inventory_index,
        original_inventory_index=original_inventory_index,
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


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================


if __name__ == "__main__":
    main()