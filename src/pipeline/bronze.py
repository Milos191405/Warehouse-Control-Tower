from pathlib import Path
import random
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"

DATASETS = [
    "product_master.csv",
    "locations.csv",
    "inventory.csv",
    "orders.csv",
    "order_items.csv",
    "picking.csv",
    "packing.csv",
    "shipping.csv",
]

SEED = 20261004
WHITESPACE_RATE = 0.01
MISSING_RATE = 0.005
CATEGORY_RATE = 0.005
DUPLICATE_RATE = 0.005

KEY_COLUMNS = {
    "id", "product_id", "location_id", "inventory_id",
    "order_id", "order_item_id", "picking_id", "packing_id",
    "shipment_id", "container_id", "customer_id",
    "article_number", "ean",
}


def is_key_column(column):
    name = column.strip().lower()
    return name in KEY_COLUMNS or name.endswith("_id")


def is_string_column(series):
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def add_whitespace(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    return f" {value} " if value else value


def add_category_issue(value):
    if pd.isna(value):
        return value
    value = str(value).strip()
    if not value:
        return value
    if value.isupper():
        return value.lower()
    if value.islower():
        return value.upper()
    return f" {value} "


def inject_issues(df, rng):
    result = df.copy()
    counts = {
        "whitespace_issues": 0,
        "missing_values": 0,
        "category_issues": 0,
        "duplicate_rows": 0,
    }

    string_cols = [
        c for c in result.columns
        if is_string_column(result[c]) and not is_key_column(c)
    ]

    for col in string_cols:
        rows = result.index.tolist()
        n = max(1, int(len(rows) * WHITESPACE_RATE))
        for idx in rng.sample(rows, min(n, len(rows))):
            old = result.at[idx, col]
            new = add_whitespace(old)
            if new != old:
                result.at[idx, col] = new
                counts["whitespace_issues"] += 1

    preferred_missing = [
        "short_description", "long_description", "type",
        "delivery_priority", "delivery_status", "shipping_method",
        "transport_mode", "carrier", "destination_country",
        "destination_region", "packing_type", "packing_status",
        "picking_status", "picking_method", "storage_type",
        "quantity", "requested_quantity", "picked_quantity",
        "total_weight_kg", "requested_delivery_datetime",
        "order_datetime",
    ]
    missing_cols = [
        c for c in preferred_missing
        if c in result.columns and not is_key_column(c)
    ]

    if not missing_cols:
        missing_cols = [
            c for c in result.columns
            if not is_key_column(c)
        ][:3]

    for col in missing_cols:
        rows = result.index[result[col].notna()].tolist()
        if not rows:
            continue
        n = max(1, int(len(rows) * MISSING_RATE))
        for idx in rng.sample(rows, min(n, len(rows))):
            result.at[idx, col] = pd.NA
            counts["missing_values"] += 1

    category_cols = [
        c for c in [
            "type", "delivery_priority", "delivery_status",
            "shipping_method", "transport_mode", "carrier",
            "destination_country", "destination_region",
            "packing_type", "packing_status", "picking_status",
            "picking_method", "storage_type", "container_type",
            "base_unit", "pack_type_1", "pack_type_2", "pack_type_3",
        ]
        if c in result.columns and not is_key_column(c)
        and is_string_column(result[c])
    ]

    for col in category_cols:
        rows = result.index[result[col].notna()].tolist()
        if not rows:
            continue
        n = max(1, int(len(rows) * CATEGORY_RATE))
        for idx in rng.sample(rows, min(n, len(rows))):
            old = result.at[idx, col]
            new = add_category_issue(old)
            if new != old:
                result.at[idx, col] = new
                counts["category_issues"] += 1

    duplicate_count = min(max(1, int(len(result) * DUPLICATE_RATE)), len(result))
    selected = rng.sample(result.index.tolist(), duplicate_count)
    result = pd.concat([result, result.loc[selected]], ignore_index=True)
    counts["duplicate_rows"] = duplicate_count

    return result, counts


def process_dataset(filename, rng):
    source = PROCESSED_DIR / filename
    target = BRONZE_DIR / filename

    if not source.exists():
        raise FileNotFoundError(f"Missing processed dataset: {source}")

    print(f"\nProcessing: {filename}")

    df = pd.read_csv(source, low_memory=False, dtype=object)
    dirty, counts = inject_issues(df, rng)
    dirty.to_csv(target, index=False, encoding="utf-8-sig")

    print(f"  Source rows: {len(df):,}")
    print(f"  Bronze rows: {len(dirty):,}")
    print(f"  Whitespace:  {counts['whitespace_issues']:,}")
    print(f"  Missing:     {counts['missing_values']:,}")
    print(f"  Categories:  {counts['category_issues']:,}")
    print(f"  Duplicates:  {counts['duplicate_rows']:,}")

    return {
        "dataset": filename,
        "source_rows": len(df),
        "bronze_rows": len(dirty),
        **counts,
    }


def main():
    print("Warehouse Bronze Layer Generator")
    print("================================")
    print("Source: data/processed")
    print("Target: data/bronze")
    print(f"Seed:   {SEED}")

    if not PROCESSED_DIR.exists():
        raise FileNotFoundError(f"Processed directory not found: {PROCESSED_DIR}")

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    results = [process_dataset(name, rng) for name in DATASETS]

    report = pd.DataFrame(results)
    report.to_csv(
        BRONZE_DIR / "bronze_quality_report.csv",
        index=False,
        encoding="utf-8-sig",
    )

    missing = [
        name for name in DATASETS
        if not (BRONZE_DIR / name).exists()
    ]
    if missing:
        raise ValueError(f"Bronze generation incomplete: {missing}")

    print("\nBronze validation passed.")
    print(f"Datasets generated: {len(DATASETS)}")
    print(f"Output directory: {BRONZE_DIR}")
    print("Bronze generation complete.")


if __name__ == "__main__":
    main()
