"""
Warehouse Control Tower - Inventory Generator

Generates synthetic warehouse inventory from:
    product_master.csv
    locations.csv

Important:
    inventory.product_id is a foreign-key-style reference to
    product_master.product_id.

    article_number remains the business/article identifier in
    the product master and is not used as the inventory FK.
"""

from pathlib import Path
import csv
import random
from datetime import datetime


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRODUCT_FILE = PROCESSED_DIR / "product_master.csv"
LOCATIONS_FILE = PROCESSED_DIR / "locations.csv"
INVENTORY_FILE = PROCESSED_DIR / "inventory.csv"


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

TARGET_OCCUPANCY = 0.70

INVENTORY_ID_START = 1

STATUS = "AVAILABLE"

STORAGE_TYPES = {
    "PALLET_STORAGE",
    "BOX_STORAGE",
}


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
# LOAD PRODUCTS
# ============================================================

def load_products():
    products = read_csv(PRODUCT_FILE)

    if not products:
        raise ValueError(
            "Product master is empty."
        )

    required = {
        "product_id",
        "article_number",
    }

    missing = required - set(products[0].keys())

    if missing:
        raise ValueError(
            f"Product master missing fields: {missing}"
        )

    product_ids = [
        row["product_id"].strip()
        for row in products
        if row["product_id"].strip()
    ]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError(
            "Duplicate product_id values in product master."
        )

    return products


# ============================================================
# LOAD LOCATIONS
# ============================================================

def load_locations():
    locations = read_csv(LOCATIONS_FILE)

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

    missing = required - set(locations[0].keys())

    if missing:
        raise ValueError(
            f"Locations missing fields: {missing}"
        )

    for row in locations:
        if row["storage_type"] not in STORAGE_TYPES:
            raise ValueError(
                f"Invalid storage_type: "
                f"{row['storage_type']}"
            )

    return locations


# ============================================================
# INVENTORY QUANTITY
# ============================================================

def generate_quantity(storage_type):
    """
    Generate synthetic stock quantity.

    Pallet storage carries larger quantities.
    Box storage carries smaller picking quantities.
    """

    if storage_type == "PALLET_STORAGE":
        return random.randint(50, 500)

    return random.randint(1, 100)


# ============================================================
# CONTAINER TYPE
# ============================================================

def generate_container_type(storage_type):
    """
    Map storage type to the physical inventory container.

    PALLET_STORAGE -> PALLET
    BOX_STORAGE    -> BOX
    """

    if storage_type == "PALLET_STORAGE":
        return "PALLET"

    return "BOX"


# ============================================================
# CONTAINER ID
# ============================================================

def generate_container_id(
    container_type,
    inventory_number,
):
    return (
        f"{container_type}-"
        f"INV-{inventory_number:06d}"
    )


# ============================================================
# INVENTORY GENERATION
# ============================================================

def generate_inventory(
    products,
    locations,
):
    """
    Generate one inventory record per occupied location.

    The occupied locations are selected according to the
    configured warehouse occupancy target.

    Each occupied location receives one product.

    Product assignment uses product_master.product_id so that
    inventory.product_id is a valid reference to the product
    master.

    The same product may be placed at multiple locations in
    future model extensions; the current generator keeps the
    initial dataset simple and deterministic by assigning
    unique products to occupied locations.
    """

    target_count = int(
        len(locations) * TARGET_OCCUPANCY
    )

    if target_count > len(products):
        raise ValueError(
            "Not enough products to assign unique products "
            "to all occupied locations."
        )

    pallet_locations = [
        row
        for row in locations
        if row["storage_type"] == "PALLET_STORAGE"
    ]

    box_locations = [
        row
        for row in locations
        if row["storage_type"] == "BOX_STORAGE"
    ]

    # Select occupied locations independently by storage type
    # so the inventory reflects the physical warehouse mix.
    pallet_target = min(
        len(pallet_locations),
        round(
            target_count
            * len(pallet_locations)
            / len(locations)
        ),
    )

    box_target = target_count - pallet_target

    if box_target > len(box_locations):
        box_target = len(box_locations)
        pallet_target = target_count - box_target

    if pallet_target > len(pallet_locations):
        pallet_target = len(pallet_locations)
        box_target = target_count - pallet_target

    selected_pallet_locations = random.sample(
        pallet_locations,
        pallet_target,
    )

    selected_box_locations = random.sample(
        box_locations,
        box_target,
    )

    selected_locations = (
        selected_pallet_locations
        + selected_box_locations
    )

    random.shuffle(selected_locations)

    # Use product_id directly as the FK.
    product_pool = [
        row["product_id"].strip()
        for row in products
        if row["product_id"].strip()
    ]

    selected_products = random.sample(
        product_pool,
        len(selected_locations),
    )

    inventory = []

    for number, (location, product_id) in enumerate(
        zip(
            selected_locations,
            selected_products,
        ),
        start=INVENTORY_ID_START,
    ):
        storage_type = location["storage_type"]

        container_type = generate_container_type(
            storage_type
        )

        inventory.append(
            {
                "inventory_id": (
                    f"INV-{number:06d}"
                ),
                "product_id": product_id,
                "location_id": location[
                    "location_id"
                ],
                "hall_id": location[
                    "hall_id"
                ],
                "zone_nr": location[
                    "zone_nr"
                ],
                "storage_type": storage_type,
                "picking_method": location[
                    "picking_method"
                ],
                "quantity": generate_quantity(
                    storage_type
                ),
                "container_type": container_type,
                "container_id": generate_container_id(
                    container_type,
                    number,
                ),
                "status": STATUS,
                "last_updated": (
                    datetime.now().isoformat(
                        timespec="seconds"
                    )
                ),
            }
        )

    return inventory


# ============================================================
# VALIDATION
# ============================================================

def validate_inventory(
    inventory,
    products,
    locations,
):
    product_ids = {
        row["product_id"]
        for row in products
    }

    location_ids = {
        row["location_id"]
        for row in locations
    }

    inventory_ids = [
        row["inventory_id"]
        for row in inventory
    ]

    assert len(inventory_ids) == len(
        set(inventory_ids)
    ), "Duplicate inventory_id values."

    occupied_locations = [
        row["location_id"]
        for row in inventory
    ]

    assert len(occupied_locations) == len(
        set(occupied_locations)
    ), (
        "Duplicate occupied locations found. "
        "A location may contain only one inventory "
        "record in this initial model."
    )

    for row in inventory:
        assert row["product_id"] in product_ids, (
            f"Unknown product_id: "
            f"{row['product_id']}"
        )

        assert row["location_id"] in location_ids, (
            f"Unknown location_id: "
            f"{row['location_id']}"
        )

        quantity = int(
            float(row["quantity"])
        )

        assert quantity > 0

        assert row["status"] == STATUS

        if row["storage_type"] == "PALLET_STORAGE":
            assert row["container_type"] == "PALLET"

        elif row["storage_type"] == "BOX_STORAGE":
            assert row["container_type"] == "BOX"

    assert len(inventory) > 0

    print(
        "Inventory validation passed."
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    inventory,
):
    total_quantity = sum(
        int(
            float(row["quantity"])
        )
        for row in inventory
    )

    pallet_count = sum(
        row["container_type"] == "PALLET"
        for row in inventory
    )

    box_count = sum(
        row["container_type"] == "BOX"
        for row in inventory
    )

    print()
    print("Warehouse Inventory Summary")
    print("===========================")

    print(
        f"Inventory records:     "
        f"{len(inventory):,}"
    )

    print(
        f"Total quantity:        "
        f"{total_quantity:,}"
    )

    print(
        f"Pallet inventory:      "
        f"{pallet_count:,}"
    )

    print(
        f"Box inventory:         "
        f"{box_count:,}"
    )


# ============================================================
# EXPORT
# ============================================================

def export_inventory(
    inventory,
):
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "inventory_id",
        "product_id",
        "location_id",
        "hall_id",
        "zone_nr",
        "storage_type",
        "picking_method",
        "quantity",
        "container_type",
        "container_id",
        "status",
        "last_updated",
    ]

    with INVENTORY_FILE.open(
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
            inventory
        )

    print()
    print("Inventory export complete:")
    print(INVENTORY_FILE)


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("Warehouse Inventory Generator")
    print("=============================")

    print()
    print("Loading products...")

    products = load_products()

    print(
        f"Products loaded:       "
        f"{len(products):,}"
    )

    print()
    print("Loading locations...")

    locations = load_locations()

    print(
        f"Locations loaded:      "
        f"{len(locations):,}"
    )

    print()
    print("Generating inventory...")

    inventory = generate_inventory(
        products=products,
        locations=locations,
    )

    print(
        f"Inventory generated:   "
        f"{len(inventory):,}"
    )

    print()
    print("Validating inventory...")

    validate_inventory(
        inventory=inventory,
        products=products,
        locations=locations,
    )

    print_summary(
        inventory
    )

    export_inventory(
        inventory
    )


if __name__ == "__main__":
    main()
