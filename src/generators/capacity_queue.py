import random
from datetime import datetime, timedelta

from working_time import OPEN_TIME, next_working_datetime


# Average number of completed picking operations per hour for each hall.
# These are operation-count capacities, not per-worker rates.
HALL_PICKS_PER_HOUR = {
    1: 42,
    2: 10,
    3: 4,
}

PRIORITY_RANK = {
    "URGENT": 0,
    "HIGH": 1,
    "NORMAL": 2,
    "LOW": 3,
}


class HourlyCapacity:
    def __init__(self, capacity_by_date, picks_per_hour=None):
        self.capacity_by_date = capacity_by_date
        self.picks_per_hour = dict(
            HALL_PICKS_PER_HOUR if picks_per_hour is None else picks_per_hour
        )
        self.used = {}

        # Cache the next hour with capacity separately for each hall.
        # Without this cursor, every pick may rescan the same full hours,
        # making large queues increasingly slow.
        self.next_candidate_by_hall = {}

        if not self.picks_per_hour:
            raise ValueError("picks_per_hour cannot be empty.")

        normalized = {}
        for hall, capacity in self.picks_per_hour.items():
            try:
                hall_id = int(hall)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid hall id: {hall!r}") from exc
            if hall_id <= 0:
                raise ValueError(f"Invalid hall id: {hall}")
            if (
                not isinstance(capacity, (int, float))
                or isinstance(capacity, bool)
                or capacity <= 0
            ):
                raise ValueError(
                    f"Capacity for hall {hall} must be a positive number."
                )
            if hall_id in normalized:
                raise ValueError(f"Duplicate hall id after normalization: {hall_id}")
            normalized[hall_id] = float(capacity)
        self.picks_per_hour = normalized

    def _next_hour(self, timestamp):
        next_hour = datetime(
            timestamp.year, timestamp.month, timestamp.day, timestamp.hour
        ) + timedelta(hours=1)
        candidate = next_working_datetime(next_hour, self.capacity_by_date)

        # Add jitter only when the candidate is exactly at the start of an hour.
        # Normalize again so jitter cannot land inside a break or outside a shift.
        if candidate.minute == 0 and candidate.second == 0:
            candidate += timedelta(seconds=random.randint(0, 3599))
            candidate = next_working_datetime(candidate, self.capacity_by_date)
        return candidate

    def reserve(self, hall_id, earliest):
        try:
            hall = int(hall_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid hall id: {hall_id!r}") from exc
        if hall not in self.picks_per_hour:
            raise ValueError(f"No hourly capacity configured for hall {hall}.")
        if not isinstance(earliest, datetime):
            raise TypeError("earliest must be a datetime.")

        timestamp = next_working_datetime(earliest, self.capacity_by_date)

        # Key optimization: if this hall already has a later candidate hour
        # because earlier hours filled up, never scan those full hours again.
        cached_candidate = self.next_candidate_by_hall.get(hall)
        if cached_candidate is not None and cached_candidate > timestamp:
            timestamp = cached_candidate

        while True:
            timestamp = next_working_datetime(timestamp, self.capacity_by_date)
            factor = float(self.capacity_by_date.get(timestamp.date(), 0.0))
            if not 0.0 <= factor <= 1.0:
                raise ValueError(
                    f"Invalid capacity multiplier on {timestamp.date()}: {factor}"
                )

            if factor == 0:
                timestamp = next_working_datetime(
                    datetime.combine(timestamp.date() + timedelta(days=1), OPEN_TIME),
                    self.capacity_by_date,
                )
                self.next_candidate_by_hall[hall] = timestamp
                continue

            # If a reduced capacity rounds down to zero, this hour has no slots.
            limit = int(self.picks_per_hour[hall] * factor)
            if limit < 1:
                timestamp = self._next_hour(timestamp)
                self.next_candidate_by_hall[hall] = timestamp
                continue

            key = (hall, timestamp.date(), timestamp.hour)
            used = self.used.get(key, 0)

            if used < limit:
                used += 1
                self.used[key] = used

                # Once an hour is full, cache the next candidate immediately.
                # The next reservation for this hall can start there directly.
                if used >= limit:
                    self.next_candidate_by_hall[hall] = self._next_hour(timestamp)
                else:
                    self.next_candidate_by_hall[hall] = timestamp

                return timestamp

            timestamp = self._next_hour(timestamp)
            self.next_candidate_by_hall[hall] = timestamp


def apply_hall_capacity(picking_records, capacity_by_date, order_metadata=None):
    """Schedule picks within shift/calendar constraints and hall capacities.

    Work is grouped by arrival hour. Within that hour, earlier delivery deadlines
    take precedence, followed by URGENT/HIGH/NORMAL/LOW priority. Original pick
    time and picking ID provide stable ordering within equal-priority groups.
    """
    queue = HourlyCapacity(capacity_by_date)
    last_by_order = {}
    order_metadata = order_metadata or {}

    def scheduling_key(record):
        wanted = datetime.fromisoformat(record["pick_datetime"])
        metadata = order_metadata.get(record["order_id"], {})
        deadline = metadata.get("deadline")
        priority = str(metadata.get("priority", "NORMAL")).strip().upper()
        priority_rank = PRIORITY_RANK.get(priority, PRIORITY_RANK["NORMAL"])
        arrival_hour = wanted.replace(minute=0, second=0, microsecond=0)
        if deadline is None:
            deadline = wanted
        elif isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)

        return (
            arrival_hour,
            deadline,
            priority_rank,
            wanted,
            record["picking_id"],
        )

    ordered = sorted(picking_records, key=scheduling_key)

    for record in ordered:
        wanted = datetime.fromisoformat(record["pick_datetime"])
        previous = last_by_order.get(record["order_id"])

        if previous is not None and wanted <= previous:
            wanted = previous + timedelta(seconds=1)

        scheduled = queue.reserve(record["hall_id"], wanted)

        if previous is not None and scheduled <= previous:
            raise RuntimeError(
                f"Capacity scheduling broke chronological order for "
                f"order {record['order_id']}."
            )

        last_by_order[record["order_id"]] = scheduled
        record["pick_datetime"] = scheduled.isoformat(timespec="seconds")

    return picking_records
