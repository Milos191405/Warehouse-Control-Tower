#!/usr/bin/env python3
"""
Warehouse Logistics Data Generator - Master Execution Pipeline

Runs all warehouse simulation generators in strict dependency order,
executes cross-dataset validation, and generates picking capacity diagnostics.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = Path(
    os.getenv("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed")
).resolve()

PIPELINE_STEPS = [
    (
        "business_calendar.py",
        "Step 1/11: Generating Baden-Württemberg Business Calendar",
        ["calendar.csv"],
    ),
    (
        "location.py",
        "Step 2/11: Generating 3-Hall Warehouse Storage Locations (24,180 positions)",
        ["locations.csv"],
    ),
    (
        "products.py",
        "Step 3/11: Standardizing ABB Product Master Data",
        ["product_master.csv"],
    ),
    (
        "inventory.py",
        "Step 4/11: Generating Opening Warehouse Inventory Snapshot",
        ["inventory.csv"],
    ),
    (
        "orders.py",
        "Step 5/11: Generating Customers, Orders & Order Line Items",
        ["customers.csv", "orders.csv", "order_items.csv"],
    ),
    (
        "picking.py",
        "Step 6/11: Simulating Warehouse Picking & Hall Capacity Queue",
        ["picking.csv"],
    ),
    (
        "packing.py",
        "Step 7/11: Simulating Packing Stations & Package Classification",
        ["packing.csv"],
    ),
    (
        "shipping.py",
        "Step 8/11: Simulating Dispatch, Transit & Delivery Performance",
        ["shipping.csv"],
    ),
    (
        "finalize_order_items.py",
        "Step 9/11: Finalizing Order Items (picked / packed / shipped quantity & status)",
        [],
    ),
    (
        "validation.py",
        "Step 10/11: Running Cross-Dataset Referential & Business Logic Validation",
        [],
    ),
    (
        "check_generator_output.py",
        "Step 11/11: Independent Cross-File Consistency Checks (keys, timing, capacity)",
        [],
    ),
]

DIAGNOSTICS_STEP = (
    "picking_capacity_diagnostics.py",
    "Bonus Diagnostic: Generating Picking Capacity & Lateness Reports",
    [
        "diagnostics/daily_hall_load.csv",
        "diagnostics/hourly_capacity_check.csv",
        "diagnostics/capacity_violations.csv",
        "diagnostics/monthly_timeliness.csv",
        "diagnostics/order_lateness_detail.csv",
        "diagnostics/daily_total_load.csv",
    ],
)


def find_script(script_name: str) -> Path:
    direct_candidates = [
        PROJECT_ROOT / script_name,
        PROJECT_ROOT / "src" / script_name,
        PROJECT_ROOT / "src" / "generators" / script_name,
        PROJECT_ROOT / "src" / "pipeline" / script_name,
        PROJECT_ROOT / "src" / "diagnostics" / script_name,
    ]
    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    matches = [
        path
        for path in PROJECT_ROOT.rglob(script_name)
        if ".venv" not in path.parts and "venv" not in path.parts
    ]
    if not matches:
        raise FileNotFoundError(
            f"Could not find '{script_name}' anywhere under {PROJECT_ROOT}"
        )
    return matches[0]


def run_step(script_name: str, description: str, expected_outputs: list[str]) -> float:
    script_path = find_script(script_name)

    print()
    print("=" * 72)
    print(description)
    print(f"Script: {script_path.relative_to(PROJECT_ROOT)}")
    print("=" * 72)

    env = os.environ.copy()
    env["WCT_PROCESSED_DIR"] = str(PROCESSED_DIR)
    existing_pythonpath = env.get("PYTHONPATH", "")
    generators_dir = str(PROJECT_ROOT / "src" / "generators")
    script_dir = str(script_path.parent)
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, [script_dir, generators_dir, existing_pythonpath])
    )

    start_time = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(script_path.parent),
        env=env,
    )
    elapsed = time.perf_counter() - start_time

    if result.returncode != 0:
        raise RuntimeError(
            f"Pipeline failed at '{script_name}' (exit code {result.returncode})."
        )

    for rel_output in expected_outputs:
        output_path = PROCESSED_DIR / rel_output
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise FileNotFoundError(
                f"Expected output file missing or empty after {script_name}: {output_path}"
            )

    print(f"\n[OK] {script_name} finished in {elapsed:.2f}s")
    return elapsed


def print_final_manifest(total_elapsed: float, include_diagnostics: bool) -> None:
    all_outputs = [out for _, _, outputs in PIPELINE_STEPS for out in outputs]
    if include_diagnostics:
        all_outputs.extend(DIAGNOSTICS_STEP[2])

    print()
    print("=" * 72)
    print("WAREHOUSE DATA GENERATOR - PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 72)
    print(f"Output directory: {PROCESSED_DIR}")
    print(f"Total runtime:    {total_elapsed:.2f}s")
    print()
    print("Generated CSV Files:")
    print("-" * 72)

    for rel_path in all_outputs:
        file_path = PROCESSED_DIR / rel_path
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"  {rel_path:<42} {size_mb:>8.2f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the complete Warehouse Logistics CSV generation pipeline."
    )
    parser.add_argument(
        "--skip-diagnostics",
        action="store_true",
        help="Skip running picking_capacity_diagnostics.py at the end.",
    )
    args = parser.parse_args()

    print()
    print("Warehouse Logistics Data Generator - Full Simulation Pipeline")
    print("-------------------------------------------------------------")
    print(f"Python executable: {sys.executable}")
    print(f"Target output dir: {PROCESSED_DIR}")

    pipeline_start = time.perf_counter()

    for script_name, description, expected_outputs in PIPELINE_STEPS:
        run_step(script_name, description, expected_outputs)

    if not args.skip_diagnostics:
        run_step(*DIAGNOSTICS_STEP)

    total_elapsed = time.perf_counter() - pipeline_start
    print_final_manifest(
        total_elapsed=total_elapsed,
        include_diagnostics=not args.skip_diagnostics,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)