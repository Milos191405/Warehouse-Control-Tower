from pathlib import Path
import random


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"


# ============================================================
# CONTAINER TYPES
# ============================================================

CONTAINER_TYPES = {
    "BOX": "Box",
    "CART": "Picking Cart",
    "PALLET": "Pallet",
}


# ============================================================
# DIMENSION / VOLUME HELPERS
# ============================================================

def calculate_volume_m3(length_mm, width_mm, height_mm):
    """Calculate geometric volume in cubic meters from millimeters."""
    return (length_mm * width_mm * height_mm) / 1_000_000_000


# ============================================================
# BOX TYPES
# ============================================================

BOX_TYPES = {
    201: {
        "box_code": 201,
        "box_name": "Small Box",
        "length_mm": 300,
        "width_mm": 190,
        "height_mm": 170,
        "volume_m3": calculate_volume_m3(300, 190, 170),
    },
    202: {
        "box_code": 202,
        "box_name": "Medium Box",
        "length_mm": 400,
        "width_mm": 300,
        "height_mm": 235,
        "volume_m3": calculate_volume_m3(400, 300, 235),
    },
    203: {
        "box_code": 203,
        "box_name": "Large Box",
        "length_mm": 600,
        "width_mm": 400,
        "height_mm": 235,
        "volume_m3": calculate_volume_m3(600, 400, 235),
    },
}


# ============================================================
# PALLET TYPES
# ============================================================

PALLET_TYPES = {
    "PALLET_EUR": {
        "pallet_code": "PALLET_EUR",
        "pallet_name": "Euro Pallet",
        "length_mm": 1200,
        "width_mm": 800,
        "height_mm": 144,
        "volume_m3": calculate_volume_m3(1200, 800, 144),
        "available_quantity": 20,
    },
    "PALLET_HALF": {
        "pallet_code": "PALLET_HALF",
        "pallet_name": "Half Pallet",
        "length_mm": 800,
        "width_mm": 600,
        "height_mm": 144,
        "volume_m3": calculate_volume_m3(800, 600, 144),
        "available_quantity": 40,
    },
    "PALLET_QUARTER": {
        "pallet_code": "PALLET_QUARTER",
        "pallet_name": "Quarter Pallet",
        "length_mm": 600,
        "width_mm": 400,
        "height_mm": 140,
        "volume_m3": calculate_volume_m3(600, 400, 140),
        "available_quantity": 50,
    },
}


# ============================================================
# PALLET LOADING RULES
# ============================================================
# These rules are currently defined only for BOX_202, based on
# the operational capacities supplied:
#   EUR:     8 boxes/layer, max 4 layers for air/sea, 5 for road
#   HALF:    4 boxes/layer, max 4 layers for air/sea, 5 for road
#   QUARTER: 2 boxes/layer, max 3 layers; air/sea not permitted
#
# A max layer count of 0 means that the transport combination
# is not allowed.

PALLET_LOADING_RULES = {
    "BOX_202": {
        "PALLET_EUR": {
            "boxes_per_layer": 8,
            "max_layers_road": 5,
            "max_layers_air": 4,
            "max_layers_sea": 4,
        },
        "PALLET_HALF": {
            "boxes_per_layer": 4,
            "max_layers_road": 5,
            "max_layers_air": 4,
            "max_layers_sea": 4,
        },
        "PALLET_QUARTER": {
            "boxes_per_layer": 2,
            "max_layers_road": 3,
            "max_layers_air": 0,
            "max_layers_sea": 0,
        },
    },
}


# ============================================================
# CART CONFIGURATION
# ============================================================

CART_POSITION_COUNT = 9


# ============================================================
# CONTAINER ID GENERATORS
# ============================================================

def create_container_id(container_type, number):
    """
    Create a unique container identifier.

    Examples:
        BOX-000001
        CART-000001
        PALLET-000001
    """
    prefixes = {
        "BOX": "BOX",
        "CART": "CART",
        "PALLET": "PALLET",
    }

    if container_type not in prefixes:
        raise ValueError(f"Unsupported container type: {container_type}")

    return f"{prefixes[container_type]}-{number:06d}"


# ============================================================
# BOX GENERATOR
# ============================================================

def generate_boxes(count, start_number=1, box_codes=None):
    """
    Generate box master records with physical dimensions.

    Args:
        count: Number of individual box records to generate.
        start_number: Starting sequence number.
        box_codes: Optional iterable of box codes to use. When omitted,
                   box types are selected randomly.
    """
    boxes = []
    available_codes = list(box_codes) if box_codes is not None else list(BOX_TYPES)

    if not available_codes:
        raise ValueError("At least one box code must be provided.")

    unknown_codes = set(available_codes) - set(BOX_TYPES)
    if unknown_codes:
        raise ValueError(f"Unknown box codes: {sorted(unknown_codes)}")

    for number in range(start_number, start_number + count):
        box_code = random.choice(available_codes)
        config = BOX_TYPES[box_code]

        boxes.append({
            "container_id": create_container_id("BOX", number),
            "container_type": "BOX",
            "barcode": f"BOX-{number:06d}",
            "box_code": config["box_code"],
            "box_name": config["box_name"],
            "length_mm": config["length_mm"],
            "width_mm": config["width_mm"],
            "height_mm": config["height_mm"],
            "volume_m3": config["volume_m3"],
            "status": "AVAILABLE",
        })

    return boxes


# ============================================================
# CART GENERATOR
# ============================================================

def generate_carts(count, start_number=1):
    """Generate picking carts, each with 9 picking positions."""
    carts = []

    for number in range(start_number, start_number + count):
        cart_id = create_container_id("CART", number)

        carts.append({
            "cart_id": cart_id,
            "container_type": "CART",
            "barcode": cart_id,
            "position_count": CART_POSITION_COUNT,
            "status": "AVAILABLE",
        })

    return carts


# ============================================================
# PALLET GENERATOR
# ============================================================

def generate_pallets(count, start_number=1, pallet_codes=None):
    """
    Generate pallet records with physical dimensions.

    `available_quantity` in PALLET_TYPES is configuration/master-data
    information; it is not decremented by this synthetic record generator.
    """
    pallets = []
    available_codes = (
        list(pallet_codes)
        if pallet_codes is not None
        else list(PALLET_TYPES)
    )

    if not available_codes:
        raise ValueError("At least one pallet code must be provided.")

    unknown_codes = set(available_codes) - set(PALLET_TYPES)
    if unknown_codes:
        raise ValueError(f"Unknown pallet codes: {sorted(unknown_codes)}")

    for number in range(start_number, start_number + count):
        pallet_code = random.choice(available_codes)
        config = PALLET_TYPES[pallet_code]
        pallet_id = create_container_id("PALLET", number)

        pallets.append({
            "container_id": pallet_id,
            "container_type": "PALLET",
            "barcode": pallet_id,
            "pallet_code": config["pallet_code"],
            "pallet_name": config["pallet_name"],
            "length_mm": config["length_mm"],
            "width_mm": config["width_mm"],
            "height_mm": config["height_mm"],
            "volume_m3": config["volume_m3"],
            "status": "AVAILABLE",
        })

    return pallets


# ============================================================
# CART POSITIONS
# ============================================================

def generate_cart_positions(cart_id):
    """
    Generate the 9 physical positions available on a picking cart.
    Positions start at 1 and end at 9.
    """
    return [
        {
            "cart_id": cart_id,
            "position_number": position_number,
            "qr_code": f"{cart_id}-POS-{position_number:02d}",
            "status": "EMPTY",
            "container_id": None,
        }
        for position_number in range(1, CART_POSITION_COUNT + 1)
    ]


# ============================================================
# VALIDATION
# ============================================================

def validate_box_types():
    """Validate box codes, dimensions, and calculated volumes."""
    expected_codes = {201, 202, 203}
    actual_codes = set(BOX_TYPES)

    if actual_codes != expected_codes:
        raise ValueError(
            f"Unexpected box type configuration: {sorted(actual_codes)}"
        )

    for code, box in BOX_TYPES.items():
        for dimension in ("length_mm", "width_mm", "height_mm"):
            if not isinstance(box[dimension], (int, float)) or box[dimension] <= 0:
                raise ValueError(f"Invalid {dimension} for BOX_{code}")

        expected_volume = calculate_volume_m3(
            box["length_mm"], box["width_mm"], box["height_mm"]
        )
        if abs(box["volume_m3"] - expected_volume) > 1e-12:
            raise ValueError(f"Incorrect volume for BOX_{code}")

    print("Box type validation passed.")


def validate_pallet_types():
    """Validate pallet codes, dimensions, quantities, and volumes."""
    expected_codes = {"PALLET_EUR", "PALLET_HALF", "PALLET_QUARTER"}

    if set(PALLET_TYPES) != expected_codes:
        raise ValueError("Unexpected pallet type configuration.")

    for code, pallet in PALLET_TYPES.items():
        for dimension in ("length_mm", "width_mm", "height_mm"):
            if not isinstance(pallet[dimension], (int, float)) or pallet[dimension] <= 0:
                raise ValueError(f"Invalid {dimension} for {code}")

        if pallet["available_quantity"] < 0:
            raise ValueError(f"Invalid available quantity for {code}")

        expected_volume = calculate_volume_m3(
            pallet["length_mm"], pallet["width_mm"], pallet["height_mm"]
        )
        if abs(pallet["volume_m3"] - expected_volume) > 1e-12:
            raise ValueError(f"Incorrect volume for {code}")

    print("Pallet type validation passed.")


def validate_pallet_loading_rules():
    """Validate that configured loading rules reference known pallet types."""
    for box_code, pallet_rules in PALLET_LOADING_RULES.items():
        if not box_code.startswith("BOX_"):
            raise ValueError(f"Invalid box code in pallet rules: {box_code}")

        for pallet_code, rules in pallet_rules.items():
            if pallet_code not in PALLET_TYPES:
                raise ValueError(f"Unknown pallet type in loading rules: {pallet_code}")

            if rules["boxes_per_layer"] <= 0:
                raise ValueError(f"Invalid boxes_per_layer for {box_code}/{pallet_code}")

            for transport in ("road", "air", "sea"):
                key = f"max_layers_{transport}"
                if key not in rules or rules[key] < 0:
                    raise ValueError(f"Invalid {key} for {box_code}/{pallet_code}")

    print("Pallet loading rule validation passed.")


def validate_cart_positions(positions):
    """Validate cart position numbering."""
    if len(positions) != CART_POSITION_COUNT:
        raise ValueError("Invalid cart position count.")

    position_numbers = [position["position_number"] for position in positions]
    expected = list(range(1, CART_POSITION_COUNT + 1))

    if position_numbers != expected:
        raise ValueError("Cart positions must be numbered 1-9.")

    print("Cart position validation passed.")


# ============================================================
# SUMMARY
# ============================================================

def print_summary():
    """Print configured container, box, and pallet master data."""
    print()
    print("Warehouse Container Configuration")
    print("=================================")
    print()

    print("Container types:")
    for code, name in CONTAINER_TYPES.items():
        print(f"  {code:7} | {name}")

    print()
    print("Box types:")
    for box in BOX_TYPES.values():
        print(
            f"  BOX_{box['box_code']} | {box['box_name']} | "
            f"{box['length_mm']} x {box['width_mm']} x "
            f"{box['height_mm']} mm | "
            f"Volume: {box['volume_m3']:.5f} m3"
        )

    print()
    print("Pallet types:")
    for pallet in PALLET_TYPES.values():
        print(
            f"  {pallet['pallet_code']} | {pallet['pallet_name']} | "
            f"{pallet['length_mm']} x {pallet['width_mm']} x "
            f"{pallet['height_mm']} mm | "
            f"Volume: {pallet['volume_m3']:.5f} m3 | "
            f"Available: {pallet['available_quantity']}"
        )

    print()
    print(f"Picking cart positions: {CART_POSITION_COUNT}")

    print()
    print("Pallet loading rules:")
    for box_code, pallet_rules in PALLET_LOADING_RULES.items():
        for pallet_code, rules in pallet_rules.items():
            print(
                f"  {box_code} on {pallet_code}: "
                f"{rules['boxes_per_layer']} boxes/layer; "
                f"max layers road={rules['max_layers_road']}, "
                f"air={rules['max_layers_air']}, "
                f"sea={rules['max_layers_sea']}"
            )


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("Warehouse Container Generator")
    print("==============================")

    validate_box_types()
    validate_pallet_types()
    validate_pallet_loading_rules()
    print_summary()

    # Example cart and positions
    carts = generate_carts(1)
    cart_id = carts[0]["cart_id"]
    positions = generate_cart_positions(cart_id)
    validate_cart_positions(positions)

    print()
    print("Example cart:")
    print(carts[0])

    print()
    print("Cart positions:")
    for position in positions:
        print(position)

    # Example box and pallet records, including dimensions
    print()
    print("Example box:")
    print(generate_boxes(1)[0])

    print()
    print("Example pallet:")
    print(generate_pallets(1)[0])


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
