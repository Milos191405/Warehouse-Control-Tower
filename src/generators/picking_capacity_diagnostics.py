#!/usr/bin/env python3
"""
Warehouse Control Tower - Picking Capacity Diagnostics

Read-only diagnostic for:
  data/processed/orders.csv
  data/processed/picking.csv
  data/processed/calendar.csv

Writes one report CSV per diagnostic to:
  data/processed/diagnostics/

This script does not modify source data or rerun generators.
"""

from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path
import csv
import math
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROCESSED_DIR / "diagnostics"

ORDERS_FILE = PROCESSED_DIR / "orders.csv"
PICKING_FILE = PROCESSED_DIR / "picking.csv"
CALENDAR_FILE = PROCESSED_DIR / "calendar.csv"

HALL_CAPACITY_PER_HOUR = {1: 42, 2: 10, 3: 4}
SHIFT_HOURS_PER_DAY = 15.0  # 06:30-22:45 minus 45 min + 30 min breaks = 15 h
# NOTE: the shift windows overlap at 14:45 in the current configuration only as
# a boundary; productive minutes total 7h30 + 7h30 = 15 h/day.

def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def parse_dt(value, field_name, row_id):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field_name}={value!r} for {row_id}") from exc

def pct(n, total):
    return 100.0 * n / total if total else 0.0

def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    print("Warehouse Picking Capacity Diagnostics")
    print("=" * 44)
    orders = read_csv(ORDERS_FILE)
    picks = read_csv(PICKING_FILE)
    calendar = read_csv(CALENDAR_FILE)

    required_order_cols = {"order_id", "order_datetime", "requested_delivery_datetime"}
    required_pick_cols = {"picking_id", "order_id", "hall_id", "pick_datetime"}
    required_cal_cols = {"date", "warehouse_capacity_multiplier"}
    if orders and not required_order_cols.issubset(orders[0]):
        raise ValueError(f"orders.csv missing columns: {sorted(required_order_cols - set(orders[0]))}")
    if picks and not required_pick_cols.issubset(picks[0]):
        raise ValueError(f"picking.csv missing columns: {sorted(required_pick_cols - set(picks[0]))}")
    if calendar and not required_cal_cols.issubset(calendar[0]):
        raise ValueError(f"calendar.csv missing columns: {sorted(required_cal_cols - set(calendar[0]))}")

    order_by_id = {r["order_id"]: r for r in orders}
    deadline_by_order = {
        oid: parse_dt(r["requested_delivery_datetime"], "requested_delivery_datetime", oid)
        for oid, r in order_by_id.items()
    }
    order_time_by_order = {
        oid: parse_dt(r["order_datetime"], "order_datetime", oid)
        for oid, r in order_by_id.items()
    }

    # Aggregate pick operations per order and compute each order's final pick.
    picks_by_order = defaultdict(list)
    by_hall_day = Counter()
    by_hall_hour = Counter()
    picks_after_deadline = Counter()
    daily_total = Counter()
    monthly_total = Counter()
    monthly_late_orders = Counter()
    monthly_orders = Counter()
    order_final_pick = {}

    parsed_picks = []
    for r in picks:
        oid = r["order_id"]
        if oid not in order_by_id:
            continue
        ts = parse_dt(r["pick_datetime"], "pick_datetime", r["picking_id"])
        try:
            hall = int(r["hall_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid hall_id={r['hall_id']!r} for {r['picking_id']}") from exc
        parsed_picks.append((r, oid, ts, hall))
        picks_by_order[oid].append(ts)
        by_hall_day[(hall, ts.date())] += 1
        by_hall_hour[(hall, ts.date(), ts.hour)] += 1
        daily_total[ts.date()] += 1
        if ts >= deadline_by_order[oid]:
            picks_after_deadline[oid] += 1
        if oid not in order_final_pick or ts > order_final_pick[oid]:
            order_final_pick[oid] = ts

    for oid, order in order_by_id.items():
        month = order_time_by_order[oid].strftime("%Y-%m")
        monthly_orders[month] += 1
        final_pick = order_final_pick.get(oid)
        if final_pick and final_pick >= deadline_by_order[oid]:
            monthly_late_orders[month] += 1

    for day, n in daily_total.items():
        monthly_total[day.strftime("%Y-%m")] += n

    # Read calendar multipliers and estimate theoretical daily capacity.
    capacity_by_day = {}
    for row in calendar:
        d = date.fromisoformat(row["date"])
        capacity_by_day[d] = float(row["warehouse_capacity_multiplier"])

    # Capacity uses one hourly bucket per (hall, date, hour), matching queue logic.
    # The queue counts a pick in the timestamp's hour; shifts and breaks are checked separately.
    observed_hour_rows = []
    capacity_violations = []
    for (hall, day, hour), n in sorted(by_hall_hour.items()):
        factor = capacity_by_day.get(day, 0.0)
        limit = math.floor(HALL_CAPACITY_PER_HOUR.get(hall, 0) * factor)
        observed_hour_rows.append({
            "date": day.isoformat(),
            "hall_id": hall,
            "hour": hour,
            "picking_operations": n,
            "capacity_multiplier": factor,
            "hourly_limit": limit,
            "utilization_pct": round(pct(n, limit), 2) if limit else "",
        })
        if n > limit:
            capacity_violations.append({
                "date": day.isoformat(),
                "hall_id": hall,
                "hour": hour,
                "picking_operations": n,
                "hourly_limit": limit,
            })

    # Daily workload and theoretical daily capacity by hall.
    daily_hall_rows = []
    for day in sorted(set(d for _, d in by_hall_day) | set(capacity_by_day)):
        factor = capacity_by_day.get(day, 0.0)
        for hall, hourly_cap in sorted(HALL_CAPACITY_PER_HOUR.items()):
            observed = by_hall_day[(hall, day)]
            # Approximate 15 productive hours/day. This is a rough upper bound,
            # not an exact count of valid hourly buckets across shifts/breaks.
            theoretical = math.floor(hourly_cap * factor * SHIFT_HOURS_PER_DAY)
            daily_hall_rows.append({
                "date": day.isoformat(),
                "hall_id": hall,
                "picking_operations": observed,
                "capacity_multiplier": factor,
                "approx_daily_capacity": theoretical,
                "utilization_pct": round(pct(observed, theoretical), 2) if theoretical else "",
                "backlog_signal": observed > theoretical,
            })

    # Monthly order timeliness.
    monthly_rows = []
    for month in sorted(monthly_orders):
        total_orders = monthly_orders[month]
        late = monthly_late_orders[month]
        monthly_rows.append({
            "order_month": month,
            "orders": total_orders,
            "orders_late_by_final_pick": late,
            "orders_on_time_by_final_pick": total_orders - late,
            "late_pct": round(pct(late, total_orders), 2),
            "picking_operations_scheduled_in_month": monthly_total.get(month, 0),
        })

    # Per-order lateness details, useful for identifying long-tail cases.
    lateness_rows = []
    for oid, order in order_by_id.items():
        deadline = deadline_by_order[oid]
        final_pick = order_final_pick.get(oid)
        if final_pick is None:
            continue
        delay_hours = max(0.0, (final_pick - deadline).total_seconds() / 3600)
        lateness_rows.append({
            "order_id": oid,
            "order_datetime": order_time_by_order[oid].isoformat(sep=" "),
            "deadline": deadline.isoformat(sep=" "),
            "final_pick_datetime": final_pick.isoformat(sep=" "),
            "late": final_pick >= deadline,
            "delay_hours": round(delay_hours, 2),
            "picking_operations": len(picks_by_order[oid]),
            "picks_after_deadline": picks_after_deadline[oid],
        })
    lateness_rows.sort(key=lambda r: r["delay_hours"], reverse=True)

    # Daily total timeline: compare actual workload against approximate total capacity.
    daily_rows = []
    for day in sorted(set(daily_total) | set(capacity_by_day)):
        factor = capacity_by_day.get(day, 0.0)
        actual = daily_total[day]
        total_cap = math.floor(sum(HALL_CAPACITY_PER_HOUR.values()) * factor * SHIFT_HOURS_PER_DAY)
        daily_rows.append({
            "date": day.isoformat(),
            "picking_operations": actual,
            "capacity_multiplier": factor,
            "approx_total_capacity": total_cap,
            "utilization_pct": round(pct(actual, total_cap), 2) if total_cap else "",
            "backlog_signal": actual > total_cap,
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "daily_hall_load.csv",
              ["date", "hall_id", "picking_operations", "capacity_multiplier",
               "approx_daily_capacity", "utilization_pct", "backlog_signal"],
              daily_hall_rows)
    write_csv(OUTPUT_DIR / "hourly_capacity_check.csv",
              ["date", "hall_id", "hour", "picking_operations", "capacity_multiplier",
               "hourly_limit", "utilization_pct"],
              observed_hour_rows)
    write_csv(OUTPUT_DIR / "capacity_violations.csv",
              ["date", "hall_id", "hour", "picking_operations", "hourly_limit"],
              capacity_violations)
    write_csv(OUTPUT_DIR / "monthly_timeliness.csv",
              ["order_month", "orders", "orders_late_by_final_pick", "orders_on_time_by_final_pick",
               "late_pct", "picking_operations_scheduled_in_month"],
              monthly_rows)
    write_csv(OUTPUT_DIR / "order_lateness_detail.csv",
              ["order_id", "order_datetime", "deadline", "final_pick_datetime", "late",
               "delay_hours", "picking_operations", "picks_after_deadline"],
              lateness_rows)
    write_csv(OUTPUT_DIR / "daily_total_load.csv",
              ["date", "picking_operations", "capacity_multiplier", "approx_total_capacity",
               "utilization_pct", "backlog_signal"],
              daily_rows)

    late_orders = sum(1 for row in lateness_rows if row["late"])
    print(f"Orders loaded: {len(orders):,}")
    print(f"Picking operations loaded: {len(picks):,}")
    print(f"Orders with at least one pick: {len(order_final_pick):,}")
    print(f"Orders late by final picking timestamp: {late_orders:,} ({pct(late_orders, len(order_by_id)):.2f}%)")
    print(f"Hourly capacity violations: {len(capacity_violations):,}")
    print(f"Report folder: {OUTPUT_DIR}")
    print()
    print("Generated reports:")
    for name in (
        "daily_hall_load.csv",
        "hourly_capacity_check.csv",
        "capacity_violations.csv",
        "monthly_timeliness.csv",
        "order_lateness_detail.csv",
        "daily_total_load.csv",
    ):
        print(f"  - {name}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"DIAGNOSTIC FAILED: {exc}", file=sys.stderr)
        raise
