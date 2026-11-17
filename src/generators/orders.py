from pathlib import Path
import os
import csv
import random
import hashlib
from datetime import datetime, timedelta

from working_time import (
    add_working_days,
    load_capacity_by_date,
    random_order_time_of_day,
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = Path(
    os.getenv("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed")
).resolve()

PRODUCT_FILE = PROCESSED_DIR / "product_master.csv"
INVENTORY_FILE = PROCESSED_DIR / "inventory.csv"

CUSTOMERS_FILE = PROCESSED_DIR / "customers.csv"
ORDERS_FILE = PROCESSED_DIR / "orders.csv"
ORDER_ITEMS_FILE = PROCESSED_DIR / "order_items.csv"

CALENDAR_FILE = PROCESSED_DIR / "calendar.csv"


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

ORDERS_PER_YEAR = {
    2024: 34_000,
    2025: 40_000,
    2026: 36_000,
}

MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 40

MIN_QUANTITY_PER_ITEM = 1
MAX_QUANTITY_PER_ITEM = 500

ORDER_ID_START = 1

CUSTOMER_COUNT = 500


# ============================================================
# BUSINESS CALENDAR
# ============================================================

CALENDAR_REQUIRED_FIELDS = {
    "date",
    "demand_multiplier",
}


# ============================================================
# ORDER WEIGHT DISTRIBUTION (<= 30 kg BOXES, > 30 kg PALLETS)
# ============================================================

ORDER_WEIGHT_CLASSES = [
    "SMALL",
    "MEDIUM",
    "HEAVY",
    "VERY_HEAVY",
]

ORDER_WEIGHT_CLASS_WEIGHTS = {
    "SMALL": 0.58,       # 0.2 - 10.0 kg (postal/parcel small boxes, often 1 item & 1 qty)
    "MEDIUM": 0.26,      # 10.1 - 30.0 kg (boxes up to 30 kg limit)
    "HEAVY": 0.11,       # 30.5 - 350.0 kg (pallets > 30 kg)
    "VERY_HEAVY": 0.05,  # 350.0 - 2,500.0 kg (heavy pallets > 30 kg)
}

ORDER_WEIGHT_RANGES = {
    "SMALL": (0.2, 10.0),
    "MEDIUM": (10.1, 30.0),
    "HEAVY": (30.5, 350.0),
    "VERY_HEAVY": (350.0, 2500.0),
}

VERY_HEAVY_SUBRANGES = [
    (350.0, 799.9),
    (800.0, 1499.9),
    (1500.0, 2500.0),
]

ORDER_LINE_COUNT_RANGES = [
    (1, 3),
    (4, 8),
    (9, 15),
    (16, 25),
    (26, 40),
]

ORDER_LINE_COUNT_WEIGHTS = [
    0.52,
    0.30,
    0.11,
    0.05,
    0.02,
]


# ============================================================
# ORDER STATUS & PRIORITY
# ============================================================

FINAL_ORDER_STATUS = "DELIVERED"

ORDER_STATUSES = [
    FINAL_ORDER_STATUS,
]

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
# BUSINESS CALENDAR
# ============================================================

def load_business_calendar():
    calendar_rows = read_csv(CALENDAR_FILE)

    if not calendar_rows:
        raise ValueError("Business calendar is empty.")

    missing_fields = CALENDAR_REQUIRED_FIELDS - set(calendar_rows[0].keys())
    if missing_fields:
        raise ValueError(
            f"Business calendar is missing fields: {missing_fields}"
        )

    weighted_days = []

    for row in calendar_rows:
        date_value = str(row.get("date", "")).strip()
        if not date_value:
            continue

        try:
            demand_multiplier = float(row.get("demand_multiplier", 0))
        except (ValueError, TypeError):
            continue

        if demand_multiplier <= 0:
            continue

        try:
            selected_date = datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            continue

        if selected_date.year not in ORDERS_PER_YEAR:
            continue

        weighted_days.append((selected_date, demand_multiplier))

    if not weighted_days:
        raise ValueError(
            "Business calendar contains no dates with positive demand."
        )

    capacity_by_date = get_capacity_by_date()
    eligible_days = []
    excluded_for_deadline_coverage = 0

    for selected_date, demand_weight in weighted_days:
        try:
            add_working_days(
                datetime.combine(selected_date, datetime.min.time()),
                5,
                capacity_by_date,
            )
        except ValueError:
            excluded_for_deadline_coverage += 1
            continue
        eligible_days.append((selected_date, demand_weight))

    weighted_days = eligible_days

    if not weighted_days:
        raise ValueError(
            "Calendar has no order dates with enough future coverage "
            "for 5 working-day delivery deadlines."
        )

    days_by_year = {}
    for selected_date, demand_weight in weighted_days:
        days_by_year.setdefault(selected_date.year, []).append(
            (selected_date, demand_weight)
        )

    print(
        f"Order dates excluded (insufficient deadline buffer): "
        f"{excluded_for_deadline_coverage:,}"
    )

    print()
    print("Business Calendar Validation")
    print("============================")
    print(f"Calendar rows loaded: {len(calendar_rows):,}")
    print(f"Order-active dates: {len(weighted_days):,}")
    print(f"Total demand weight: {sum(weight for _, weight in weighted_days):.3f}")
    print("Orders configured per calendar year:")
    for year in sorted(days_by_year):
        annual_target = ORDERS_PER_YEAR[year]
        print(
            f"  {year}: {annual_target:,} orders across "
            f"{len(days_by_year[year]):,} active dates"
        )

    missing_years = set(ORDERS_PER_YEAR) - set(days_by_year)
    if missing_years:
        raise ValueError(
            f"Missing calendar dates for configured years: {sorted(missing_years)}"
        )

    return days_by_year


# ============================================================
# PRODUCT WEIGHT
# ============================================================

def generate_synthetic_unit_weight(product):
    article_number = str(product.get("article_number", "")).strip()

    digest = hashlib.sha256(article_number.encode("utf-8")).hexdigest()
    seed_value = int(digest[:16], 16)
    normalized = seed_value / float(16**16 - 1)

    minimum = 0.05
    maximum = 15.0

    weight = minimum * ((maximum / minimum) ** normalized)
    return round(weight, 3)


def parse_source_weight(raw_weight):
    if raw_weight is None:
        return None

    value = str(raw_weight).strip()
    if not value:
        return None

    try:
        if "," in value and "." in value:
            if value.rfind(",") > value.rfind("."):
                value = value.replace(".", "").replace(",", ".")
            else:
                value = value.replace(",", "")
        elif "," in value:
            value = value.replace(",", ".")

        parsed = float(value)
        if parsed > 0:
            return parsed
    except (ValueError, TypeError):
        pass

    return None


def load_products():
    products = read_csv(PRODUCT_FILE)

    if not products:
        raise ValueError("Product master is empty.")

    required_fields = {
        "product_id",
        "article_number",
        "unit_weight_kg",
    }

    missing_fields = required_fields - set(products[0].keys())
    if missing_fields:
        raise ValueError(
            f"Product master is missing fields: {missing_fields}"
        )

    valid_products = []
    source_weight_count = 0
    synthetic_weight_count = 0
    invalid_weight_count = 0

    for product in products:
        product_id = str(product.get("product_id", "")).strip()
        article_number = str(product.get("article_number", "")).strip()

        if not product_id or product_id.lower() in {"none", "nan", "<na>"}:
            continue
        if not article_number or article_number.lower() in {"none", "nan", "<na>"}:
            continue

        source_weight = parse_source_weight(product.get("unit_weight_kg", ""))

        if source_weight is not None:
            product["unit_weight_kg"] = round(source_weight, 3)
            product["weight_source"] = "ABB_SOURCE"
            source_weight_count += 1
        else:
            if product.get("unit_weight_kg", ""):
                invalid_weight_count += 1

            product["unit_weight_kg"] = generate_synthetic_unit_weight(product)
            product["weight_source"] = "SYNTHETIC"
            synthetic_weight_count += 1

        valid_products.append(product)

    print()
    print("Product Weight Validation")
    print("=========================")
    print(f"Total products:         {len(products):,}")
    print(f"ABB source weights:     {source_weight_count:,}")
    print(f"Synthetic weights:      {synthetic_weight_count:,}")
    print(f"Invalid source weights: {invalid_weight_count:,}")

    if not valid_products:
        raise ValueError("No valid products available.")

    return valid_products


# ============================================================
# INVENTORY
# ============================================================

def load_inventory():
    inventory = read_csv(INVENTORY_FILE)

    if not inventory:
        raise ValueError("Inventory is empty.")

    required_fields = {
        "inventory_id",
        "product_id",
        "quantity",
    }

    missing_fields = required_fields - set(inventory[0].keys())
    if missing_fields:
        raise ValueError(
            f"Inventory is missing fields: {missing_fields}"
        )

    return inventory


def build_inventory_index(inventory):
    inventory_index = {}

    for record in inventory:
        product_id = str(record.get("product_id", "")).strip()
        if not product_id or product_id.lower() in {"none", "nan", "<na>"}:
            raise ValueError("Inventory contains a missing product_id.")

        try:
            quantity_value = float(record.get("quantity", ""))
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid inventory quantity for product {product_id}: "
                f"{record.get('quantity')!r}"
            )

        if not quantity_value.is_integer() or quantity_value < 0:
            raise ValueError(
                f"Inventory quantity must be a non-negative integer: "
                f"{product_id}={quantity_value}"
            )

        inventory_index[product_id] = (
            inventory_index.get(product_id, 0) + int(quantity_value)
        )

    return inventory_index


# ============================================================
# AVAILABLE PRODUCT POOL
# ============================================================

def build_available_product_pool(products, inventory_index):
    available_products = []

    for product in products:
        product_id = product["product_id"]
        quantity = inventory_index.get(product_id, 0)
        if quantity <= 0:
            continue

        unit_weight = float(product["unit_weight_kg"])
        if unit_weight <= 0:
            continue

        available_products.append(product)

    if not available_products:
        raise ValueError(
            "No products with positive inventory are available."
        )

    return available_products


# ============================================================
# CUSTOMER GENERATION
# ============================================================

def generate_customer_id(number):
    return f"CUST-{number:05d}"


def generate_customers(count=CUSTOMER_COUNT):
    customers = []

    for number in range(1, count + 1):
        customer_type = random.choices(
            ["B2B", "B2C"],
            weights=[0.80, 0.20],
            k=1,
        )[0]

        customers.append(
            {
                "customer_id": generate_customer_id(number),
                "customer_type": customer_type,
                "status": "ACTIVE",
            }
        )

    return customers


# ============================================================
# DELIVERY PRIORITY & ORDER DATETIME
# ============================================================

def generate_delivery_priority():
    priorities = list(DELIVERY_PRIORITY_WEIGHTS.keys())
    weights = [DELIVERY_PRIORITY_WEIGHTS[p] for p in priorities]
    return random.choices(priorities, weights=weights, k=1)[0]


_CAPACITY_BY_DATE = None


def get_capacity_by_date():
    global _CAPACITY_BY_DATE
    if _CAPACITY_BY_DATE is None:
        _CAPACITY_BY_DATE = load_capacity_by_date(CALENDAR_FILE)
    return _CAPACITY_BY_DATE


def generate_order_datetime(business_calendar_days):
    selected_date = random.choices(
        business_calendar_days,
        weights=[weight for _, weight in business_calendar_days],
        k=1,
    )[0][0]

    return (
        datetime.combine(selected_date, datetime.min.time())
        + random_order_time_of_day()
    )


# ============================================================
# WEIGHT CLASS & PRODUCT SELECTION
# ============================================================

def generate_weight_class():
    classes = list(ORDER_WEIGHT_CLASS_WEIGHTS.keys())
    weights = [ORDER_WEIGHT_CLASS_WEIGHTS[c] for c in classes]
    return random.choices(classes, weights=weights, k=1)[0]


def generate_weight_target(weight_class):
    if weight_class == "VERY_HEAVY":
        return random.choice(VERY_HEAVY_SUBRANGES)
    return ORDER_WEIGHT_RANGES[weight_class]


def choose_product_for_order(available_products, target_min_weight, target_max_weight):
    sample_size = min(100, len(available_products))
    candidates = random.sample(available_products, sample_size)

    if target_max_weight <= 10.0:
        light_candidates = [
            p for p in candidates if float(p["unit_weight_kg"]) <= 2.0
        ]
        if light_candidates:
            return random.choice(light_candidates)

    elif target_max_weight <= 30.0:
        medium_candidates = [
            p for p in candidates if 0.2 <= float(p["unit_weight_kg"]) <= 8.0
        ]
        if medium_candidates:
            return random.choice(medium_candidates)

    elif target_min_weight >= 350.0:
        heavy_candidates = [
            p for p in candidates if float(p["unit_weight_kg"]) >= 3.0
        ]
        if heavy_candidates:
            return random.choice(heavy_candidates)

    return random.choice(available_products)


# ============================================================
# ORDER HEADER & ITEMS
# ============================================================

def generate_order(
    order_number,
    customer,
    weight_class,
    business_calendar_days,
):
    order_id = f"ORD-{order_number:08d}"
    order_datetime = generate_order_datetime(business_calendar_days)

    requested_delivery_datetime = add_working_days(
        order_datetime,
        random.randint(2, 5),
        get_capacity_by_date(),
    )

    return {
        "order_id": order_id,
        "customer_id": customer["customer_id"],
        "order_datetime": order_datetime.isoformat(timespec="seconds"),
        "order_status": FINAL_ORDER_STATUS,
        "delivery_priority": generate_delivery_priority(),
        "order_weight_class": weight_class,
        "requested_delivery_datetime": requested_delivery_datetime.isoformat(
            timespec="seconds"
        ),
        "total_items": 0,
        "total_weight_kg": 0.0,
    }


def generate_order_line_count(weight_class):
    # Postal/parcel SMALL orders are predominantly 1-2 lines (often 1 single item)
    if weight_class == "SMALL":
        return random.choices([1, 2, 3, 4], weights=[0.60, 0.25, 0.10, 0.05], k=1)[0]
    if weight_class == "MEDIUM":
        return random.choices([1, 2, 3, 4, 5, 6], weights=[0.20, 0.25, 0.20, 0.15, 0.12, 0.08], k=1)[0]

    selected_range = random.choices(
        ORDER_LINE_COUNT_RANGES,
        weights=ORDER_LINE_COUNT_WEIGHTS,
        k=1,
    )[0]
    return random.randint(*selected_range)


def generate_requested_quantity(weight_class):
    # Postal/parcel SMALL orders very frequently order just 1 piece of a product
    if weight_class == "SMALL":
        return random.choices([1, 2, 3, 4, 5], weights=[0.65, 0.18, 0.09, 0.05, 0.03], k=1)[0]
    if weight_class == "MEDIUM":
        return random.choices([1, 2, 3, 5, 10, 15], weights=[0.25, 0.25, 0.20, 0.15, 0.10, 0.05], k=1)[0]

    quantity_ranges = [
        (1, 15),
        (16, 60),
        (61, 150),
        (151, MAX_QUANTITY_PER_ITEM),
    ]
    quantity_weights = [0.35, 0.40, 0.18, 0.07]

    selected_range = random.choices(
        quantity_ranges,
        weights=quantity_weights,
        k=1,
    )[0]
    return random.randint(*selected_range)


def create_order_item(order, product, line_number, quantity):
    unit_weight = float(product["unit_weight_kg"])
    total_weight = quantity * unit_weight

    return {
        "order_item_id": f"{order['order_id']}-ITEM-{line_number:02d}",
        "order_id": order["order_id"],
        "line_number": line_number,
        "product_id": product["product_id"],
        "requested_quantity": quantity,
        "unit_weight_kg": round(unit_weight, 3),
        "weight_source": product.get("weight_source", "SYNTHETIC"),
        "total_weight_kg": round(total_weight, 3),
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
    items = []
    used_products = set()
    total_weight = 0.0
    weight_class = order["order_weight_class"]

    target_lines = min(
        MAX_ITEMS_PER_ORDER,
        max(MIN_ITEMS_PER_ORDER, generate_order_line_count(weight_class)),
    )

    for line_number in range(1, target_lines + 1):
        remaining_weight = target_max_weight - total_weight
        if remaining_weight <= 0:
            break

        product = None
        for _ in range(12):
            candidate = choose_product_for_order(
                available_products,
                target_min_weight,
                target_max_weight,
            )
            if candidate["product_id"] not in used_products:
                product = candidate
                break

        if product is None:
            break

        product_id = product["product_id"]
        unit_weight = float(product["unit_weight_kg"])
        if unit_weight <= 0:
            continue

        remaining_lines = target_lines - line_number

        if remaining_lines == 0 and total_weight < target_min_weight and weight_class != "SMALL":
            required_weight = target_min_weight - total_weight
            quantity = max(1, int(round(required_weight / unit_weight)))
        else:
            quantity = generate_requested_quantity(weight_class)

        if target_min_weight >= 350.0:
            quantity = max(
                quantity,
                int((target_min_weight / max(target_lines, 1)) / unit_weight),
            )

        max_quantity_by_weight = int(remaining_weight / unit_weight)
        if max_quantity_by_weight <= 0:
            continue

        quantity = min(
            quantity,
            MAX_QUANTITY_PER_ITEM,
            max_quantity_by_weight,
            inventory_index.get(product_id, 0),
        )

        if quantity < 1:
            continue

        item = create_order_item(
            order=order,
            product=product,
            line_number=line_number,
            quantity=quantity,
        )

        items.append(item)
        used_products.add(product_id)
        total_weight += float(item["total_weight_kg"])

    if total_weight < target_min_weight and len(items) < MAX_ITEMS_PER_ORDER and weight_class != "SMALL":
        required_weight = target_min_weight - total_weight
        sample_size = min(100, len(available_products))
        candidates = random.sample(available_products, sample_size)

        candidates = [
            product
            for product in candidates
            if product["product_id"] not in used_products
            and 0 < float(product["unit_weight_kg"]) <= (target_max_weight - total_weight)
        ]

        if candidates:
            product = min(
                candidates,
                key=lambda candidate: abs(
                    float(candidate["unit_weight_kg"]) - required_weight
                ),
            )

            unit_weight = float(product["unit_weight_kg"])
            max_allowed_qty = int((target_max_weight - total_weight) / unit_weight)
            quantity = max(1, int(round(required_weight / unit_weight)))
            quantity = min(
                quantity,
                max_allowed_qty,
                MAX_QUANTITY_PER_ITEM,
                inventory_index.get(product["product_id"], 0),
            )

            if quantity >= 1:
                line_number = (
                    max(
                        (int(existing["line_number"]) for existing in items),
                        default=0,
                    )
                    + 1
                )

                item = create_order_item(
                    order=order,
                    product=product,
                    line_number=line_number,
                    quantity=quantity,
                )
                items.append(item)

    return items


# ============================================================
# GENERATE ORDERS
# ============================================================

def generate_orders(
    orders_per_year,
    customers,
    products,
    inventory_index,
    business_calendar_days_by_year,
):
    available_products = build_available_product_pool(products, inventory_index)
    product_index = {product["product_id"]: product for product in products}

    orders = []
    order_items = []
    next_order_number = ORDER_ID_START
    total_to_generate = sum(
        orders_per_year[year] for year in business_calendar_days_by_year
    )
    generated_count = 0

    for year in sorted(business_calendar_days_by_year):
        year_days = business_calendar_days_by_year[year]
        annual_target = orders_per_year[year]
        print(f"\nGenerating {annual_target:,} orders for {year}...")

        year_generated = 0
        while year_generated < annual_target:
            weight_class = generate_weight_class()
            target_min_weight, target_max_weight = generate_weight_target(weight_class)
            customer = random.choice(customers)

            order = generate_order(
                order_number=next_order_number,
                customer=customer,
                weight_class=weight_class,
                business_calendar_days=year_days,
            )

            items = generate_order_items(
                order=order,
                available_products=available_products,
                inventory_index=inventory_index,
                product_index=product_index,
                target_min_weight=target_min_weight,
                target_max_weight=target_max_weight,
            )

            if not items:
                continue

            total_items = sum(int(item["requested_quantity"]) for item in items)
            total_weight = sum(float(item["total_weight_kg"]) for item in items)
            order["total_items"] = total_items
            order["total_weight_kg"] = round(total_weight, 3)

            orders.append(order)
            order_items.extend(items)
            next_order_number += 1
            year_generated += 1
            generated_count += 1

            if generated_count % 5_000 == 0:
                print(
                    f"  Generated {generated_count:,} / {total_to_generate:,} orders..."
                )

        print(f"  {year}: generated {year_generated:,} orders.")

    return orders, order_items


# ============================================================
# VALIDATION
# ============================================================

def validate_orders(orders, order_items, customers, inventory_index):
    assert orders, "No orders were generated."
    assert order_items, "No order items were generated."

    customer_ids = {customer["customer_id"] for customer in customers}
    order_ids = [order["order_id"] for order in orders]
    assert len(order_ids) == len(set(order_ids)), "Duplicate order IDs detected."

    order_item_ids = [item["order_item_id"] for item in order_items]
    assert len(order_item_ids) == len(set(order_item_ids)), (
        "Duplicate order item IDs detected."
    )

    order_lookup = {order["order_id"]: order for order in orders}

    for order in orders:
        order_id = order["order_id"]
        assert order["customer_id"] in customer_ids
        assert order["order_status"] in ORDER_STATUSES
        assert order["delivery_priority"] in DELIVERY_PRIORITIES
        assert order["order_weight_class"] in ORDER_WEIGHT_CLASSES
        assert float(order["total_weight_kg"]) > 0
        assert int(order["total_items"]) > 0

        order_datetime = datetime.fromisoformat(order["order_datetime"])
        delivery_datetime = datetime.fromisoformat(
            order["requested_delivery_datetime"]
        )
        assert delivery_datetime > order_datetime

    order_product_pairs = set()

    for item in order_items:
        order_id = item["order_id"]
        product_id = item["product_id"]

        assert order_id in order_lookup
        assert product_id in inventory_index

        pair = (order_id, product_id)
        assert pair not in order_product_pairs
        order_product_pairs.add(pair)

        quantity = int(item["requested_quantity"])
        assert MIN_QUANTITY_PER_ITEM <= quantity <= MAX_QUANTITY_PER_ITEM
        assert quantity <= inventory_index[product_id]

        unit_weight = float(item["unit_weight_kg"])
        total_weight = float(item["total_weight_kg"])
        assert abs(quantity * unit_weight - total_weight) < 0.01

        assert item["picked_quantity"] == 0
        assert item["packed_quantity"] == 0
        assert item["shipped_quantity"] == 0
        assert item["item_status"] == "NOT_STARTED"

    calculated_quantity = {}
    calculated_weight = {}

    for item in order_items:
        order_id = item["order_id"]
        calculated_quantity[order_id] = (
            calculated_quantity.get(order_id, 0)
            + int(item["requested_quantity"])
        )
        calculated_weight[order_id] = (
            calculated_weight.get(order_id, 0.0)
            + float(item["total_weight_kg"])
        )

    for order in orders:
        order_id = order["order_id"]
        assert int(order["total_items"]) == calculated_quantity[order_id]
        assert abs(
            float(order["total_weight_kg"]) - calculated_weight[order_id]
        ) < 0.01

    print("Order validation passed.")


# ============================================================
# SUMMARY & EXPORTS
# ============================================================

def print_order_summary(orders, order_items):
    total_orders = len(orders)
    total_order_items = len(order_items)
    total_requested_quantity = sum(
        int(item["requested_quantity"]) for item in order_items
    )
    total_weight = sum(float(order["total_weight_kg"]) for order in orders)

    average_weight = total_weight / total_orders if total_orders else 0
    average_items = total_order_items / total_orders if total_orders else 0
    min_weight = min(float(order["total_weight_kg"]) for order in orders)
    max_weight = max(float(order["total_weight_kg"]) for order in orders)
    single_qty_lines = sum(int(item["requested_quantity"]) == 1 for item in order_items)

    print()
    print("Warehouse Order Summary")
    print("=======================")
    print(f"Orders generated:       {total_orders:,}")
    print(f"Order items generated:  {total_order_items:,}")
    print(f"Single-piece lines (1): {single_qty_lines:,} ({single_qty_lines / total_order_items * 100:.1f}%)")
    print(f"Requested quantity:     {total_requested_quantity:,}")
    print(f"Total order weight:     {total_weight:,.1f} kg")
    print(f"Average order weight:   {average_weight:,.1f} kg")
    print(f"Minimum order weight:   {min_weight:,.1f} kg")
    print(f"Maximum order weight:   {max_weight:,.1f} kg")
    print(f"Avg order lines:        {average_items:.2f}")


def print_weight_summary(orders):
    up_to_30 = sum(float(o["total_weight_kg"]) <= 30.0 for o in orders)
    above_30 = sum(float(o["total_weight_kg"]) > 30.0 for o in orders)
    total = len(orders)

    print()
    print("Order Weight Distribution (<= 30 kg Box vs > 30 kg Pallet)")
    print("===========================================================")
    print(f"Up to 30 kg (Boxes):    {up_to_30:,} ({up_to_30 / total * 100:.1f}%)")
    print(f"Over 30 kg (Pallets):   {above_30:,} ({above_30 / total * 100:.1f}%)")


def export_customers(customers, output_file=CUSTOMERS_FILE):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["customer_id", "customer_type", "status"]

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(customers)

    print("\nCustomers export complete:")
    print(output_file)


def export_orders(orders, output_file=ORDERS_FILE):
    output_file.parent.mkdir(parents=True, exist_ok=True)
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

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(orders)

    print("\nOrders export complete:")
    print(output_file)


def export_order_items(order_items, output_file=ORDER_ITEMS_FILE):
    output_file.parent.mkdir(parents=True, exist_ok=True)
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

    with output_file.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(order_items)

    print("\nOrder items export complete:")
    print(output_file)


def main():
    print()
    print("Warehouse Order Generator")
    print("==========================")

    print("\nLoading products...")
    products = load_products()
    print(f"Products loaded: {len(products):,}")

    print("\nLoading inventory...")
    inventory = load_inventory()
    print(f"Inventory records loaded: {len(inventory):,}")

    print("\nBuilding inventory index...")
    inventory_index = build_inventory_index(inventory)
    print(f"Products with inventory: {len(inventory_index):,}")

    print("\nLoading business calendar...")
    business_calendar_days = load_business_calendar()

    print("\nGenerating customers...")
    customers = generate_customers()
    print(f"Customers generated: {len(customers):,}")

    print("\nGenerating orders...")
    orders, order_items = generate_orders(
        orders_per_year=ORDERS_PER_YEAR,
        customers=customers,
        products=products,
        inventory_index=inventory_index,
        business_calendar_days_by_year=business_calendar_days,
    )

    print("\nValidating orders...")
    validate_orders(
        orders=orders,
        order_items=order_items,
        customers=customers,
        inventory_index=inventory_index,
    )

    print_order_summary(orders, order_items)
    print_weight_summary(orders)

    export_customers(customers)
    export_orders(orders)
    export_order_items(order_items)

    print("\nOrder generation completed successfully.")


if __name__ == "__main__":
    main()