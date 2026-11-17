from pathlib import Path
import os
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

START_DATE = "2024-01-01"
END_DATE = "2027-03-31"

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(
    os.environ.get("WCT_PROCESSED_DIR", BASE_DIR / "data" / "processed")
)
OUTPUT_FILE = OUTPUT_DIR / "calendar.csv"

# This calendar covers historical reference years 2024 and 2025,
# plus January-October 2026. No dates after END_DATE are generated.


# ============================================================
# PUBLIC HOLIDAYS - BADEN-WÜRTTEMBERG
# ============================================================

PUBLIC_HOLIDAYS = {
    # 2024
    "2024-01-01": "Neujahr",
    "2024-01-06": "Heilige Drei Könige",
    "2024-03-29": "Karfreitag",
    "2024-04-01": "Ostermontag",
    "2024-05-01": "Tag der Arbeit",
    "2024-05-09": "Christi Himmelfahrt",
    "2024-05-20": "Pfingstmontag",
    "2024-05-30": "Fronleichnam",
    "2024-10-03": "Tag der Deutschen Einheit",
    "2024-11-01": "Allerheiligen",
    "2024-12-25": "Erster Weihnachtsfeiertag",
    "2024-12-26": "Zweiter Weihnachtsfeiertag",

    # 2025
    "2025-01-01": "Neujahr",
    "2025-01-06": "Heilige Drei Könige",
    "2025-04-18": "Karfreitag",
    "2025-04-21": "Ostermontag",
    "2025-05-01": "Tag der Arbeit",
    "2025-05-29": "Christi Himmelfahrt",
    "2025-06-09": "Pfingstmontag",
    "2025-06-19": "Fronleichnam",
    "2025-10-03": "Tag der Deutschen Einheit",
    "2025-11-01": "Allerheiligen",
    "2025-12-25": "Erster Weihnachtsfeiertag",
    "2025-12-26": "Zweiter Weihnachtsfeiertag",

    # 2026 (only holidays up to the simulation end date are included
    # in calendar.csv; later dates are harmless dictionary entries)
    "2026-01-01": "Neujahr",
    "2026-01-06": "Heilige Drei Könige",
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
}


# ============================================================
# SCHOOL HOLIDAYS - BADEN-WÜRTTEMBERG
# Dates are statewide school holiday periods. Local movable days
# are not included because they vary by school/municipality.
# ============================================================

SCHOOL_HOLIDAYS = [
    # Christmas holidays 2023/2024 (only Jan 1-5 fall in this calendar)
    ("2023-12-23", "2024-01-05", "Weihnachtsferien"),

    # School year 2023/2024
    ("2024-03-23", "2024-04-05", "Osterferien"),
    ("2024-05-21", "2024-05-31", "Pfingstferien"),
    ("2024-07-25", "2024-09-07", "Sommerferien"),
    ("2024-10-28", "2024-10-30", "Herbstferien"),
    ("2024-12-23", "2025-01-04", "Weihnachtsferien"),

    # School year 2024/2025
    ("2025-04-14", "2025-04-26", "Osterferien"),
    ("2025-06-10", "2025-06-20", "Pfingstferien"),
    ("2025-07-31", "2025-09-13", "Sommerferien"),
    ("2025-10-27", "2025-10-30", "Herbstferien"),
    ("2025-12-22", "2026-01-05", "Weihnachtsferien"),

    # School year 2025/2026
    ("2026-03-30", "2026-04-11", "Osterferien"),
    ("2026-05-26", "2026-06-05", "Pfingstferien"),
    ("2026-07-30", "2026-09-12", "Sommerferien"),
    ("2026-10-26", "2026-10-30", "Herbstferien"),
]

# Additional school-free days in Baden-Württemberg.
# These are not part of the multi-day school holiday periods above.
# Reformation Day (31 October) is school-free in these years.
SCHOOL_FREE_DAYS = {
    "2024-10-31": "Reformationsfest (unterrichtsfrei)",
    "2025-10-31": "Reformationsfest (unterrichtsfrei)",
    "2026-10-31": "Reformationsfest (unterrichtsfrei)",
}


# ============================================================
# SEASON
# ============================================================

def get_season(date):
    if date.month in (12, 1, 2):
        return "WINTER"
    if date.month in (3, 4, 5):
        return "SPRING"
    if date.month in (6, 7, 8):
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

def get_demand_multiplier(date, is_weekend, is_public_holiday, is_school_holiday):
    """
    Estimates customer demand by month and calendar conditions.
    School holidays do not directly reduce demand; their effect
    is represented separately in warehouse capacity.
    """
    if is_weekend or is_public_holiday:
        return 0.0

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

    # Christmas slowdown
    if date.month == 12 and date.day >= 16:
        multiplier *= 0.70
    if date.month == 12 and date.day >= 23:
        multiplier *= 0.35

    # New Year slowdown
    if date.month == 1 and date.day <= 7:
        multiplier *= 0.35
    elif date.month == 1 and date.day <= 14:
        multiplier *= 0.70

    return round(multiplier, 3)


# ============================================================
# WAREHOUSE CAPACITY MULTIPLIER
# ============================================================

def get_capacity_multiplier(
    is_weekend,
    is_public_holiday,
    is_school_holiday,
    is_school_free_day,
):
    """
    Estimates available warehouse capacity.
    School holiday periods and additional school-free days are modeled
    as a small workforce-availability reduction. This is a simulation
    assumption, not a claim that the warehouse itself is closed.
    """
    if is_weekend or is_public_holiday:
        return 0.0

    multiplier = 0.90 if (is_school_holiday or is_school_free_day) else 1.0
    return round(multiplier, 3)


# ============================================================
# BUILD CALENDAR
# ============================================================

def build_calendar():
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    rows = []

    for timestamp in dates:
        date = timestamp.date()
        date_string = date.isoformat()
        weekday = timestamp.day_name()
        weekday_number = timestamp.weekday()
        is_weekend = weekday_number >= 5

        holiday_name = PUBLIC_HOLIDAYS.get(date_string)
        is_public_holiday = holiday_name is not None

        is_school_holiday, school_holiday_name = get_school_holiday(date)
        school_free_day_name = SCHOOL_FREE_DAYS.get(date_string)
        is_school_free_day = school_free_day_name is not None

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
            is_school_free_day=is_school_free_day,
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
                "is_school_free_day": is_school_free_day,
                "school_free_day_name": school_free_day_name,
                "is_vacation_period": is_school_holiday or is_school_free_day,
                "season": get_season(date),
                "demand_multiplier": demand_multiplier,
                "warehouse_capacity_multiplier": capacity_multiplier,
                "is_buffer_period": False,
            }
        )

    calendar = pd.DataFrame(rows)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------
    expected_dates = pd.date_range(start=START_DATE, end=END_DATE, freq="D").date

    if calendar["date"].duplicated().any():
        raise ValueError("Calendar contains duplicate dates.")
    if list(calendar["date"]) != list(expected_dates):
        raise ValueError("Calendar dates are not continuous or do not match the configured range.")

    for column in ("demand_multiplier", "warehouse_capacity_multiplier"):
        if (
            calendar[column].isna().any()
            or not calendar[column].between(0, 1.5).all()
        ):
            raise ValueError(f"Invalid values found in {column}.")

    closed_days = calendar["is_weekend"] | calendar["is_public_holiday"]
    if not calendar.loc[closed_days, "demand_multiplier"].eq(0).all():
        raise ValueError("Demand must be zero on weekends and public holidays.")
    if not calendar.loc[closed_days, "warehouse_capacity_multiplier"].eq(0).all():
        raise ValueError("Warehouse capacity must be zero on weekends and public holidays.")

    if calendar["is_buffer_period"].any():
        raise ValueError("No buffer dates should be generated for this configured period.")

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    calendar.to_csv(OUTPUT_FILE, index=False, date_format="%Y-%m-%d")

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    print("Warehouse Business Calendar - Baden-Württemberg")
    print("=" * 60)
    print(f"Date range: {calendar['date'].min()} to {calendar['date'].max()}")
    print(f"Rows: {len(calendar):,}")
    print(f"Years covered: {', '.join(map(str, sorted(calendar['year'].unique())))}")
    print("Validation: PASSED")
    print(f"Public holiday dates in range: {calendar['is_public_holiday'].sum():,}")
    print(f"School holiday days in range: {calendar['is_school_holiday'].sum():,}")
    print(f"Additional school-free days in range: {calendar['is_school_free_day'].sum():,}")
    print()

    print("Additional school-free days:")
    free_day_sample = calendar.loc[
        calendar["is_school_free_day"],
        ["date", "school_free_day_name", "is_weekend", "warehouse_capacity_multiplier"],
    ]
    print(free_day_sample.to_string(index=False))
    print()

    print("Demand multiplier:")
    print(calendar["demand_multiplier"].describe())
    print()

    print("Warehouse capacity multiplier:")
    print(calendar["warehouse_capacity_multiplier"].describe())
    print()

    print("School holiday sample:")
    sample = calendar.loc[
        calendar["is_school_holiday"],
        [
            "date",
            "school_holiday_name",
            "demand_multiplier",
            "warehouse_capacity_multiplier",
        ],
    ].head(20)
    print(sample.to_string(index=False))
    print()
    print(f"Output: {OUTPUT_FILE}")

    return calendar


if __name__ == "__main__":
    build_calendar()
