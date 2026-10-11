from pathlib import Path

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

YEAR = 2026

# Calendar rows after Dec 31 (no new orders, but the warehouse can still
# work off backlog). Needed so late-December orders can finish in January.
BUFFER_END = f"{YEAR + 1}-02-28"

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "data" / "processed"

OUTPUT_FILE = OUTPUT_DIR / "calendar.csv"


# ============================================================
# PUBLIC HOLIDAYS - BADEN-WÜRTTEMBERG 2026
# ============================================================

PUBLIC_HOLIDAYS = {
    "2026-01-01": "Neujahr",
    "2026-01-06": "Erscheinungsfest",
    "2026-04-03": "Karfreitag",
    "2026-04-06": "Ostermontag",
    "2026-05-01": "Tag der Arbeit",
    "2026-05-14": "Christi Himmelfahrt",
    "2026-05-25": "Pfingstmontag",
    "2026-06-04": "Fronleichnam",
    "2026-10-03": "Tag der Deutschen Einheit",
    "2026-11-01": "Allerheiligen",
    "2026-12-25": "Erster Weihnachtsfeiertag",
    "2026-12-26": "Zweiter Weihnachtsfeiertag",
    "2027-01-01": "Neujahr",
    "2027-01-06": "Erscheinungsfest",
}


# ============================================================
# SCHOOL HOLIDAYS - BADEN-WÜRTTEMBERG 2026
# ============================================================

SCHOOL_HOLIDAYS = [
    (
        "2026-01-01",
        "2026-01-05",
        "Weihnachtsferien",
    ),
    (
        "2026-03-30",
        "2026-04-11",
        "Osterferien",
    ),
    (
        "2026-05-26",
        "2026-06-05",
        "Pfingstferien",
    ),
    (
        "2026-07-30",
        "2026-09-12",
        "Sommerferien",
    ),
    (
        "2026-10-26",
        "2026-10-30",
        "Herbstferien",
    ),
    (
        "2026-12-23",
        "2026-12-31",
        "Weihnachtsferien",
    ),
]


# ============================================================
# SEASON
# ============================================================

def get_season(date):
    month = date.month

    if month in [12, 1, 2]:
        return "WINTER"

    if month in [3, 4, 5]:
        return "SPRING"

    if month in [6, 7, 8]:
        return "SUMMER"

    return "AUTUMN"


# ============================================================
# SCHOOL HOLIDAY LOOKUP
# ============================================================

def get_school_holiday(date):
    for start, end, name in SCHOOL_HOLIDAYS:
        start_date = pd.Timestamp(start).date()
        end_date = pd.Timestamp(end).date()

        if start_date <= date <= end_date:
            return True, name

    return False, None


# ============================================================
# DEMAND MULTIPLIER
# ============================================================

def get_demand_multiplier(
    date,
    is_weekend,
    is_public_holiday,
    is_school_holiday,
):
    """
    Calculates customer demand.

    School holidays do NOT directly reduce demand.
    They are handled separately through warehouse capacity.
    """

    # Buffer period after the simulated year: no new orders.
    if date.year > YEAR:
        return 0.0

    # No normal warehouse order activity
    # on weekends / public holidays.
    if is_weekend or is_public_holiday:
        return 0.0

    # --------------------------------------------------------
    # Base seasonal demand
    # --------------------------------------------------------

    monthly_multiplier = {
        1: 0.90,
        2: 0.95,
        3: 1.00,
        4: 1.00,
        5: 1.00,
        6: 0.95,
        7: 0.85,
        8: 0.75,
        9: 1.00,
        10: 1.05,
        11: 1.10,
        12: 0.85,
    }

    multiplier = monthly_multiplier[date.month]

    # --------------------------------------------------------
    # Christmas period
    # --------------------------------------------------------

    # Demand starts declining before Christmas.
    if date.month == 12 and date.day >= 16:
        multiplier *= 0.70

    # Strong reduction during Christmas shutdown.
    if date.month == 12 and date.day >= 23:
        multiplier *= 0.35

    # --------------------------------------------------------
    # New Year period
    # --------------------------------------------------------

    # Very low activity during the first week of January.
    if date.month == 1 and date.day <= 7:
        multiplier *= 0.35

    # Gradual recovery after the first week.
    if date.month == 1 and 8 <= date.day <= 14:
        multiplier *= 0.70

    return round(multiplier, 3)


# ============================================================
# WAREHOUSE CAPACITY MULTIPLIER
# ============================================================

def get_capacity_multiplier(
    is_weekend,
    is_public_holiday,
    is_school_holiday,
):
    """
    Calculates available warehouse capacity.

    School holidays affect workforce availability,
    not customer demand.
    """

    # No normal warehouse operation
    # on weekends / public holidays.
    if is_weekend or is_public_holiday:
        return 0.0

    multiplier = 1.0

    # Reduced workforce availability during
    # school holiday periods.
    if is_school_holiday:
        multiplier *= 0.90

    return round(multiplier, 3)


# ============================================================
# BUILD CALENDAR
# ============================================================

def build_calendar():
    dates = pd.date_range(
        start=f"{YEAR}-01-01",
        end=BUFFER_END,
        freq="D",
    )

    rows = []

    for timestamp in dates:
        date = timestamp.date()
        date_string = date.isoformat()

        weekday = timestamp.day_name()
        weekday_number = timestamp.weekday()

        # Saturday = 5
        # Sunday = 6
        is_weekend = weekday_number >= 5

        holiday_name = PUBLIC_HOLIDAYS.get(date_string)
        is_public_holiday = holiday_name is not None

        is_school_holiday, school_holiday_name = (
            get_school_holiday(date)
        )

        demand_multiplier = get_demand_multiplier(
            date=date,
            is_weekend=is_weekend,
            is_public_holiday=is_public_holiday,
            is_school_holiday=is_school_holiday,
        )

        capacity_multiplier = get_capacity_multiplier(
            is_weekend=is_weekend,
            is_public_holiday=is_public_holiday,
            is_school_holiday=is_school_holiday,
        )

        rows.append(
            {
                "date": date,
                "year": timestamp.year,
                "month": timestamp.month,
                "week": timestamp.isocalendar().week,
                "weekday": weekday,
                "is_weekend": is_weekend,
                "is_public_holiday": is_public_holiday,
                "holiday_name": holiday_name,
                "is_school_holiday": is_school_holiday,
                "school_holiday_name": school_holiday_name,
                "is_vacation_period": is_school_holiday,
                "season": get_season(date),
                "demand_multiplier": demand_multiplier,
                "warehouse_capacity_multiplier": capacity_multiplier,
                "is_buffer_period": date.year > YEAR,
            }
        )

    calendar = pd.DataFrame(rows)

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    calendar.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # --------------------------------------------------------
    # VALIDATION / SUMMARY
    # --------------------------------------------------------

    print("Warehouse Business Calendar")
    print("=" * 60)

    print(f"Year: {YEAR}")
    print(f"Rows: {len(calendar):,}")

    print(
        f"Public holidays: "
        f"{calendar['is_public_holiday'].sum():,}"
    )

    print(
        f"School holiday days: "
        f"{calendar['is_school_holiday'].sum():,}"
    )

    print()

    print("Demand multiplier:")
    print(
        calendar["demand_multiplier"].describe()
    )

    print()

    print("Warehouse capacity multiplier:")
    print(
        calendar[
            "warehouse_capacity_multiplier"
        ].describe()
    )

    print()

    print("School holiday demand/capacity sample:")

    school_holiday_sample = calendar[
        calendar["is_school_holiday"]
    ][
        [
            "date",
            "school_holiday_name",
            "demand_multiplier",
            "warehouse_capacity_multiplier",
        ]
    ].head(20)

    print(
        school_holiday_sample.to_string(
            index=False
        )
    )

    print()

    print(f"Output: {OUTPUT_FILE}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    build_calendar()