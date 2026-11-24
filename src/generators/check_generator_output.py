"""
Warehouse Control Tower - cross-file checks for the generated data

Runs as the last step of run_pipeline.py (or on its own):

    python src/pipeline/check_generator_output.py

Reads data/processed/*.csv (or $WCT_PROCESSED_DIR) and checks that the files agree with each
other. It changes nothing. Exit code 0 = all checks passed.

Location: src/pipeline/check_generator_output.py
"""

import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = Path(
    os.environ.get("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed")
)

sys.path.insert(0, str(PROJECT_ROOT / "src" / "generators"))

import working_time as wt  # noqa: E402
from capacity_queue import HALL_PICKS_PER_HOUR  # noqa: E402


RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


def read(name, **kwargs):
    return pd.read_csv(PROCESSED / f"{name}.csv", low_memory=False, **kwargs)


def minute_windows(windows):
    return [
        (a.hour * 60 + a.minute, b.hour * 60 + b.minute)
        for a, b in windows
    ]


def in_windows(series, windows):
    minutes = series.dt.hour * 60 + series.dt.minute
    mask = pd.Series(False, index=series.index)

    for start, end in minute_windows(windows):
        mask |= (minutes >= start) & (minutes < end)

    return mask


def in_shift(series):
    """True where the time lies inside a shift and NOT inside a break."""
    breaks = [
        window
        for windows in getattr(wt, "SHIFT_BREAKS", {}).values()
        for window in windows
    ]

    return in_windows(series, list(wt.SHIFTS.values())) & ~in_windows(
        series, breaks
    )


def main():
    orders = read("orders")
    items = read("order_items")
    inventory = read("inventory")
    picking = read("picking")
    packing = read("packing")
    shipping = read("shipping")
    calendar = read("calendar")

    open_days = set(
        pd.to_datetime(
            calendar.loc[
                calendar["warehouse_capacity_multiplier"] > 0, "date"
            ]
        ).dt.date
    )
    capacity = dict(
        zip(
            pd.to_datetime(calendar["date"]).dt.date,
            calendar["warehouse_capacity_multiplier"],
        )
    )

    def on_open_day(series):
        return series.dt.date.isin(open_days)

    # ---------------- counts and keys ----------------
    check("orders: unique order_id", orders.order_id.is_unique)
    check("order_items: unique order_item_id", items.order_item_id.is_unique)
    check("packing: one row per order",
          packing.order_id.is_unique and len(packing) == len(orders))
    check("shipping: one row per order",
          shipping.order_id.is_unique and len(shipping) == len(orders))
    check("orders: all DELIVERED", (orders.order_status == "DELIVERED").all())

    # ---------------- order items are finalized ----------------
    check("order_items: picked = packed = shipped = requested",
          ((items.picked_quantity == items.requested_quantity)
           & (items.packed_quantity == items.requested_quantity)
           & (items.shipped_quantity == items.requested_quantity)).all())
    check("order_items: all DELIVERED", (items.item_status == "DELIVERED").all())

    # ---------------- foreign keys ----------------
    check("items -> orders", items.order_id.isin(orders.order_id).all())
    check("every order has items", orders.order_id.isin(items.order_id).all())
    check("picking -> items", picking.order_item_id.isin(items.order_item_id).all())
    pick_item_order = picking.merge(
        items[["order_item_id", "order_id"]],
        on="order_item_id", suffixes=("", "_item"),
    )
    check("picking.order_id matches its item",
          (pick_item_order.order_id == pick_item_order.order_id_item).all())
    check("packing -> orders", packing.order_id.isin(orders.order_id).all())
    check("shipping -> packing", shipping.packing_id.isin(packing.packing_id).all())
    check("shipping.order_id matches packing",
          (shipping.merge(packing[["packing_id", "order_id"]],
                          on="packing_id", suffixes=("", "_p"))
           .eval("order_id == order_id_p")).all())

    # ---------------- quantities ----------------
    picked = picking.groupby("order_item_id").picked_quantity.sum()
    requested = items.set_index("order_item_id").requested_quantity
    check("every item picked exactly as requested",
          (picked.reindex(requested.index).fillna(0) == requested).all())
    stock = inventory.groupby("product_id").quantity.sum()
    over = items.requested_quantity > items.product_id.map(stock).fillna(0)
    check("no item requests more than total stock", not over.any(),
          f"{int(over.sum())} items")

    # ---------------- chronology per order ----------------
    picking["t"] = pd.to_datetime(picking.pick_datetime)
    first_pick = picking.groupby("order_id").t.min()
    last_pick = picking.groupby("order_id").t.max()

    o = orders.set_index("order_id")
    p = packing.set_index("order_id")
    s = shipping.set_index("order_id")
    t_order = pd.to_datetime(o.order_datetime)
    t_pack_start = pd.to_datetime(p.packing_started_at)
    t_pack_end = pd.to_datetime(p.packing_completed_at)
    t_ship = pd.to_datetime(s.shipped_at)
    t_deliv = pd.to_datetime(s.delivered_at)
    idx = o.index

    check("order < first pick", (t_order > first_pick.reindex(idx)).sum() == 0)
    check("last pick <= packing start",
          (last_pick.reindex(idx) <= t_pack_start.reindex(idx)).all())
    check("packing start < packing end",
          (t_pack_start.reindex(idx) < t_pack_end.reindex(idx)).all())
    check("packing end < shipped",
          (t_pack_end.reindex(idx) < t_ship.reindex(idx)).all())
    check("shipped < delivered",
          (t_ship.reindex(idx) < t_deliv.reindex(idx)).all())
    check("shipping repeats packing_completed_at",
          (pd.to_datetime(s.packing_completed_at).reindex(idx)
           == t_pack_end.reindex(idx)).all())
    check("shipping repeats the requested delivery",
          (pd.to_datetime(s.requested_delivery_datetime).reindex(idx)
           == pd.to_datetime(o.requested_delivery_datetime)).all())

    # ---------------- working time ----------------
    check("orders only on order days (no weekend / holiday)",
          on_open_day(t_order).all())
    check("picks on open days", on_open_day(picking.t).all())
    check("picks inside shifts", in_shift(picking.t).all())
    check("packing starts on open days", on_open_day(t_pack_start).all())
    check("packing starts inside shifts", in_shift(t_pack_start).all())
    check("shipped on open days", on_open_day(t_ship).all())
    road = s.transport_mode == "ROAD"
    check("road deliveries on open days", on_open_day(t_deliv[road]).all())
    check("road deliveries 08:00-18:00",
          ((t_deliv[road].dt.hour >= 8) & (t_deliv[road].dt.hour < 18)).all())

    # ---------------- packing stations: one order at a time ----------------
    pk_sorted = packing.assign(
        s=t_pack_start.reindex(packing.order_id).values,
        e=t_pack_end.reindex(packing.order_id).values,
    ).sort_values(["packing_station", "s"])
    prev_end = pk_sorted.groupby("packing_station").e.shift()
    overlaps = int((pk_sorted.s < prev_end).sum())
    check("packing: no overlapping jobs on a station", overlaps == 0,
          f"{overlaps:,} overlaps" if overlaps else "")

    # ---------------- capacity ----------------
    hall_hours = picking.groupby(
        ["hall_id", picking.t.dt.date, picking.t.dt.hour]
    ).size()
    limits = [
        max(1, int(HALL_PICKS_PER_HOUR[int(h)] * capacity[d]))
        for (h, d, _) in hall_hours.index
    ]
    check("hall capacity per hour respected",
          (hall_hours.values <= limits).all())

    # ---------------- flags and stock ----------------
    expected = t_deliv.reindex(idx) <= pd.to_datetime(o.requested_delivery_datetime)
    flag = s.on_time_delivery.astype(str).str.upper().eq("TRUE").reindex(idx)
    check("on_time_delivery flag matches the timestamps", (flag == expected).all())
    check("packing container exists in picking",
          packing.container_id.isin(picking.container_id).all())

    # ---------------- report ----------------
    print()
    print("Warehouse Control Tower - generator output checks")
    print("=================================================")

    failed = 0

    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
        failed += not ok

    print()
    print("Information (not pass/fail)")
    print("---------------------------")
    print(f"Orders:               {len(orders):,}")
    print(f"Order items:          {len(items):,}")
    print(f"Pick lines:           {len(picking):,}")
    print(f"Packing records:      {len(packing):,}")
    print(f"Shipments:            {len(shipping):,}")
    print(f"Picked after deadline:  {int((last_pick.reindex(idx) >= pd.to_datetime(o.requested_delivery_datetime)).sum()):,}")
    print(f"Packed after deadline:  {int((t_pack_end.reindex(idx) >= pd.to_datetime(o.requested_delivery_datetime)).sum()):,}")
    print(f"Late deliveries:        {int((~expected).sum()):,} "
          f"({(~expected).mean() * 100:.2f}%)")
    print(f"On-time (road only):    {expected[road.reindex(idx)].mean() * 100:.2f}%")

    print()
    print("ALL CHECKS PASSED" if failed == 0 else f"{failed} CHECK(S) FAILED")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
