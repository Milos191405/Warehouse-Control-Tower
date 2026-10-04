"""
Warehouse Control Tower - Shipping Generator

Generates one shipment record per packed order.

Flow:
    order -> picking -> packing -> shipping -> delivery

Shipping is based on the completed packing timestamp and the
requested delivery deadline from orders.csv.

Shipping method rules:
    SMALL_PACKAGE   -> PARCEL
    LARGE_PACKAGE   -> FREIGHT
    PALLET_SHIPMENT -> PALLET_FREIGHT

Timeline:
    packing completed
        -> dispatch preparation 10-45 min
        -> shipped/dispatch
        -> transit
        -> delivered

All operational shipping data is synthetic.
"""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ORDERS_FILE = PROCESSED_DIR / "orders.csv"
PACKING_FILE = PROCESSED_DIR / "packing.csv"
SHIPPING_FILE = PROCESSED_DIR / "shipping.csv"

RANDOM_SEED = 42

PREPARATION_MINUTES = (10, 45)

# Synthetic transit windows.
PARCEL_TRANSIT_HOURS = (8, 48)
FREIGHT_TRANSIT_HOURS = (12, 48)
PALLET_TRANSIT_HOURS = (18, 60)

SHIPPING_STATUS = "DELIVERED"

# Synthetic destination and transport model.
# Germany/Europe uses road transport with parcel carriers.
# Intercontinental destinations use air or sea depending on shipment type.
ROAD_CARRIERS = [
    ("DHL", 0.80),
    ("GLS", 0.20),
]

SEA_DESTINATIONS = [
    ("Egypt", "Africa"),
    ("China", "Asia"),
    ("India", "Asia"),
    ("USA", "North America"),
    ("Australia", "Oceania"),
]

AIR_DESTINATIONS = [
    ("United States", "North America"),
    ("Canada", "North America"),
    ("China", "Asia"),
    ("Japan", "Asia"),
    ("South Korea", "Asia"),
    ("Australia", "Oceania"),
    ("South Africa", "Africa"),
]

EUROPE_DESTINATIONS = [
    ("Germany", "Europe"),
    ("France", "Europe"),
    ("Netherlands", "Europe"),
    ("Belgium", "Europe"),
    ("Austria", "Europe"),
    ("Poland", "Europe"),
    ("Italy", "Europe"),
    ("Spain", "Europe"),
    ("Portugal", "Europe"),
    ("Czech Republic", "Europe"),
    ("Slovakia", "Europe"),
    ("Hungary", "Europe"),
    ("Switzerland", "Europe"),
    ("Denmark", "Europe"),
    ("Sweden", "Europe"),
    ("Norway", "Europe"),
    ("Finland", "Europe"),
    ("Ireland", "Europe"),
    ("United Kingdom", "Europe"),
    ("Romania", "Europe"),
    ("Bulgaria", "Europe"),
    ("Croatia", "Europe"),
    ("Slovenia", "Europe"),
    ("Greece", "Europe"),
]

AIR_TRANSIT_HOURS = (24, 96)
SEA_TRANSIT_HOURS = (120, 480)


def read_csv(file_path: Path) -> list[dict]:
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


def write_csv(
    file_path: Path,
    rows: list[dict],
    fieldnames: list[str],
) -> None:
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
        writer.writerows(rows)


def load_orders() -> list[dict]:
    orders = read_csv(ORDERS_FILE)

    required = {
        "order_id",
        "order_datetime",
        "requested_delivery_datetime",
        "delivery_priority",
        "total_items",
        "total_weight_kg",
    }

    if not orders:
        raise ValueError("orders.csv is empty.")

    missing = required - set(orders[0].keys())

    if missing:
        raise ValueError(
            f"Orders missing fields: {missing}"
        )

    return orders


def load_packing() -> list[dict]:
    packing = read_csv(PACKING_FILE)

    required = {
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
    }

    if not packing:
        raise ValueError("packing.csv is empty.")

    missing = required - set(packing[0].keys())

    if missing:
        raise ValueError(
            f"Packing missing fields: {missing}"
        )

    return packing


def build_order_index(
    orders: list[dict],
) -> dict[str, dict]:
    return {
        row["order_id"]: row
        for row in orders
    }


def build_packing_index(
    packing: list[dict],
) -> dict[str, dict]:
    return {
        row["order_id"]: row
        for row in packing
    }


def determine_shipping_method(
    packing_type: str,
) -> str:
    if packing_type == "SMALL_PACKAGE":
        return "PARCEL"

    if packing_type == "LARGE_PACKAGE":
        return "FREIGHT"

    if packing_type == "PALLET_SHIPMENT":
        return "PALLET_FREIGHT"

    raise ValueError(
        f"Unknown packing type: {packing_type}"
    )


def determine_transport(
    shipping_method: str,
    rng: random.Random,
) -> tuple[str, str, str, str]:
    """
    Returns:
        transport_mode,
        vehicle_type,
        carrier,
        destination_country,
        destination_region
    """

    if shipping_method == "PARCEL":
        destination_country, destination_region = rng.choice(
            EUROPE_DESTINATIONS
        )

        return (
            "ROAD",
            "VAN",
            rng.choices(
                [carrier for carrier, _ in ROAD_CARRIERS],
                weights=[weight for _, weight in ROAD_CARRIERS],
                k=1,
            )[0],
            destination_country,
            destination_region,
        )

    if shipping_method == "FREIGHT":
        # Large packages remain a road freight flow in the current model.
        destination_country, destination_region = rng.choice(
            EUROPE_DESTINATIONS
        )

        return (
            "ROAD",
            "TRUCK",
            rng.choices(
                [carrier for carrier, _ in ROAD_CARRIERS],
                weights=[weight for _, weight in ROAD_CARRIERS],
                k=1,
            )[0],
            destination_country,
            destination_region,
        )

    if shipping_method == "PALLET_FREIGHT":
        # European pallet shipments are handled by road freight.
        # Non-European pallet shipments are handled internationally
        # by air or sea, with sea used for a small share.
        if rng.random() < 0.95:
            destination_country, destination_region = rng.choice(
                EUROPE_DESTINATIONS
            )

            return (
                "ROAD",
                "TRUCK",
                rng.choices(
                [carrier for carrier, _ in ROAD_CARRIERS],
                weights=[weight for _, weight in ROAD_CARRIERS],
                k=1,
            )[0],
                destination_country,
                destination_region,
            )

        # Of the non-European pallet shipments, approximately 80% use air
        # and 20% use sea. This keeps sea freight at roughly 1% overall.
        if rng.random() < 0.80:
            destination_country, destination_region = rng.choice(
                AIR_DESTINATIONS
            )

            return (
                "AIR",
                "AIRCRAFT",
                "AIR_FREIGHT",
                destination_country,
                destination_region,
            )

        destination_country, destination_region = rng.choice(
            SEA_DESTINATIONS
        )

        return (
            "SEA",
            "CONTAINER_SHIP",
            "OCEAN_FREIGHT",
            destination_country,
            destination_region,
        )

    raise ValueError(
        f"Unknown shipping method: {shipping_method}"
    )


def get_transit_hours(
    shipping_method: str,
    transport_mode: str,
    rng: random.Random,
) -> int:
    if transport_mode == "AIR":
        return rng.randint(
            *AIR_TRANSIT_HOURS
        )

    if transport_mode == "SEA":
        return rng.randint(
            *SEA_TRANSIT_HOURS
        )

    if shipping_method == "PARCEL":
        return rng.randint(
            *PARCEL_TRANSIT_HOURS
        )

    if shipping_method == "FREIGHT":
        return rng.randint(
            *FREIGHT_TRANSIT_HOURS
        )

    if shipping_method == "PALLET_FREIGHT":
        return rng.randint(
            *PALLET_TRANSIT_HOURS
        )

    raise ValueError(
        f"Unknown shipping method: {shipping_method}"
    )


def generate_tracking_number(
    shipping_method: str,
    shipment_number: int,
) -> str:
    prefix = {
        "PARCEL": "PARCEL",
        "FREIGHT": "FREIGHT",
        "PALLET_FREIGHT": "PALLET",
    }[shipping_method]

    return f"{prefix}-{shipment_number:08d}"


def generate_shipping_records(
    orders: list[dict],
    packing: list[dict],
) -> list[dict]:
    rng = random.Random(RANDOM_SEED)

    order_index = build_order_index(orders)
    packing_index = build_packing_index(packing)

    records = []

    for shipment_number, order in enumerate(
        orders,
        start=1,
    ):
        order_id = order["order_id"]

        if order_id not in packing_index:
            raise ValueError(
                f"Order {order_id} has no packing record."
            )

        pack = packing_index[order_id]

        if pack["packing_status"] != "PACKED":
            raise ValueError(
                f"Order {order_id} is not packed."
            )

        packing_completed_at = datetime.fromisoformat(
            pack["packing_completed_at"]
        )

        requested_delivery = datetime.fromisoformat(
            order["requested_delivery_datetime"]
        )

        shipping_method = determine_shipping_method(
            pack["packing_type"]
        )

        (
            transport_mode,
            vehicle_type,
            carrier,
            destination_country,
            destination_region,
        ) = determine_transport(
            shipping_method,
            rng,
        )

        preparation_minutes = rng.randint(
            *PREPARATION_MINUTES
        )

        shipped_at = (
            packing_completed_at
            + timedelta(minutes=preparation_minutes)
        )

        transit_hours = get_transit_hours(
            shipping_method,
            transport_mode,
            rng,
        )

        delivered_at = (
            shipped_at
            + timedelta(hours=transit_hours)
        )

        fulfillment_hours = (
            delivered_at
            - datetime.fromisoformat(
                order["order_datetime"]
            )
        ).total_seconds() / 3600

        delivery_margin_hours = (
            requested_delivery - delivered_at
        ).total_seconds() / 3600

        on_time = delivered_at <= requested_delivery

        records.append(
            {
                "shipment_id": (
                    f"SHIP-{shipment_number:06d}"
                ),
                "order_id": order_id,
                "packing_id": pack["packing_id"],
                "shipping_method": shipping_method,
                "transport_mode": transport_mode,
                "vehicle_type": vehicle_type,
                "carrier": carrier,
                "origin_country": "Germany",
                "destination_country": destination_country,
                "destination_region": destination_region,
                "carrier_type": shipping_method,
                "tracking_number": generate_tracking_number(
                    shipping_method,
                    shipment_number,
                ),
                "container_id": pack["container_id"],
                "container_type": pack["container_type"],
                "shipment_status": SHIPPING_STATUS,
                "packing_completed_at": (
                    packing_completed_at.isoformat(
                        timespec="seconds"
                    )
                ),
                "shipped_at": (
                    shipped_at.isoformat(
                        timespec="seconds"
                    )
                ),
                "requested_delivery_datetime": (
                    requested_delivery.isoformat(
                        timespec="seconds"
                    )
                ),
                "delivered_at": (
                    delivered_at.isoformat(
                        timespec="seconds"
                    )
                ),
                "transit_hours": transit_hours,
                "shipping_preparation_minutes": (
                    preparation_minutes
                ),
                "fulfillment_hours": round(
                    fulfillment_hours,
                    2,
                ),
                "delivery_margin_hours": round(
                    delivery_margin_hours,
                    2,
                ),
                "on_time_delivery": str(
                    on_time
                ).upper(),
                "delivery_priority": (
                    order["delivery_priority"]
                ),
            }
        )

    return records


def validate_shipping(
    shipping: list[dict],
    orders: list[dict],
    packing: list[dict],
) -> None:
    print()
    print("Validating shipping...")

    order_ids = {
        row["order_id"]
        for row in orders
    }

    packing_order_ids = {
        row["order_id"]
        for row in packing
    }

    shipping_order_ids = {
        row["order_id"]
        for row in shipping
    }

    assert len(shipping) == len(orders), (
        "Shipping record count does not match "
        "order count."
    )

    assert shipping_order_ids == order_ids, (
        "Shipping orders do not match orders."
    )

    assert packing_order_ids == order_ids, (
        "Some orders are missing packing records."
    )

    assert len(shipping_order_ids) == len(shipping), (
        "Duplicate shipping records detected."
    )

    order_index = build_order_index(orders)

    for row in shipping:
        order_id = row["order_id"]

        packing_completed_at = datetime.fromisoformat(
            row["packing_completed_at"]
        )

        shipped_at = datetime.fromisoformat(
            row["shipped_at"]
        )

        delivered_at = datetime.fromisoformat(
            row["delivered_at"]
        )

        requested_delivery = datetime.fromisoformat(
            order_index[order_id][
                "requested_delivery_datetime"
            ]
        )

        order_datetime = datetime.fromisoformat(
            order_index[order_id]["order_datetime"]
        )

        assert shipped_at > packing_completed_at, (
            f"Shipment starts before packing completed "
            f"for {order_id}"
        )

        assert delivered_at > shipped_at, (
            f"Delivery occurs before shipment "
            f"for {order_id}"
        )

        assert delivered_at > order_datetime, (
            f"Delivery occurs before order "
            f"for {order_id}"
        )

        expected_on_time = (
            delivered_at <= requested_delivery
        )

        assert (
            row["on_time_delivery"]
            == str(expected_on_time).upper()
        ), (
            f"Invalid on-time flag for {order_id}"
        )

        expected_method = determine_shipping_method(
            next(
                pack["packing_type"]
                for pack in packing
                if pack["order_id"] == order_id
            )
        )

        assert row["shipping_method"] == expected_method, (
            f"Invalid shipping method for {order_id}"
        )

        if row["shipping_method"] in {"PARCEL", "FREIGHT"}:
            assert row["transport_mode"] == "ROAD", (
                f"Invalid road transport mode for {order_id}"
            )
            assert row["carrier"] in {carrier for carrier, _ in ROAD_CARRIERS}, (
                f"Invalid road carrier for {order_id}"
            )

        elif row["shipping_method"] == "PALLET_FREIGHT":
            assert row["transport_mode"] in {"ROAD", "AIR", "SEA"}, (
                f"Invalid pallet transport mode for {order_id}"
            )

            if row["transport_mode"] == "ROAD":
                assert row["carrier"] in {carrier for carrier, _ in ROAD_CARRIERS}, (
                    f"Invalid road carrier for {order_id}"
                )
                assert row["destination_country"] in {
                    country for country, _ in EUROPE_DESTINATIONS
                }, (
                    f"Road pallet shipment has non-European destination "
                    f"for {order_id}"
                )

            elif row["transport_mode"] == "AIR":
                assert row["destination_country"] in {
                    country for country, _ in AIR_DESTINATIONS
                }, (
                    f"Air pallet shipment has invalid destination "
                    f"for {order_id}"
                )

            elif row["transport_mode"] == "SEA":
                assert row["destination_country"] in {
                    country for country, _ in SEA_DESTINATIONS
                }, (
                    f"Sea pallet shipment has invalid destination "
                    f"for {order_id}"
                )

        assert row["origin_country"] == "Germany"

        assert row["destination_country"].strip()
        assert row["destination_region"].strip()
        assert row["vehicle_type"].strip()

        assert row["shipment_status"] == "DELIVERED"

        assert row["tracking_number"].strip()

        assert float(
            row["fulfillment_hours"]
        ) > 0

        calculated_margin = (
            requested_delivery - delivered_at
        ).total_seconds() / 3600

        assert abs(
            calculated_margin
            - float(row["delivery_margin_hours"])
        ) < 0.02, (
            f"Invalid delivery margin for {order_id}"
        )

    print("Shipping validation passed.")


def print_shipping_summary(
    shipping: list[dict],
) -> None:
    shipping_methods = {}
    transport_modes = {}
    carriers = {}
    on_time_count = 0
    late_count = 0

    for row in shipping:
        transport_mode = row["transport_mode"]
        carrier = row["carrier"]

        transport_modes[transport_mode] = (
            transport_modes.get(transport_mode, 0) + 1
        )

        carriers[carrier] = (
            carriers.get(carrier, 0) + 1
        )
        method = row["shipping_method"]

        shipping_methods[method] = (
            shipping_methods.get(method, 0) + 1
        )

        if row["on_time_delivery"] == "TRUE":
            on_time_count += 1
        else:
            late_count += 1

    fulfillment_hours = [
        float(row["fulfillment_hours"])
        for row in shipping
    ]

    avg_fulfillment = (
        sum(fulfillment_hours)
        / len(fulfillment_hours)
    )

    print()
    print("Warehouse Shipping Summary")
    print("===========================")
    print(
        f"Shipments:             "
        f"{len(shipping):,}"
    )

    print()
    print("Shipping Method")
    print("---------------")

    for method in (
        "PARCEL",
        "FREIGHT",
        "PALLET_FREIGHT",
    ):
        print(
            f"{method:<20}"
            f"{shipping_methods.get(method, 0):>8,}"
        )

    print()
    print("Transport Mode")
    print("--------------")

    for mode in ("ROAD", "AIR", "SEA"):
        print(
            f"{mode:<20}"
            f"{transport_modes.get(mode, 0):>8,}"
        )

    print()
    print("Carrier / Transport Provider")
    print("----------------------------")

    for carrier, count in sorted(carriers.items()):
        print(
            f"{carrier:<25}{count:>8,}"
        )

    print()
    print("Delivery Performance")
    print("--------------------")
    print(
        f"On-time deliveries:    "
        f"{on_time_count:>8,}"
    )
    print(
        f"Late deliveries:       "
        f"{late_count:>8,}"
    )

    on_time_rate = (
        on_time_count
        / len(shipping)
        * 100
    )

    print(
        f"On-time delivery rate: "
        f"{on_time_rate:>7.2f}%"
    )

    print(
        f"Avg fulfillment time:  "
        f"{avg_fulfillment:>7.2f} h"
    )


def export_shipping(
    shipping: list[dict],
) -> None:
    fieldnames = [
        "shipment_id",
        "order_id",
        "packing_id",
        "shipping_method",
        "transport_mode",
        "vehicle_type",
        "carrier",
        "origin_country",
        "destination_country",
        "destination_region",
        "carrier_type",
        "tracking_number",
        "container_id",
        "container_type",
        "shipment_status",
        "packing_completed_at",
        "shipped_at",
        "requested_delivery_datetime",
        "delivered_at",
        "transit_hours",
        "shipping_preparation_minutes",
        "fulfillment_hours",
        "delivery_margin_hours",
        "on_time_delivery",
        "delivery_priority",
    ]

    write_csv(
        SHIPPING_FILE,
        shipping,
        fieldnames,
    )

    print()
    print("Shipping export complete:")
    print(SHIPPING_FILE)


def main() -> None:
    print()
    print("Warehouse Shipping Generator")
    print("============================")

    print()
    print("Loading orders...")

    orders = load_orders()

    print(
        f"Orders loaded: "
        f"{len(orders):,}"
    )

    print()
    print("Loading packing...")

    packing = load_packing()

    print(
        f"Packing records loaded: "
        f"{len(packing):,}"
    )

    print()
    print("Generating shipping records...")

    shipping = generate_shipping_records(
        orders=orders,
        packing=packing,
    )

    print(
        f"Shipping records generated: "
        f"{len(shipping):,}"
    )

    validate_shipping(
        shipping=shipping,
        orders=orders,
        packing=packing,
    )

    print_shipping_summary(
        shipping
    )

    export_shipping(
        shipping
    )


if __name__ == "__main__":
    main()
