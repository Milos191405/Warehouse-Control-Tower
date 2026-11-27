#!/usr/bin/env python3
"""
Warehouse Fire Protection & Safety Inspection Generator.

Generates sprinklers, main control valves, and hydrants aligned to the exact
2D facility floor plan coordinates (X: 0..100, Y: 0..62) across Hall 1, Hall 2,
and Hall 3, along with realistic inspection dates, due dates, pressure readings,
and compliance statuses.
"""

from __future__ import annotations

import csv
import os
import random
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(os.getenv("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed"))
OUTPUT_FILE = OUTPUT_DIR / "fire_safety.csv"

REFERENCE_DATE = date(2026, 11, 26)
SEED = 42

# Exact bounding boxes matching powerbi/mockups/warehouse_floor_plan_clean.png
# (hall_id, zone_nr, area_label, x_min, y_min, x_max, y_max, cols, rows)
ZONE_GRIDS = [
    # Hall 1
    (1, 1, "ZONE 01 - High Rack", 5.5, 36.0, 17.5, 51.0, 3, 3),
    (1, 2, "ZONE 02 - Low Rack", 22.5, 36.0, 34.5, 51.0, 3, 3),
    (1, 3, "ZONES 03-04 - Vertical Lifts", 39.5, 36.0, 52.5, 51.0, 3, 3),
    (1, 5, "ZONES 05-07 - Picking Cart Areas", 6.0, 19.0, 34.0, 30.0, 5, 2),
    (1, 6, "H1-KP (01-05) Small Packing", 6.0, 9.0, 24.0, 13.5, 3, 1),
    (1, 7, "H1-GP (01-09) Large Packing", 30.0, 9.0, 52.0, 13.5, 4, 1),
    # Hall 2
    (2, 8, "ZONE 08 - Vertical Lift", 63.0, 40.0, 78.0, 51.0, 3, 2),
    (2, 9, "ZONE 09 - High Rack", 63.0, 24.0, 78.0, 34.0, 3, 2),
    (2, 10, "ZONE 10 - Low Rack", 63.0, 9.5, 78.0, 18.0, 3, 2),
    # Hall 3
    (3, 11, "ZONE 11 - Low Rack", 88.5, 36.0, 94.5, 51.0, 2, 3),
    (3, 12, "ZONE 12 - Stapler Picking", 88.5, 19.0, 94.5, 30.0, 2, 2),
    (3, 12, "H3-GP (01-02) Packing", 88.5, 9.5, 94.5, 13.5, 2, 1),
]

# Main Control Valves (hall_id, zone_nr, area_label, x, y, code)
CONTROL_VALVES = [
    (1, 1, "Hall 1 North Main Riser", 3.2, 51.0, "V-H1-N"),
    (1, 5, "Hall 1 South Main Riser", 3.2, 16.0, "V-H1-S"),
    (1, 3, "Hall 1 East Packing Valve", 54.8, 30.0, "V-H1-E"),
    (2, 8, "Hall 2 North Main Riser", 60.2, 48.0, "V-H2-N"),
    (2, 10, "Hall 2 South Main Riser", 60.2, 14.0, "V-H2-S"),
    (3, 11, "Hall 3 Main Riser", 85.8, 30.0, "V-H3-M"),
]

# Hydrants / Hose Reels along docks & main aisles
HYDRANTS = [
    (1, 6, "Hall 1 Dock West", 10.0, 4.8, "HYD-H1-01"),
    (1, 7, "Hall 1 Dock Center", 36.0, 4.8, "HYD-H1-02"),
    (1, 7, "Hall 1 Dock East", 48.0, 4.8, "HYD-H1-03"),
    (2, 10, "Hall 2 Dock West", 66.0, 4.8, "HYD-H2-01"),
    (2, 10, "Hall 2 Dock East", 75.0, 4.8, "HYD-H2-02"),
    (3, 12, "Hall 3 Dock", 90.0, 4.8, "HYD-H3-01"),
]

INSPECTORS = [
    "TÜV-SÜD-BW-01",
    "TÜV-SÜD-BW-02",
    "DEKRA-IND-04",
    "INTERNAL-HSE-01",
    "INTERNAL-HSE-02",
]


def _linspace(start: float, stop: float, count: int) -> list[float]:
    if count <= 1:
        return [round((start + stop) / 2.0, 2)]
    step = (stop - start) / (count - 1)
    return [round(start + i * step, 2) for i in range(count)]


def _build_inspection_record(
    rng: random.Random,
    device_id: str,
    device_type: str,
    hall_id: int,
    zone_nr: int,
    area_label: str,
    x_coord: float,
    y_coord: float,
    force_status: str | None = None,
) -> dict:
    freq_days = 180 if device_type in ("SPRINKLER", "CONTROL_VALVE") else 365

    # Realistic distribution: ~85% COMPLIANT, ~10% DUE_SOON, ~5% OVERDUE
    if force_status:
        target_status = force_status
    else:
        roll = rng.random()
        if roll < 0.85:
            target_status = "COMPLIANT"
        elif roll < 0.95:
            target_status = "DUE_SOON"
        else:
            target_status = "OVERDUE"

    if target_status == "COMPLIANT":
        days_until_due = rng.randint(31, freq_days - 5)
    elif target_status == "DUE_SOON":
        days_until_due = rng.randint(1, 30)
    else:
        days_until_due = -rng.randint(1, 45)

    next_due = REFERENCE_DATE + timedelta(days=days_until_due)
    last_insp = next_due - timedelta(days=freq_days)
    install_date = date(2021, 1, 1) + timedelta(days=rng.randint(0, 700))

    if target_status == "OVERDUE":
        pressure = round(rng.uniform(4.8, 6.1), 2)
        note = "Inspection overdue - schedule maintenance check"
    elif target_status == "DUE_SOON":
        pressure = round(rng.uniform(6.4, 7.8), 2)
        note = "Routine inspection due within 30 days"
    else:
        pressure = round(rng.uniform(6.8, 8.4), 2)
        note = "Passed visual & pressure test"

    return {
        "device_id": device_id,
        "device_type": device_type,
        "hall_id": hall_id,
        "zone_nr": zone_nr,
        "area_label": area_label,
        "x_coord": x_coord,
        "y_coord": y_coord,
        "installation_date": install_date.isoformat(),
        "inspection_frequency_days": freq_days,
        "last_inspection_date": last_insp.isoformat(),
        "next_inspection_due": next_due.isoformat(),
        "days_until_due": days_until_due,
        "inspection_status": target_status,
        "inspector_id": rng.choice(INSPECTORS),
        "pressure_bar": pressure,
        "notes": note,
    }


def generate_fire_safety_data() -> list[dict]:
    rng = random.Random(SEED)
    records: list[dict] = []

    # 1. Sprinklers across all zones
    sprinkler_seq = 1
    for hall_id, zone_nr, area_label, x_min, y_min, x_max, y_max, cols, rows in ZONE_GRIDS:
        xs = _linspace(x_min, x_max, cols)
        ys = _linspace(y_min, y_max, rows)
        for y in ys:
            for x in xs:
                dev_id = f"FP-H{hall_id}-Z{zone_nr:02d}-SP-{sprinkler_seq:03d}"
                records.append(
                    _build_inspection_record(
                        rng, dev_id, "SPRINKLER", hall_id, zone_nr, area_label, x, y
                    )
                )
                sprinkler_seq += 1

    # 2. Main Control Valves (ensure 1 overdue and 1 due_soon for realistic demo)
    for idx, (hall_id, zone_nr, area_label, x, y, code) in enumerate(CONTROL_VALVES):
        forced = None
        if idx == 1:
            forced = "OVERDUE"
        elif idx == 3:
            forced = "DUE_SOON"
        records.append(
            _build_inspection_record(
                rng, code, "CONTROL_VALVE", hall_id, zone_nr, area_label, x, y, force_status=forced
            )
        )

    # 3. Hydrants along loading docks
    for hall_id, zone_nr, area_label, x, y, code in HYDRANTS:
        records.append(
            _build_inspection_record(
                rng, code, "HYDRANT", hall_id, zone_nr, area_label, x, y
            )
        )

    return records


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = generate_fire_safety_data()

    fieldnames = [
        "device_id",
        "device_type",
        "hall_id",
        "zone_nr",
        "area_label",
        "x_coord",
        "y_coord",
        "installation_date",
        "inspection_frequency_days",
        "last_inspection_date",
        "next_inspection_due",
        "days_until_due",
        "inspection_status",
        "inspector_id",
        "pressure_bar",
        "notes",
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    status_counts = {}
    for r in records:
        st = r["inspection_status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    print(f"Generated {len(records)} fire safety devices -> {OUTPUT_FILE}")
    print(f"Status summary: {status_counts}")


if __name__ == "__main__":
    main()
