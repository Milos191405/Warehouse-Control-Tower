from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ABB_SOURCE_DIR = (
    PROJECT_ROOT
    / "data"
    / "source"
    / "abb"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

OUTPUT_FILE = OUTPUT_DIR / "product_master.csv"


# Preferred source filenames.
# The script checks these first before searching
# for other Excel files.
PREFERRED_SOURCE_FILES = [
    "product_catalog.xlsx",
    "Excel-Preisliste_2026-09_Direkt-ABB.xlsx",
]


# ============================================================
# SOURCE COLUMN MAPPING
# ============================================================

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

# ============================================================
# SOURCE FILE DISCOVERY
# ============================================================

def find_source_file():
    """
    Find the ABB product catalog.

    Priority:
    1. Preferred filenames
    2. If only one Excel file exists, use it
    3. If multiple files exist, stop instead of guessing
    """

    if not ABB_SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"ABB source directory not found:\n"
            f"{ABB_SOURCE_DIR}"
        )

    # --------------------------------------------------------
    # 1. Check preferred filenames
    # --------------------------------------------------------

    for filename in PREFERRED_SOURCE_FILES:
        candidate = ABB_SOURCE_DIR / filename

        if candidate.exists():
            print("Using ABB source file:")
            print(f"  {candidate.name}")
            return candidate

    # --------------------------------------------------------
    # 2. Search for Excel files
    # --------------------------------------------------------

    excel_files = sorted(
        [
            *ABB_SOURCE_DIR.glob("*.xlsx"),
            *ABB_SOURCE_DIR.glob("*.xls"),
        ]
    )

    if not excel_files:
        raise FileNotFoundError(
            f"No Excel files found in:\n"
            f"{ABB_SOURCE_DIR}"
        )

    # --------------------------------------------------------
    # 3. Exactly one file
    # --------------------------------------------------------

    if len(excel_files) == 1:
        print("No preferred filename found.")
        print("Using the only Excel file found:")
        print(f"  {excel_files[0].name}")

        return excel_files[0]

    # --------------------------------------------------------
    # 4. Multiple files
    # --------------------------------------------------------

    print()
    print("Multiple ABB Excel files were found:")
    print()

    for file in excel_files:
        print(f"  - {file.name}")

    print()

    raise RuntimeError(
        "Multiple Excel source files found and no preferred "
        "source file was found."
    )


# ============================================================
# LOAD SOURCE FILE
# ============================================================

def inspect_source_file(source_file):
    """
    Load the ABB Excel file.

    dtype=str is intentional:
    article numbers and EANs must not be converted
    to numeric values automatically.
    """

    print()
    print("Reading source file...")
    print()

    df = pd.read_excel(
        source_file,
        dtype=str
    )

    print(f"Rows:    {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    return df


# ============================================================
# INSPECT COLUMNS
# ============================================================

def inspect_columns(df):
    """
    Print source columns for debugging and validation.
    """

    print()
    print("Source columns:")
    print()

    for index, column in enumerate(df.columns, start=1):
        print(f"{index:3}. {column}")

    print()


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """
    Standardize text values.
    """

    if pd.isna(value):
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


# ============================================================
# CLEAN PRODUCT DATA
# ============================================================

def clean_product_data(df):
    """
    Clean raw ABB product data before standardization.
    """

    df = df.copy()

    for column in df.columns:
        df[column] = df[column].apply(clean_text)

    return df


# ============================================================
# STANDARDIZE PRODUCT DATA
# ============================================================

def standardize_product_data(df):
    """
    Select relevant ABB columns and rename them
    to the project's standardized English names.
    """

    missing_columns = [
        column
        for column in SOURCE_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        print()
        print("Missing expected source columns:")
        print()

        for column in missing_columns:
            print(f"  - {column}")

        print()

        raise ValueError(
            "The ABB source file does not contain all "
            "required columns."
        )

    product_df = df[
        list(SOURCE_COLUMNS.keys())
    ].rename(
        columns=SOURCE_COLUMNS
    )

    return product_df


# ============================================================
# PRODUCT ID
# ============================================================

def create_product_id(df):
    """
    Create an internal product identifier.

    Example:
        ABB-2CMA100240R1000
    """

    df = df.copy()

    df["product_id"] = (
        "ABB-"
        + df["article_number"].astype(str).str.strip()
    )

    # Put product_id first
    columns = [
        "product_id"
    ] + [
        column
        for column in df.columns
        if column != "product_id"
    ]

    df = df[columns]

    return df


# ============================================================
# NUMERIC CONVERSION
# ============================================================

def convert_numeric_columns(df):
    """
    Convert numeric fields to numeric types.

    Text identifiers such as article_number and EAN
    remain strings.
    """

    df = df.copy()

    numeric_columns = [
        "min_order_quantity",
        "included_quantity",
        "unit_weight_kg",
        "width_m",
        "height_m",
        "length_m",
        "pack_qty_1",
        "pack_gross_weight_1",
        "pack_qty_2",
        "pack_gross_weight_2",
        "pack_qty_3",
        "pack_gross_weight_3",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_product_master(df):
    """
    Validate the standardized product master.
    """

    print()
    print("Product master validation")
    print("-------------------------")

    # --------------------------------------------------------
    # Row count
    # --------------------------------------------------------

    if len(df) == 0:
        raise ValueError(
            "Product master is empty."
        )

    print(f"Products: {len(df):,}")

    # --------------------------------------------------------
    # Product ID
    # --------------------------------------------------------

    missing_product_ids = (
        df["product_id"]
        .isna()
        .sum()
    )

    if missing_product_ids > 0:
        raise ValueError(
            f"Missing product IDs: "
            f"{missing_product_ids}"
        )

    duplicate_product_ids = (
        df["product_id"]
        .duplicated()
        .sum()
    )

    if duplicate_product_ids > 0:
        raise ValueError(
            f"Duplicate product IDs: "
            f"{duplicate_product_ids}"
        )

    print("Product IDs: OK")

    # --------------------------------------------------------
    # Article numbers
    # --------------------------------------------------------

    missing_article_numbers = (
        df["article_number"]
        .isna()
        .sum()
    )

    print(
        f"Missing article numbers: "
        f"{missing_article_numbers}"
    )

    # --------------------------------------------------------
    # Weight
    # --------------------------------------------------------

    negative_weights = (
        df["unit_weight_kg"]
        .dropna()
        .lt(0)
        .sum()
    )

    if negative_weights > 0:
        raise ValueError(
            f"Negative product weights found: "
            f"{negative_weights}"
        )

    print("Weights: OK")

    # --------------------------------------------------------
    # Dimensions
    # --------------------------------------------------------

    for column in [
        "width_m",
        "height_m",
        "length_m",
    ]:
        negative_values = (
            df[column]
            .dropna()
            .lt(0)
            .sum()
        )

        if negative_values > 0:
            raise ValueError(
                f"Negative values found in {column}: "
                f"{negative_values}"
            )

    print("Dimensions: OK")

    # --------------------------------------------------------
    # Duplicated article numbers
    # --------------------------------------------------------

    duplicate_articles = (
        df["article_number"]
        .duplicated()
        .sum()
    )

    print(
        f"Duplicate article numbers: "
        f"{duplicate_articles}"
    )

    print()
    print("Product master validation passed.")


# ============================================================
# EXPORT
# ============================================================

def export_product_master(df):
    """
    Export standardized product master to CSV.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print()
    print("Export complete:")
    print(f"  {OUTPUT_FILE}")


# ============================================================
# MAIN PIPELINE
# ============================================================

def build_product_master():
    """
    Complete ABB product master pipeline.
    """

    print()
    print("ABB Product Master Generator")
    print("============================")
    print()

    # --------------------------------------------------------
    # Find source file
    # --------------------------------------------------------

    source_file = find_source_file()

    print()
    print("Source file:")
    print(f"  {source_file}")
    print()

    # --------------------------------------------------------
    # Read source
    # --------------------------------------------------------

    df = inspect_source_file(
        source_file
    )

    # --------------------------------------------------------
    # Inspect source structure
    # --------------------------------------------------------

    inspect_columns(df)

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    df = clean_product_data(df)

    # --------------------------------------------------------
    # Standardize
    # --------------------------------------------------------

    product_df = standardize_product_data(
        df
    )

    # --------------------------------------------------------
    # Product ID
    # --------------------------------------------------------

    product_df = create_product_id(
        product_df
    )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    product_df = convert_numeric_columns(
        product_df
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_product_master(
        product_df
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    export_product_master(
        product_df
    )

    return product_df


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":
    build_product_master()