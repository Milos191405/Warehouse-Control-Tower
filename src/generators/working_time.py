"""
Warehouse Control Tower - Working Time Helpers


Responsibilities:
    - Load warehouse capacity from calendar.csv
    - Define warehouse shifts
    - Move timestamps into valid working windows
    - Keep tasks within working hours
    - Calculate working-day deadlines
    - Generate realistic customer order timestamps

Note:
    Customer orders may arrive outside warehouse working hours.
    Warehouse operations must follow the configured shifts.
"""

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALENDAR_FILE = PROJECT_ROOT / "data" / "processed" / "calendar.csv"

SHIFTS = {
    "EARLY": (time(6, 0), time(14, 0)),
    "LATE": (time(14, 0), time(22, 0)),
}

OPEN_TIME = min(start for start, _ in SHIFTS.values())
CLOSE_TIME = max(end for _, end in SHIFTS.values())

OPENING_JITTER_MINUTES = 20
MIN_EVENT_GAP_SECONDS = 30
MAX_EVENT_GAP_SECONDS = 120
DEFAULT_MAX_SEARCH_DAYS = 60

ORDER_HOUR_WEIGHTS = {
    0: 1,
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 2,
    6: 5,
    7: 9,
    8: 12,
    9: 12,
    10: 11,
    11: 10,
    12: 7,
    13: 9,
    14: 10,
    15: 9,
    16: 7,
    17: 5,
    18: 3,
    19: 2,
    20: 2,
    21: 1,
    22: 1,
    23: 1,
}


# ============================================================
# CALENDAR
# ============================================================

def load_capacity_by_date(calendar_file=CALENDAR_FILE):
    """
    Load daily warehouse capacity.

    Returns:
        dict[date, float]

    A capacity multiplier greater than zero means the warehouse
    can operate on that date.
    """
    calendar_path = Path(calendar_file)

    if not calendar_path.exists():
        raise FileNotFoundError(
            f"Calendar file not found: {calendar_path}. "
            "Run business_calendar.py first."
        )

    capacity_by_date = {}

    with calendar_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)

        required_columns = {
            "date",
            "warehouse_capacity_multiplier",
        }

        missing_columns = required_columns - set(
            reader.fieldnames or []
        )

        if missing_columns:
            raise ValueError(
                "calendar.csv is missing required columns: "
                f"{sorted(missing_columns)}"
            )

        for row in reader:
            day = date.fromisoformat(row["date"])
            capacity = float(
                row["warehouse_capacity_multiplier"]
            )

            if capacity < 0:
                raise ValueError(
                    f"Negative warehouse capacity on {day}: "
                    f"{capacity}"
                )

            if day in capacity_by_date:
                raise ValueError(
                    f"Duplicate calendar date: {day}"
                )

            capacity_by_date[day] = capacity

    if not capacity_by_date:
        raise ValueError("calendar.csv contains no calendar rows.")

    return capacity_by_date


def is_working_day(day, capacity_by_date):
    """Return True if the warehouse has positive capacity that day."""
    return capacity_by_date.get(day, 0.0) > 0


def validate_calendar_coverage(
    start_date,
    end_date,
    capacity_by_date,
):
    """Ensure every date in the requested range exists in the calendar."""
    if end_date < start_date:
        raise ValueError(
            f"Invalid calendar range: {start_date} to {end_date}"
        )

    current = start_date

    while current <= end_date:
        if current not in capacity_by_date:
            raise ValueError(
                f"Calendar does not cover {current}. "
                "Extend business_calendar.py and regenerate calendar.csv."
            )

        current += timedelta(days=1)


# ============================================================
# SHIFT HELPERS
# ============================================================

def is_open(dt):
    """Return True when dt falls inside one of the configured shifts."""
    current_time = dt.time()

    return any(
        start <= current_time < end
        for start, end in SHIFTS.values()
    )


def shift_name(dt):
    """Return EARLY, LATE, or OFF for a timestamp."""
    current_time = dt.time()

    for name, (start, end) in SHIFTS.items():
        if start <= current_time < end:
            return name

    return "OFF"


def _opening(day, start=OPEN_TIME):
    """Return a shift opening timestamp with a small random jitter."""
    jitter = random.randint(
        0,
        OPENING_JITTER_MINUTES * 60,
    )

    return datetime.combine(day, start) + timedelta(
        seconds=jitter
    )


def _next_shift_start(current_time):
    """Find the next configured shift start later on the same day."""
    later_starts = sorted(
        start
        for start, _ in SHIFTS.values()
        if start > current_time
    )

    return later_starts[0] if later_starts else None


# ============================================================
# WORKING TIMESTAMPS
# ============================================================

def next_working_datetime(
    dt,
    capacity_by_date,
    max_days=DEFAULT_MAX_SEARCH_DAYS,
):
    """
    Return the earliest valid warehouse working timestamp at or after dt.

    If dt is during a shift on an open day, it is returned unchanged.
    If dt is before opening, the first shift opening is returned.
    If dt is after closing or on a closed day, the next working
    day's opening is returned.
    """
    if max_days < 0:
        raise ValueError("max_days cannot be negative.")

    day = dt.date()

    for offset in range(max_days + 1):
        candidate_day = day + timedelta(days=offset)

        if not is_working_day(
            candidate_day,
            capacity_by_date,
        ):
            continue

        if offset == 0:
            if is_open(dt):
                return dt

            if dt.time() < OPEN_TIME:
                return _opening(candidate_day)

            next_start = _next_shift_start(dt.time())

            if next_start is not None:
                return _opening(candidate_day, next_start)

        else:
            return _opening(candidate_day)

    raise ValueError(
        f"No working timestamp found on or after {dt} "
        f"within {max_days} days. Check calendar.csv coverage."
    )


def add_working_duration(
    start_dt,
    duration,
    capacity_by_date,
    max_days=DEFAULT_MAX_SEARCH_DAYS,
):
    """
    Add elapsed working time while respecting shift boundaries.

    Closed periods, nights, weekends, and holidays do not consume
    the supplied working duration.

    Example:
        Starting at 13:00 with a two-hour task:
        - one hour is used until 14:00;
        - the remaining hour continues at 14:00 if the next shift
          starts immediately, as it does in the default configuration.

    A duration of zero returns the next valid working timestamp.
    """
    if duration < timedelta(0):
        raise ValueError("duration cannot be negative.")

    current = next_working_datetime(
        start_dt,
        capacity_by_date,
        max_days=max_days,
    )

    remaining = duration

    if remaining == timedelta(0):
        return current

    while remaining > timedelta(0):
        day = current.date()

        active_shift = next(
            (
                (start, end)
                for start, end in SHIFTS.values()
                if start <= current.time() < end
            ),
            None,
        )

        if active_shift is None:
            current = next_working_datetime(
                current,
                capacity_by_date,
                max_days=max_days,
            )
            continue

        _, shift_end = active_shift

        available = datetime.combine(day, shift_end) - current

        if remaining <= available:
            return current + remaining

        remaining -= available

        # Move to the next valid working timestamp.
        current = next_working_datetime(
            datetime.combine(day, shift_end),
            capacity_by_date,
            max_days=max_days,
        )

    return current


def snap_timestamps(timestamps, capacity_by_date):
    """
    Snap timestamps to working windows and keep them strictly increasing.

    The input should already be sorted chronologically.
    """
    result = []
    previous = None

    for timestamp in timestamps:
        snapped = next_working_datetime(
            timestamp,
            capacity_by_date,
        )

        if previous is not None and snapped <= previous:
            gap = random.randint(
                MIN_EVENT_GAP_SECONDS,
                MAX_EVENT_GAP_SECONDS,
            )

            snapped = next_working_datetime(
                previous + timedelta(seconds=gap),
                capacity_by_date,
            )

        result.append(snapped)
        previous = snapped

    return result


# ============================================================
# DEADLINES
# ============================================================

def add_working_days(
    dt,
    days,
    capacity_by_date,
    max_days=DEFAULT_MAX_SEARCH_DAYS,
):
    """
    Return the same local time after the requested number of working days.

    The starting date is not counted as one of the added days.

    This calculates a deadline; it does not force the deadline itself
    to fall inside a warehouse shift.
    """
    if not isinstance(days, int) or days < 0:
        raise ValueError("days must be a non-negative integer.")

    if days == 0:
        return dt

    current_day = dt.date()
    remaining = days
    steps = 0

    while remaining > 0:
        current_day += timedelta(days=1)
        steps += 1

        if steps > max_days:
            raise ValueError(
                f"Could not add {days} working days to {dt}. "
                "Check calendar coverage or extend BUFFER_END."
            )

        if current_day not in capacity_by_date:
            raise ValueError(
                f"Calendar does not cover {current_day}. "
                "Extend business_calendar.py and regenerate calendar.csv."
            )

        if is_working_day(current_day, capacity_by_date):
            remaining -= 1

    return datetime.combine(current_day, dt.time())


# ============================================================
# CUSTOMER ORDER TIMES
# ============================================================

def random_order_time_of_day():
    """
    Generate a customer order time.

    Customer orders may arrive outside warehouse working hours.
    Warehouse processing timestamps must be normalized separately.
    """
    hour = random.choices(
        list(ORDER_HOUR_WEIGHTS),
        weights=list(ORDER_HOUR_WEIGHTS.values()),
        k=1,
    )[0]

    return timedelta(
        hours=hour,
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )