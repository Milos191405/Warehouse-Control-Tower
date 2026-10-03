from pathlib import Path
import random


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


# ============================================================
# CONTAINER TYPES
# ============================================================

CONTAINER_TYPES = {
    "BOX": "Box",
    "CART": "Picking Cart",
    "PALLET": "Pallet",
}


# ============================================================
# BOX TYPES
# ============================================================

BOX_TYPES = {
    201: {
        "box_code": 201,
        "box_name": "Small Box",
        "length_mm": None,
        "width_mm": None,
        "height_mm": None,
        "volume_m3": None,
    },
    202: {
        "box_code": 202,
        "box_name": "Medium Box",
        "length_mm": None,
        "width_mm": None,
        "height_mm": None,
        "volume_m3": None,
    },
    203: {
        "box_code": 203,
        "box_name": "Large Box",
        "length_mm": None,
        "width_mm": None,
        "height_mm": None,
        "volume_m3": None,
    },
}


# ============================================================
# CART CONFIGURATION
# ============================================================

CART_POSITION_COUNT = 9


# ============================================================
# CONTAINER ID GENERATORS
# ============================================================

def create_container_id(
    container_type,
    number,
):
    """
    Create a unique container identifier.

    Examples:
        BOX-000001
        CART-000001
        PALLET-000001
    """

    prefix = {
        "BOX": "BOX",
        "CART": "CART",
        "PALLET": "PALLET",
    }[container_type]

    return f"{prefix}-{number:06d}"


# ============================================================
# BOX GENERATOR
# ============================================================

def generate_boxes(
    count,
    start_number=1,
):
    """
    Generate box master records.

    Box dimensions are intentionally left empty
    until physically verified.
    """

    boxes = []

    for number in range(
        start_number,
        start_number + count,
    ):
        box = {
            "container_id": create_container_id(
                "BOX",
                number,
            ),
            "container_type": "BOX",
            "barcode": f"BOX-{number:06d}",
            "box_code": random.choice(
                list(BOX_TYPES.keys())
            ),
            "status": "AVAILABLE",
        }

        boxes.append(box)

    return boxes


# ============================================================
# CART GENERATOR
# ============================================================

def generate_carts(
    count,
    start_number=1,
):
    """
    Generate picking carts.

    Each cart has 9 picking positions.
    """

    carts = []

    for number in range(
        start_number,
        start_number + count,
    ):
        cart_id = create_container_id(
            "CART",
            number,
        )

        cart = {
            "cart_id": cart_id,
            "container_type": "CART",
            "barcode": cart_id,
            "position_count": CART_POSITION_COUNT,
            "status": "AVAILABLE",
        }

        carts.append(cart)

    return carts


# ============================================================
# PALLET GENERATOR
# ============================================================

def generate_pallets(
    count,
    start_number=1,
):
    """
    Generate pallet records.
    """

    pallets = []

    for number in range(
        start_number,
        start_number + count,
    ):
        pallet_id = create_container_id(
            "PALLET",
            number,
        )

        pallet = {
            "container_id": pallet_id,
            "container_type": "PALLET",
            "barcode": pallet_id,
            "status": "AVAILABLE",
        }

        pallets.append(pallet)

    return pallets


# ============================================================
# CART POSITIONS
# ============================================================

def generate_cart_positions(
    cart_id,
):
    """
    Generate the 9 physical positions
    available on a picking cart.

    Positions start at 1 and end at 9.
    """

    positions = []

    for position_number in range(
        1,
        CART_POSITION_COUNT + 1,
    ):
        position = {
            "cart_id": cart_id,
            "position_number": position_number,
            "qr_code": (
                f"{cart_id}-POS-{position_number:02d}"
            ),
            "status": "EMPTY",
            "container_id": None,
        }

        positions.append(position)

    return positions


# ============================================================
# VALIDATION
# ============================================================

def validate_box_types():
    """
    Validate configured box types.
    """

    expected_codes = {
        201,
        202,
        203,
    }

    actual_codes = set(
        BOX_TYPES.keys()
    )

    if actual_codes != expected_codes:
        raise ValueError(
            "Unexpected box type configuration."
        )

    print(
        "Box type validation passed."
    )


def validate_cart_positions(
    positions,
):
    """
    Validate cart position numbering.
    """

    if len(positions) != CART_POSITION_COUNT:
        raise ValueError(
            "Invalid cart position count."
        )

    position_numbers = [
        position["position_number"]
        for position in positions
    ]

    expected = list(
        range(
            1,
            CART_POSITION_COUNT + 1,
        )
    )

    if position_numbers != expected:
        raise ValueError(
            "Cart positions must be numbered 1-9."
        )

    print(
        "Cart position validation passed."
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary():
    """
    Print current container configuration.
    """

    print()
    print("Warehouse Container Configuration")
    print("=================================")
    print()

    print("Container types:")

    for code, name in CONTAINER_TYPES.items():
        print(
            f"  {code:7} | {name}"
        )

    print()

    print("Box types:")

    for box in BOX_TYPES.values():
        print(
            f"  {box['box_code']} | "
            f"{box['box_name']} | "
            f"dimensions pending verification"
        )

    print()

    print(
        f"Picking cart positions: "
        f"{CART_POSITION_COUNT}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("Warehouse Container Generator")
    print("=============================")

    validate_box_types()

    print_summary()

    # Example cart
    carts = generate_carts(1)

    cart_id = carts[0]["cart_id"]

    positions = generate_cart_positions(
        cart_id
    )

    validate_cart_positions(
        positions
    )

    print()
    print("Example cart:")
    print(carts[0])

    print()
    print("Cart positions:")

    for position in positions:
        print(position)


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()