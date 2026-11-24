# Warehouse Control Tower

End-to-end data analytics and warehouse operations project based on a synthetic simulation of a three-hall distribution center in Germany, progressing from Python data generation to PostgreSQL transformations (`Bronze → Silver → Gold`), SQL analytics, and Power BI reporting.

## Project Overview

This project models warehouse operations end to end—from calendar and storage topology setup to inventory, order creation, picking, packing, and shipping.

The goal is to build a realistic data platform and analytical solution for monitoring warehouse performance, capacity utilization, order fulfillment, picking, packing, and shipping operations.

## Key Domain & Simulation Rules

- **Warehouse Topology:** Three halls (`Hall 1`, `Hall 2`, `Hall 3`) with **24,180 storage locations** across 12 zones and picking methods (`VERTICAL_LIFT`, `PICKING_CART`, `FORKLIFT`, `STAPLER`). Packing stations are modeled separately from storage positions.
- **Calendar & Shifts:** Driven by a Baden-Württemberg business calendar (`2024-01-01` to `2027-03-31`) with holidays, school holiday capacity factors, and two shifts (`EARLY`: `06:30–14:45`, `LATE`: `14:45–22:45`) including configured shift breaks (`SHIFT_BREAKS`) and hourly hall picking capacity queues.
- **Packing Classification (`<= 30 kg` Cartons vs. `> 30 kg` Pallets):**
  - `> 30.0 kg` → `PALLET_SHIPMENT` (`PALLET` / `PALLET_FREIGHT`)
  - `<= 30.0 kg` with `1–4` lines and `<= 10.0 kg` → `SMALL_PACKAGE` (_Kleinpacken_, boxes `BOX_201`–`BOX_203`)
  - `<= 30.0 kg` (remaining orders up to 30 kg) → `LARGE_PACKAGE` (_Großpacken_, boxes `BOX_201`–`BOX_203`)

## Current Generated Dataset

The latest validated simulation run produced **110,000 orders** (`2024`: 34,000; `2025`: 40,000; `2026`: 36,000):

| Dataset / Metric                |     Value | Notes                                                         |
| :------------------------------ | --------: | :------------------------------------------------------------ |
| Products (`product_master.csv`) |  `37,500` | Standardized reference catalog based on ABB article data      |
| Locations (`locations.csv`)     |  `24,180` | 3 halls, 12 zones, box & pallet storage                       |
| Inventory (`inventory.csv`)     |  `16,926` | Opening stock snapshot                                        |
| Orders (`orders.csv`)           | `110,000` | `84.5%` up to 30 kg (boxes), `15.5%` over 30 kg (pallets)     |
| Order Items (`order_items.csv`) | `259,425` | `40.5%` single-piece lines (`quantity = 1`)                   |
| Picking (`picking.csv`)         | `261,053` | `0` hourly capacity violations                                |
| Packing (`packing.csv`)         | `110,000` | `64,750` small, `28,210` large, `17,040` pallet shipments     |
| Shipping (`shipping.csv`)       | `110,000` | **93.28%** on-time delivery (`102,609` on-time, `7,391` late) |

## Project Structure

````text
Warehouse Control Tower/
├── data/
│   ├── source/abb/          # Source ABB catalog spreadsheets
│   ├── bronze/              # Bronze ingestion / staging files
│   └── processed/           # Generated CSV datasets & diagnostics/
├── src/
│   ├── generators/          # Simulation modules & picking_capacity_diagnostics.py
│   └── pipeline/            # bronze.py and validation.py
├── sql/                     # PostgreSQL Bronze / Silver / Gold & analytics scripts
├── notebooks/               # Data quality and exploratory notebooks
├── powerbi/                 # Power BI report files and assets
├── documentation/
│   └── complete_project_documentation.md
├── run_pipeline.py          # Master pipeline & validation runner
├── requirements.txt
└── README.md

## Running the Data Pipeline

```bash
pip install -r requirements.txt
python run_pipeline.py
````

For full details on architecture, roadmap, KPIs, and data rules, see [documentation/complete_project_documentation.md](documentation/complete_project_documentation.md)[cite: 3].

## Data Source & Disclaimer

Product reference attributes are derived from publicly available ABB article master data[cite: 1, 3]. All operational orders, inventory movements, shift timestamps, picking/packing queues, and shipping records are synthetically generated for portfolio, analytics, and data engineering demonstration purposes[cite: 1, 3].
