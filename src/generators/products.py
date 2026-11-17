from pathlib import Path
import os

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ABB_SOURCE_DIR = Path(os.getenv("WCT_ABB_SOURCE_DIR", PROJECT_ROOT / "data" / "source" / "abb"))
OUTPUT_DIR = Path(os.getenv("WCT_PROCESSED_DIR", PROJECT_ROOT / "data" / "processed"))
OUTPUT_FILE = OUTPUT_DIR / "product_master.csv"

PREFERRED_SOURCE_FILES = [
    "product_catalog.xlsx",
    "Excel-Preisliste_2026-09_Direkt-ABB.xlsx",
]

SOURCE_COLUMNS = {
    "Bestellnummer": "article_number",
    "EAN": "ean",
    "Typ": "type",
    "Kurztext": "short_description",
    "Langtext": "long_description",
    "Liefereinheit": "sales_unit",
    "Mindestbestellmenge": "min_order_quantity",
    "Basismengeneinheit": "base_unit",
    "Enthaltene Stückzahl": "included_quantity",
    "Nettogewicht [kg]": "unit_weight_kg",
    "Breite [m]": "width_m",
    "Höhe [m]": "height_m",
    "Länge [m]": "length_m",
    "Menge VPE1": "pack_qty_1",
    "Verpackungstyp VPE1": "pack_type_1",
    "Bruttogewicht VPE1 [kg]": "pack_gross_weight_1",
    "Menge VPE2": "pack_qty_2",
    "Verpackungstyp VPE2": "pack_type_2",
    "Bruttogewicht VPE2 [kg]": "pack_gross_weight_2",
    "Menge VPE3": "pack_qty_3",
    "Verpackungstyp VPE3": "pack_type_3",
    "Bruttogewicht VPE3 [kg]": "pack_gross_weight_3",
}

NUMERIC_COLUMNS = [
    "min_order_quantity", "included_quantity", "unit_weight_kg",
    "width_m", "height_m", "length_m", "pack_qty_1",
    "pack_gross_weight_1", "pack_qty_2", "pack_gross_weight_2",
    "pack_qty_3", "pack_gross_weight_3",
]


def find_source_file():
    if not ABB_SOURCE_DIR.exists():
        raise FileNotFoundError(f"ABB source directory not found: {ABB_SOURCE_DIR}")

    for filename in PREFERRED_SOURCE_FILES:
        candidate = ABB_SOURCE_DIR / filename
        if candidate.exists():
            return candidate

    excel_files = sorted(
        list(ABB_SOURCE_DIR.glob("*.xlsx")) + list(ABB_SOURCE_DIR.glob("*.xls"))
    )
    if len(excel_files) == 1:
        return excel_files[0]
    if not excel_files:
        raise FileNotFoundError(f"No Excel files found in: {ABB_SOURCE_DIR}")

    names = ", ".join(path.name for path in excel_files)
    raise RuntimeError(
        f"Multiple Excel files found and no preferred source matched: {names}"
    )


def clean_text(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def load_source(source_file):
    df = pd.read_excel(source_file, dtype=str)
    if df.empty:
        raise ValueError(f"ABB source file is empty: {source_file}")
    return df.apply(lambda column: column.map(clean_text))


def standardize_product_data(df):
    missing = [column for column in SOURCE_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"ABB source is missing required columns: {missing}")

    result = df[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS).copy()
    result["article_number"] = result["article_number"].map(clean_text)

    if result["article_number"].isna().any():
        count = int(result["article_number"].isna().sum())
        raise ValueError(f"Missing article numbers: {count}")

    result["product_id"] = "ABB-" + result["article_number"]
    result = result[["product_id"] + [c for c in result.columns if c != "product_id"]]

    for column in NUMERIC_COLUMNS:
        values = (
            result[column].astype("string").str.strip()
            .str.replace(",", ".", regex=False)
        )
        result[column] = pd.to_numeric(values, errors="coerce")

    return result


def validate_product_master(df):
    if df.empty:
        raise ValueError("Product master is empty.")

    for column in ("product_id", "article_number"):
        if df[column].isna().any() or df[column].astype("string").str.strip().eq("").any():
            raise ValueError(f"{column} contains missing or blank values.")
        duplicates = int(df[column].duplicated().sum())
        if duplicates:
            raise ValueError(f"{column} contains {duplicates} duplicate values.")

    for column in ("unit_weight_kg", "width_m", "height_m", "length_m"):
        negative_count = int(df[column].dropna().lt(0).sum())
        if negative_count:
            raise ValueError(f"{column} contains {negative_count} negative values.")

    for column in ("min_order_quantity", "included_quantity", "pack_qty_1",
                   "pack_qty_2", "pack_qty_3"):
        negative_count = int(df[column].dropna().lt(0).sum())
        if negative_count:
            raise ValueError(f"{column} contains {negative_count} negative values.")

    return True


def export_product_master(df, output_file=OUTPUT_FILE):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


def build_product_master(source_file=None, output_file=OUTPUT_FILE):
    source_file = Path(source_file) if source_file else find_source_file()
    source = load_source(source_file)
    product_df = standardize_product_data(source)
    validate_product_master(product_df)
    exported = export_product_master(product_df, output_file)
    print(f"Products: {len(product_df):,}")
    print(f"Output: {exported}")
    return product_df


if __name__ == "__main__":
    build_product_master()
