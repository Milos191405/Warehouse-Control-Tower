from pathlib import Path
import csv


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_FILE = OUTPUT_DIR / "locations.csv"


# ============================================================
# LOCATION MODEL
# ============================================================

"""
Warehouse location generator.

The location model separates:

    storage_type
        What is physically stored at the location.

    picking_method
        How the product can normally be picked from
        that storage area.

Detailed picking actions such as:

    FULL_PALLET
    PARTIAL_PALLET
    CART_BOX

will be modeled later in picking.py.

Location ID format:

    H1-001-001-01-1

    H1  = Hall
    001 = Zone
    001 = Position
    01  = Level
    1   = Side

Side:

    1 = Left
    2 = Right


Warehouse totals:

    Hall 1 = 18,500
    Hall 2 =  4,240
    Hall 3 =  1,440

    Total = 24,180
"""


# ============================================================
# HALL 1
# ============================================================


def generate_hall_1_high_rack():
    """
    Hall 1 - Zone 1 - High Rack

    Physical storage:
        Pallets

    Picking:
        Forklift / stapler

    Structure:
        - 10 rows
        - 26 positions per row
        - 4 levels
        - 2 sides

    Total:
        10 * 26 * 4 * 2 = 2,080
    """

    locations = []

    zone_nr = 1
    total_rows = 10
    positions_per_row = 26

    position = 1

    for row in range(1, total_rows + 1):

        for row_position in range(
            1,
            positions_per_row + 1,
        ):

            for level in range(1, 5):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H1-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 1,
                        "zone_nr": zone_nr,
                        "storage_type": "PALLET_STORAGE",
                        "picking_method": "FORKLIFT",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

            position += 1

    return locations


def generate_hall_1_low_rack():
    """
    Hall 1 - Zone 2 - Low Rack

    Physical storage:
        Pallets

    Picking:
        Picking cart

    Structure:
        - 10 rows
        - 26 positions per row
        - 2 levels
        - 2 sides

    Total:
        10 * 26 * 2 * 2 = 1,040
    """

    locations = []

    zone_nr = 2
    total_rows = 10
    positions_per_row = 26

    position = 1

    for row in range(1, total_rows + 1):

        for row_position in range(
            1,
            positions_per_row + 1,
        ):

            for level in range(1, 3):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H1-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 1,
                        "zone_nr": zone_nr,
                        "storage_type": "PALLET_STORAGE",
                        "picking_method": "PICKING_CART",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

            position += 1

    return locations


def generate_hall_1_vertical_lifts():
    """
    Hall 1 - Zones 3 and 4 - Vertical Lifts

    Physical storage:
        Boxes

    Picking:
        Vertical lift / box picking

    Each lift:
        - 115 positions
        - levels 4 through 26
        - 2 sides

    Per lift:
        115 * 23 * 2 = 5,290

    Total:
        10,580
    """

    locations = []

    vertical_lift_zones = [3, 4]

    for zone_nr in vertical_lift_zones:

        for position in range(1, 116):

            for level in range(4, 27):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H1-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 1,
                        "zone_nr": zone_nr,
                        "storage_type": "BOX_STORAGE",
                        "picking_method": "VERTICAL_LIFT",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

    return locations


def generate_hall_1_picking_cart_areas():
    """
    Hall 1 - Zones 5, 6 and 7 - Picking Cart Areas

    Physical storage:
        Boxes

    Picking:
        Picking cart

    Zone 5:
        125 positions
        8 levels
        2 sides
        = 2,000

    Zone 6:
        115 positions
        8 levels
        2 sides
        = 1,840

    Zone 7:
        60 positions
        8 levels
        2 sides
        = 960

    Total:
        4,800
    """

    locations = []

    picking_cart_zones = {
        5: 125,
        6: 115,
        7: 60,
    }

    for zone_nr, max_position in picking_cart_zones.items():

        for position in range(
            1,
            max_position + 1,
        ):

            for level in range(1, 9):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H1-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 1,
                        "zone_nr": zone_nr,
                        "storage_type": "BOX_STORAGE",
                        "picking_method": "PICKING_CART",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

    return locations


def generate_hall_1_locations():
    """
    Generate all Hall 1 locations.

    Total:
        18,500
    """

    locations = []

    locations.extend(
        generate_hall_1_high_rack()
    )

    locations.extend(
        generate_hall_1_low_rack()
    )

    locations.extend(
        generate_hall_1_vertical_lifts()
    )

    locations.extend(
        generate_hall_1_picking_cart_areas()
    )

    return locations


# ============================================================
# HALL 2
# ============================================================


def generate_hall_2_vertical_lift():
    """
    Hall 2 - Zone 8 - Vertical Lift

    Physical storage:
        Boxes

    Picking:
        Vertical lift / box picking

    Structure:
        - 50 positions
        - 28 levels
        - 2 sides

    Total:
        50 * 28 * 2 = 2,800
    """

    locations = []

    zone_nr = 8

    for position in range(1, 51):

        for level in range(1, 29):

            for side in range(1, 3):

                location = {
                    "location_id": (
                        f"H2-{zone_nr:03d}-"
                        f"{position:03d}-"
                        f"{level:02d}-"
                        f"{side}"
                    ),
                    "hall_id": 2,
                    "zone_nr": zone_nr,
                    "storage_type": "BOX_STORAGE",
                    "picking_method": "VERTICAL_LIFT",
                    "position": position,
                    "level": level,
                    "side": side,
                }

                locations.append(location)

    return locations


def generate_hall_2_high_rack():
    """
    Hall 2 - Zone 9 - High Rack

    Physical storage:
        Pallets

    Picking:
        Forklift / stapler

    Structure:
        - 5 rows
        - 24 positions per row
        - 4 levels
        - 2 sides

    Total:
        5 * 24 * 4 * 2 = 960
    """

    locations = []

    zone_nr = 9
    total_rows = 5
    positions_per_row = 24

    position = 1

    for row in range(1, total_rows + 1):

        for row_position in range(
            1,
            positions_per_row + 1,
        ):

            for level in range(1, 5):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H2-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 2,
                        "zone_nr": zone_nr,
                        "storage_type": "PALLET_STORAGE",
                        "picking_method": "FORKLIFT",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

            position += 1

    return locations


def generate_hall_2_low_rack():
    """
    Hall 2 - Zone 10 - Low Rack

    Physical storage:
        Pallets

    Picking:
        Picking cart

    Structure:
        - 5 rows
        - 24 positions per row
        - 2 levels
        - 2 sides

    Total:
        5 * 24 * 2 * 2 = 480
    """

    locations = []

    zone_nr = 10
    total_rows = 5
    positions_per_row = 24

    position = 1

    for row in range(1, total_rows + 1):

        for row_position in range(
            1,
            positions_per_row + 1,
        ):

            for level in range(1, 3):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H2-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 2,
                        "zone_nr": zone_nr,
                        "storage_type": "PALLET_STORAGE",
                        "picking_method": "PICKING_CART",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

            position += 1

    return locations


def generate_hall_2_locations():
    """
    Generate all Hall 2 locations.

    Total:
        4,240
    """

    locations = []

    locations.extend(
        generate_hall_2_vertical_lift()
    )

    locations.extend(
        generate_hall_2_high_rack()
    )

    locations.extend(
        generate_hall_2_low_rack()
    )

    return locations


# ============================================================
# HALL 3
# ============================================================


def generate_hall_3_low_rack():
    """
    Hall 3 - Zone 11 - Low Rack / Cart Picking

    Physical storage:
        Pallets

    Picking:
        Picking cart

    Structure:
        - 5 rows
        - 24 positions per row
        - 2 levels
        - 2 sides

    Total:
        5 * 24 * 2 * 2 = 480
    """

    locations = []

    zone_nr = 11
    total_rows = 5
    positions_per_row = 24

    position = 1

    for row in range(1, total_rows + 1):

        for row_position in range(
            1,
            positions_per_row + 1,
        ):

            for level in range(1, 3):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H3-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 3,
                        "zone_nr": zone_nr,
                        "storage_type": "PALLET_STORAGE",
                        "picking_method": "PICKING_CART",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

            position += 1

    return locations


def generate_hall_3_stapler_picking():
    """
    Hall 3 - Zone 12 - Stapler / High Picking

    Physical storage:
        Pallets

    Picking:
        Stapler

    Possible detailed picking actions will be modeled
    later in picking.py:

        FULL_PALLET
        PARTIAL_PALLET
        CART_BOX

    Structure:
        - 5 rows
        - 24 positions per row
        - 4 levels
        - 2 sides

    Total:
        5 * 24 * 4 * 2 = 960
    """

    locations = []

    zone_nr = 12
    total_rows = 5
    positions_per_row = 24

    position = 1

    for row in range(1, total_rows + 1):

        for row_position in range(
            1,
            positions_per_row + 1,
        ):

            for level in range(1, 5):

                for side in range(1, 3):

                    location = {
                        "location_id": (
                            f"H3-{zone_nr:03d}-"
                            f"{position:03d}-"
                            f"{level:02d}-"
                            f"{side}"
                        ),
                        "hall_id": 3,
                        "zone_nr": zone_nr,
                        "storage_type": "PALLET_STORAGE",
                        "picking_method": "STAPLER",
                        "position": position,
                        "level": level,
                        "side": side,
                    }

                    locations.append(location)

            position += 1

    return locations


def generate_hall_3_locations():
    """
    Generate all Hall 3 locations.

    Total:
        1,440
    """

    locations = []

    locations.extend(
        generate_hall_3_low_rack()
    )

    locations.extend(
        generate_hall_3_stapler_picking()
    )

    return locations


# ============================================================
# ALL LOCATIONS
# ============================================================


def generate_all_locations():
    """
    Generate all warehouse storage locations.

    Hall 1 = 18,500
    Hall 2 =  4,240
    Hall 3 =  1,440

    Total = 24,180
    """

    locations = []

    locations.extend(
        generate_hall_1_locations()
    )

    locations.extend(
        generate_hall_2_locations()
    )

    locations.extend(
        generate_hall_3_locations()
    )

    return locations


# ============================================================
# CSV EXPORT
# ============================================================


def export_locations(
    locations,
    output_file=OUTPUT_FILE,
):
    """
    Export generated locations to CSV.
    """

    if not locations:
        raise ValueError(
            "No locations available for export."
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "location_id",
        "hall_id",
        "zone_nr",
        "storage_type",
        "picking_method",
        "position",
        "level",
        "side",
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
        writer.writerows(locations)

    print()
    print(
        f"Location export complete:"
    )
    print(output_file)


# ============================================================
# VALIDATION
# ============================================================


def validate_locations(locations):
    """
    Validate generated warehouse locations.

    Checks:
        - total number of locations
        - unique location IDs
        - correct hall distribution
        - correct zone distribution
        - valid side values
        - valid storage types
        - valid picking methods
    """

    expected_total = 24_180

    expected_hall_counts = {
        1: 18_500,
        2: 4_240,
        3: 1_440,
    }

    expected_zone_counts = {
        1: 2_080,
        2: 1_040,
        3: 5_290,
        4: 5_290,
        5: 2_000,
        6: 1_840,
        7: 960,
        8: 2_800,
        9: 960,
        10: 480,
        11: 480,
        12: 960,
    }

    valid_storage_types = {
        "PALLET_STORAGE",
        "BOX_STORAGE",
    }

    valid_picking_methods = {
        "FORKLIFT",
        "PICKING_CART",
        "VERTICAL_LIFT",
        "STAPLER",
    }

    # --------------------------------------------------------
    # Total count
    # --------------------------------------------------------

    actual_total = len(locations)

    assert actual_total == expected_total, (
        f"Expected {expected_total} locations, "
        f"got {actual_total}"
    )

    # --------------------------------------------------------
    # Unique location IDs
    # --------------------------------------------------------

    location_ids = [
        location["location_id"]
        for location in locations
    ]

    assert len(location_ids) == len(
        set(location_ids)
    ), (
        "Duplicate location_id values detected."
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

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

    for location in locations:

        missing_fields = (
            required_fields
            - set(location.keys())
        )

        assert not missing_fields, (
            f"Missing fields in "
            f"{location.get('location_id')}: "
            f"{missing_fields}"
        )

    # --------------------------------------------------------
    # Hall counts
    # --------------------------------------------------------

    for hall_id, expected_count in (
        expected_hall_counts.items()
    ):

        actual_count = sum(
            1
            for location in locations
            if location["hall_id"] == hall_id
        )

        assert actual_count == expected_count, (
            f"Hall {hall_id}: "
            f"expected {expected_count}, "
            f"got {actual_count}"
        )

    # --------------------------------------------------------
    # Zone counts
    # --------------------------------------------------------

    for zone_nr, expected_count in (
        expected_zone_counts.items()
    ):

        actual_count = sum(
            1
            for location in locations
            if location["zone_nr"] == zone_nr
        )

        assert actual_count == expected_count, (
            f"Zone {zone_nr}: "
            f"expected {expected_count}, "
            f"got {actual_count}"
        )

    # --------------------------------------------------------
    # Storage types
    # --------------------------------------------------------

    for location in locations:

        assert (
            location["storage_type"]
            in valid_storage_types
        ), (
            f"Invalid storage_type "
            f"'{location['storage_type']}' "
            f"in {location['location_id']}"
        )

    # --------------------------------------------------------
    # Picking methods
    # --------------------------------------------------------

    for location in locations:

        assert (
            location["picking_method"]
            in valid_picking_methods
        ), (
            f"Invalid picking_method "
            f"'{location['picking_method']}' "
            f"in {location['location_id']}"
        )

    # --------------------------------------------------------
    # Side validation
    # --------------------------------------------------------

    for location in locations:

        assert location["side"] in (1, 2), (
            f"Invalid side in "
            f"{location['location_id']}"
        )

    # --------------------------------------------------------
    # Hall validation
    # --------------------------------------------------------

    for location in locations:

        hall_prefix = (
            f"H{location['hall_id']}-"
        )

        assert location["location_id"].startswith(
            hall_prefix
        ), (
            f"Hall mismatch in "
            f"{location['location_id']}"
        )

    print(
        "Location validation passed."
    )


# ============================================================
# ZONE SUMMARY
# ============================================================


def print_zone_summary(locations):
    """
    Print a compact summary of all warehouse zones.

    Shows:
        - Hall
        - Zone number
        - Storage type
        - Picking method
        - Number of locations
    """

    zone_summary = {}

    for location in locations:

        key = (
            location["hall_id"],
            location["zone_nr"],
        )

        if key not in zone_summary:

            zone_summary[key] = {
                "storage_type": (
                    location["storage_type"]
                ),
                "picking_method": (
                    location["picking_method"]
                ),
                "locations": 0,
            }

        zone_summary[key]["locations"] += 1

    print()
    print("Warehouse Zone Summary")
    print("======================")

    current_hall = None

    for (hall_id, zone_nr), data in (
        zone_summary.items()
    ):

        if hall_id != current_hall:

            print()
            print(f"Hall {hall_id}")
            print("-" * 70)

            current_hall = hall_id

        print(
            f"Zone {zone_nr:02d} | "
            f"{data['storage_type']:<18} | "
            f"{data['picking_method']:<15} | "
            f"{data['locations']:>5}"
        )


# ============================================================
# MAIN
# ============================================================


if __name__ == "__main__":

    locations = generate_all_locations()

    hall_1 = generate_hall_1_locations()
    hall_2 = generate_hall_2_locations()
    hall_3 = generate_hall_3_locations()

    print()
    print("Warehouse Location Generator")
    print("=============================")

    print()
    print("Hall 1:")
    print(f"  Locations: {len(hall_1)}")

    print()
    print("Hall 2:")
    print(f"  Locations: {len(hall_2)}")

    print()
    print("Hall 3:")
    print(f"  Locations: {len(hall_3)}")

    print()
    print("-----------------------------")
    print(
        f"Total locations: {len(locations)}"
    )

    print()
    print("Validation:")

    validate_locations(
        locations
    )

    print_zone_summary(
        locations
    )

    export_locations(
        locations
    )

    print()
    print("First 5 locations:")

    for location in locations[:5]:
        print(location)

    print()
    print("Last 5 locations:")

    for location in locations[-5:]:
        print(location)