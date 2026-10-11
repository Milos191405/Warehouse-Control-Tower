"""
Warehouse Control Tower - hourly hall capacity (queue)

Put next to working_time.py (src/generators/).

Each hall can process a limited number of pick lines per working hour.
When more picks want the same hour, the extra ones wait for the next
free hour (next shift, next day, after weekends and holidays). This
creates a realistic backlog in busy periods, and late deliveries
that are caused by capacity instead of a random number.

Capacity per day = HALL_PICKS_PER_HOUR * warehouse_capacity_multiplier
(from calendar.csv, so school holidays reduce it).
"""

import random
from datetime import datetime, timedelta

from working_time import next_working_datetime, OPEN_TIME, CLOSE_TIME

# Calibrated on the current dataset (~138k pick lines): about 1.6x the
# average load per working hour (Hall 1 ~26, Hall 2 ~6, Hall 3 ~2 picks).
# Lower the numbers for more backlog, raise them for less.
HALL_PICKS_PER_HOUR = {
    1: 42,
    2: 10,
    3: 4,
}


class HourlyCapacity:

    def __init__(self, capacity_by_date, picks_per_hour=None):
        self.capacity_by_date = capacity_by_date
        self.picks_per_hour = picks_per_hour or HALL_PICKS_PER_HOUR
        self.used = {}

    def reserve(self, hall_id, earliest):
        """
        Return the first working moment >= earliest at which the hall
        still has free capacity, and book one pick there.
        """
        hall = int(hall_id)
        t = next_working_datetime(earliest, self.capacity_by_date)

        while True:
            factor = self.capacity_by_date.get(t.date(), 0.0)
            limit = max(1, int(self.picks_per_hour[hall] * factor))
            key = (hall, t.date(), t.hour)

            if self.used.get(key, 0) < limit:
                self.used[key] = self.used.get(key, 0) + 1
                return t

            next_hour = (
                datetime(t.year, t.month, t.day, t.hour)
                + timedelta(hours=1)
            )
            t = next_working_datetime(
                next_hour, self.capacity_by_date
            )
            # Spread the backlog inside the hour instead of
            # putting everything at hh:00:00.
            if t.minute == 0 and t.second == 0:
                t += timedelta(seconds=random.randint(0, 3599))
                if t.time() >= CLOSE_TIME:
                    t = next_working_datetime(
                        t, self.capacity_by_date
                    )


def apply_hall_capacity(picking_records, capacity_by_date):
    """
    Phase 2 of picking generation.

    Call after every record already has a 'pick_datetime' (your
    existing per-order timeline). Reschedules all picks globally in
    time order through the hall capacity queue and keeps the picks of
    one order strictly increasing. Modifies the records in place.
    """
    queue = HourlyCapacity(capacity_by_date)
    last_by_order = {}

    ordered = sorted(
        picking_records,
        key=lambda r: (r["pick_datetime"], r["picking_id"]),
    )

    for record in ordered:
        wanted = datetime.fromisoformat(record["pick_datetime"])
        previous = last_by_order.get(record["order_id"])

        if previous is not None and wanted <= previous:
            wanted = previous + timedelta(seconds=1)

        scheduled = queue.reserve(record["hall_id"], wanted)

        if previous is not None and scheduled <= previous:
            scheduled = previous + timedelta(seconds=1)

        last_by_order[record["order_id"]] = scheduled
        record["pick_datetime"] = scheduled.isoformat(timespec="seconds")

    return picking_records