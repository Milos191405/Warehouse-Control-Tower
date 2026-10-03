from pathlib import Path
import csv
import random


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

PRODUCT_FILE = (
    PROCESSED_DIR
    / "product_master.csv"
)

LOCATION_FILE = (
    PROCESSED_DIR
    / "locations.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "inventory.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

RANDOM_SEED = 42

TARGET_OCCUPANCY = 0.70

MIN_PALLET_QUANTITY = 10
MAX_PALLET_QUANTITY = 500

MIN_BOX_QUANTITY = 1
MAX_BOX_QUANTITY = 100

MAX_PRODUCTS = None
# None = use all available products


# ============================================================
# STORAGE RULES
# ============================================================

PALLET_STORAGE_TYPES = {
    "PALLET_STORAGE",
}

BOX_STORAGE_TYPES = {
    "BOX_STORAGE",
}


# ============================================================
# RANDOM GENERATOR
# ============================================================

random.seed(RANDOM_SEED)


# ============================================================
# CSV HELPERS
# ============================================================


def read_csv(file_path):
    """
    Read a CSV file and return a list of dictionaries.
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
# PRODUCT LOADING
# ============================================================


def load_products():
    """
    Load product master data.

    Required field:
        article_number
    """

    products = read_csv(
        PRODUCT_FILE
    )

    if not products:
        raise ValueError(
            "Product master is empty."
        )

    required_fields = {
        "article_number",
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

    # Remove products without an article number.
    products = [
        product
        for product in products
        if product["article_number"]
    ]

    if MAX_PRODUCTS is not None:
        products = products[
            :MAX_PRODUCTS
        ]

    return products


# ============================================================
# LOCATION LOADING
# ============================================================


def load_locations():
    """
    Load generated warehouse locations.
    """

    locations = read_csv(
        LOCATION_FILE
    )

    if not locations:
        raise ValueError(
            "Location file is empty."
        )

    required_fields = {
        "location_id",
        "hall_id",
        "zone_nr",
        "storage_type",
        "picking_method",
        "position",
        "level",
        "side",
    }

    missing_fields = (
        required_fields
        - set(locations[0].keys())
    )

    if missing_fields:
        raise ValueError(
            "Location file is missing fields: "
            f"{missing_fields}"
        )

    return locations


# ============================================================
# PRODUCT SELECTION
# ============================================================


def select_products(
    products,
    number_of_products,
):
    """
    Select products for warehouse inventory.

    Products are selected randomly but reproducibly.
    """

    if number_of_products > len(products):
        number_of_products = len(products)

    return random.sample(
        products,
        number_of_products,
    )


# ============================================================
# QUANTITY GENERATORS
# ============================================================


def generate_pallet_quantity():
    """
    Generate inventory quantity for pallet storage.
    """

    return random.randint(
        MIN_PALLET_QUANTITY,
        MAX_PALLET_QUANTITY,
    )


def generate_box_quantity():
    """
    Generate inventory quantity for box storage.
    """

    return random.randint(
        MIN_BOX_QUANTITY,
        MAX_BOX_QUANTITY,
    )


# ============================================================
# CONTAINER TYPE
# ============================================================


def get_container_type(
    storage_type,
):
    """
    Determine the physical container type
    based on storage type.
    """

    if storage_type in PALLET_STORAGE_TYPES:
        return "PALLET"

    if storage_type in BOX_STORAGE_TYPES:
        return "BOX"

    raise ValueError(
        f"Unsupported storage type: "
        f"{storage_type}"
    )


# ============================================================
# INVENTORY RECORD
# ============================================================


def create_inventory_record(
    product,
    location,
    inventory_id,
    container_number,
):
    """
    Create one inventory record.

    One inventory record represents one product
    stored at one warehouse location.
    """

    storage_type = location[
        "storage_type"
    ]

    container_type = get_container_type(
        storage_type
    )

    if container_type == "PALLET":
        quantity = generate_pallet_quantity()

        container_id = (
            f"PALLET-{container_number:06d}"
        )

    else:
        quantity = generate_box_quantity()

        container_id = (
            f"BOX-{container_number:06d}"
        )

    return {
        "inventory_id": (
            f"INV-{inventory_id:08d}"
        ),
        "product_id": product[
            "article_number"
        ],
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
        "container_type": container_type,
        "container_id": container_id,
        "quantity": quantity,
        "unit": "PCS",
        "status": "AVAILABLE",
    }


# ============================================================
# LOCATION COMPATIBILITY
# ============================================================


def get_eligible_locations(
    locations,
):
    """
    Split locations by physical storage type.
    """

    pallet_locations = [
        location
        for location in locations
        if location["storage_type"]
        in PALLET_STORAGE_TYPES
    ]

    box_locations = [
        location
        for location in locations
        if location["storage_type"]
        in BOX_STORAGE_TYPES
    ]

    return (
        pallet_locations,
        box_locations,
    )


# ============================================================
# INVENTORY GENERATION
# ============================================================


def generate_inventory(
    products,
    locations,
):
    """
    Generate warehouse inventory.

    The generator:

        1. selects products
        2. selects occupied locations
        3. creates one inventory record
           per product/location
        4. assigns a physical container
        5. generates a quantity

    The current model intentionally keeps
    inventory generation simple.

    Detailed pallet splitting, box assignment,
    cart picking and picking events will be
    handled by later generators.
    """

    (
        pallet_locations,
        box_locations,
    ) = get_eligible_locations(
        locations
    )

    if not pallet_locations:
        raise ValueError(
            "No pallet storage locations found."
        )

    if not box_locations:
        raise ValueError(
            "No box storage locations found."
        )

    total_locations = len(locations)

    target_locations = int(
        total_locations
        * TARGET_OCCUPANCY
    )

    if target_locations <= 0:
        raise ValueError(
            "Target inventory occupancy "
            "must be greater than zero."
        )

    # --------------------------------------------------------
    # We use separate pools for pallet and box storage.
    # This prevents products from being assigned to an
    # incompatible physical storage type.
    # --------------------------------------------------------

    pallet_target = int(
        target_locations
        * (
            len(pallet_locations)
            / total_locations
        )
    )

    box_target = (
        target_locations
        - pallet_target
    )

    pallet_target = min(
        pallet_target,
        len(pallet_locations),
    )

    box_target = min(
        box_target,
        len(box_locations),
    )

    occupied_pallet_locations = random.sample(
        pallet_locations,
        pallet_target,
    )

    occupied_box_locations = random.sample(
        box_locations,
        box_target,
    )

    occupied_locations = (
        occupied_pallet_locations
        + occupied_box_locations
    )

    # Shuffle so inventory is not grouped
    # by storage type in the output.
    random.shuffle(
        occupied_locations
    )

    selected_products = select_products(
        products,
        len(occupied_locations),
    )

    inventory = []

    for inventory_number, (
        product,
        location,
    ) in enumerate(
        zip(
            selected_products,
            occupied_locations,
        ),
        start=1,
    ):

        record = create_inventory_record(
            product=product,
            location=location,
            inventory_id=inventory_number,
            container_number=inventory_number,
        )

        inventory.append(record)

    return inventory


# ============================================================
# VALIDATION
# ============================================================


def validate_inventory(
    inventory,
    locations,
    products,
):
    """
    Validate generated inventory.

    Checks:

        - inventory IDs are unique
        - product IDs exist
        - location IDs exist
        - one product/location combination
        - storage types are valid
        - container types match storage
        - quantities are positive
    """

    if not inventory:
        raise ValueError(
            "Inventory is empty."
        )

    product_ids = {
        product["article_number"]
        for product in products
    }

    location_lookup = {
        location["location_id"]: location
        for location in locations
    }

    inventory_ids = [
        record["inventory_id"]
        for record in inventory
    ]

    assert len(
        inventory_ids
    ) == len(
        set(inventory_ids)
    ), (
        "Duplicate inventory_id values detected."
    )

    product_location_pairs = set()

    for record in inventory:

        # ----------------------------------------------------
        # Product validation
        # ----------------------------------------------------

        assert record["product_id"] in product_ids, (
            f"Unknown product_id: "
            f"{record['product_id']}"
        )

        # ----------------------------------------------------
        # Location validation
        # ----------------------------------------------------

        location_id = record[
            "location_id"
        ]

        assert location_id in location_lookup, (
            f"Unknown location_id: "
            f"{location_id}"
        )

        location = location_lookup[
            location_id
        ]

        # ----------------------------------------------------
        # Product / location uniqueness
        # ----------------------------------------------------

        pair = (
            record["product_id"],
            record["location_id"],
        )

        assert pair not in product_location_pairs, (
            "Duplicate product/location "
            f"combination: {pair}"
        )

        product_location_pairs.add(
            pair
        )

        # ----------------------------------------------------
        # Storage type
        # ----------------------------------------------------

        assert (
            record["storage_type"]
            == location["storage_type"]
        ), (
            f"Storage type mismatch for "
            f"{record['inventory_id']}"
        )

        # ----------------------------------------------------
        # Container type
        # ----------------------------------------------------

        expected_container_type = (
            get_container_type(
                location["storage_type"]
            )
        )

        assert (
            record["container_type"]
            == expected_container_type
        ), (
            f"Container type mismatch for "
            f"{record['inventory_id']}"
        )

        # ----------------------------------------------------
        # Quantity
        # ----------------------------------------------------

        assert record["quantity"] > 0, (
            f"Invalid quantity in "
            f"{record['inventory_id']}"
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        assert record["status"] == "AVAILABLE", (
            f"Invalid inventory status in "
            f"{record['inventory_id']}"
        )

    print(
        "Inventory validation passed."
    )


# ============================================================
# SUMMARY
# ============================================================


def print_inventory_summary(
    inventory,
):
    """
    Print inventory summary.
    """

    total_records = len(
        inventory
    )

    total_quantity = sum(
        int(record["quantity"])
        for record in inventory
    )

    pallet_records = sum(
        1
        for record in inventory
        if record["container_type"]
        == "PALLET"
    )

    box_records = sum(
        1
        for record in inventory
        if record["container_type"]
        == "BOX"
    )

    print()
    print("Warehouse Inventory Summary")
    print("===========================")

    print(
        f"Inventory records: {total_records:,}"
    )

    print(
        f"Total quantity:    {total_quantity:,}"
    )

    print(
        f"Pallet inventory:  {pallet_records:,}"
    )

    print(
        f"Box inventory:     {box_records:,}"
    )


# ============================================================
# EXPORT
# ============================================================


def export_inventory(
    inventory,
    output_file=OUTPUT_FILE,
):
    """
    Export inventory to CSV.
    """

    if not inventory:
        raise ValueError(
            "No inventory available for export."
        )

    output_file.parent.mkdir(
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
        "container_type",
        "container_id",
        "quantity",
        "unit",
        "status",
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
            inventory
        )

    print()
    print(
        "Inventory export complete:"
    )

    print(
        output_file
    )


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
        f"Products loaded: "
        f"{len(products):,}"
    )

    print()
    print("Loading locations...")

    locations = load_locations()

    print(
        f"Locations loaded: "
        f"{len(locations):,}"
    )

    print()
    print("Generating inventory...")

    inventory = generate_inventory(
        products=products,
        locations=locations,
    )

    print(
        f"Inventory records generated: "
        f"{len(inventory):,}"
    )

    print()
    print("Validating inventory...")

    validate_inventory(
        inventory=inventory,
        locations=locations,
        products=products,
    )

    print_inventory_summary(
        inventory
    )

    export_inventory(
        inventory
    )


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================


if __name__ == "__main__":
    main()