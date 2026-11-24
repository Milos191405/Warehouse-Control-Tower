Warehouse Control Tower — Complete Project Documentation

Project Overview

This project simulates warehouse operations end to end—from business calendar and storage topology setup to inventory, order creation, picking, packing, and shipping.

The goal is to build a realistic data engineering and analytics platform for monitoring warehouse performance, capacity utilization, order fulfillment, picking, packing, and shipping operations, progressing incrementally from Python data generation to PostgreSQL (Bronze → Silver → Gold), SQL analytics, and Power BI reporting.

Project Goals

Model a realistic three-hall warehouse topology and operational workflow

Generate deterministic, relationally consistent synthetic warehouse data with Python

Use publicly available ABB product catalog data as the reference product master

Build a layered relational data model in PostgreSQL (Bronze → Silver → Gold)

Implement SQL data quality checks, transformations, KPIs, and bottleneck analysis

Build a Power BI Warehouse Control Tower and plan extended analytics and cloud workflows

Project Background & Data Disclaimer

The warehouse structure and operational workflows are modeled after an industrial distribution center environment (with 24,180 storage positions across three halls).

Product Reference Data: Product master attributes are derived from publicly available ABB article master data (product identifiers, descriptions, weights, and catalog reference attributes).

Synthetic Operations: All customer records, orders, order items, inventory quantities, timestamps, picking/packing queues, and shipping/delivery records are synthetically generated.

No Confidential Data: No company systems, proprietary credentials, live ERP/WMS exports, or confidential business data are included.

Warehouse Topology & Equipment

The simulated warehouse consists of three halls with 24,180 storage positions across 12 storage zones:

Hall 1 (18,500 locations, Zones 01–07): Pallet storage (FORKLIFT, PICKING_CART) and box storage (VERTICAL_LIFT, PICKING_CART). Includes packing stations H1-GP-01..09 and H1-KP-01..05.

Hall 2 (4,240 locations, Zones 08–10): Box storage (VERTICAL_LIFT) and pallet storage (FORKLIFT, PICKING_CART).

Hall 3 (1,440 locations, Zones 11–12): Pallet storage (PICKING_CART, STAPLER). Includes packing stations H3-GP-01..02.

Packing stations are modeled as operational resources separate from the 24,180 storage positions.

Calendar, Shifts & Capacity Queues

Business Calendar (business_calendar.py): Covers 2024-01-01 to 2027-03-31 (1,186 days) with Baden-Württemberg public holidays, school holiday capacity factors, and seasonal demand weights.

Shift Schedule (working_time.py): Two shifts (EARLY: 06:30–14:45, LATE: 14:45–22:45) with configured shift breaks (SHIFT_BREAKS) and working-day calculations.

Hourly Capacity Queue (capacity_queue.py & picking.py): Enforces hall-level hourly picking limits and shift windows so operational queues and peak-period delays emerge realistically without exceeding capacity rules.

End-to-End Operational Flow & Packing Rules

Order → Picking → Packing → Shipping

Packing classification follows weight and line-count rules:

> 30.0 kg: PALLET_SHIPMENT (PALLET / PALLET_FREIGHT)

<= 30.0 kg with 1–4 lines and <= 10.0 kg: SMALL_PACKAGE (Kleinpacken, boxes BOX_201–BOX_203)

<= 30.0 kg (remaining orders up to 30 kg): LARGE_PACKAGE (Großpacken, boxes BOX_201–BOX_203)

Current Validated Dataset (110,000 Orders)

Dataset

Records

Key Characteristics

calendar.csv

1,186

Daily calendar (2024-01-01 to 2027-03-31)

locations.csv

24,180

3 halls, 12 zones, box & pallet locations

product_master.csv

37,500

Standardized product catalog

inventory.csv

16,926

Opening warehouse stock across locations

customers.csv

500

Simulated customer master records

orders.csv

110,000

34,000 (2024), 40,000 (2025), 36,000 (2026); 84.5% boxes, 15.5% pallets

order_items.csv

259,425

2.36 avg lines/order; 40.5% single-piece lines (quantity = 1)

picking.csv

261,053

0 hourly capacity violations

packing.csv

110,000

64,750 SMALL_PACKAGE, 28,210 LARGE_PACKAGE, 17,040 PALLET_SHIPMENT

shipping.csv

110,000

102,609 on-time (93.28%), 7,391 late

Project Structure

Warehouse Control Tower/
├── data/
│ ├── source/abb/ # Source ABB catalog spreadsheets
│ ├── bronze/ # Bronze ingestion / staging files
│ └── processed/ # Generated CSV datasets & diagnostics/
├── src/
│ ├── generators/ # Simulation modules & picking_capacity_diagnostics.py
│ └── pipeline/ # bronze.py and validation.py
├── sql/ # PostgreSQL Bronze / Silver / Gold & analytics scripts
├── notebooks/ # Data quality and exploratory notebooks
├── powerbi/ # Power BI report files and assets
├── documentation/
│ └── complete_project_documentation.md
├── run_pipeline.py # Master pipeline & validation runner
├── requirements.txt # Python dependencies
└── README.md # Project overview

Development Roadmap & Status

Completed

[x] Three-hall warehouse topology (24,180 storage positions) and packing station model

[x] Baden-Württemberg business calendar and shift/capacity simulation (working_time.py, capacity_queue.py)

[x] Full Python generation pipeline (run_pipeline.py) and cross-dataset validation (src/pipeline/validation.py)

[x] Picking capacity and delivery timeliness diagnostic reports (picking_capacity_diagnostics.py)

In Progress / Next Steps

[ ] Bronze Layer (src/pipeline/bronze.py & sql/): Controlled data quality anomalies, staging files, and raw PostgreSQL tables

[ ] Silver Layer (sql/): Data type casting, trimming/normalization, deduplication, referential integrity checks, and DQ logging

[ ] Gold Layer (sql/): Star-schema dimensions and facts, operational KPIs, and bottleneck views

[ ] Power BI & Extended Analytics: Control Tower dashboards, DAX measures, and future Microsoft Fabric / advanced analytics exploration

Planned KPIs & Analytics Areas

Warehouse & Inventory: Storage utilization, inventory volume by hall/zone/storage type, multi-location products, low-stock checks

Orders & Fulfillment: Daily order volume, priority breakdown, average order size, order-to-delivery lead time, on-time delivery rate

Picking: Picking volume, picked quantity, picks per hour, hall/equipment workload, shift/queue bottleneck analysis

Packing: Orders packed, package/station workload (H1-KP, H1-GP, H3-GP), carton (<= 30 kg) vs. pallet (> 30 kg) split

Shipping: Shipment volume, carrier/transport mode mix, transit and fulfillment duration, late delivery root causes

Data Source & Disclaimer

The product master reference is based on publicly available ABB article master data. All operational warehouse data—including customers, orders, order items, inventory quantities, timestamps, picking/packing operations, and shipping records—is synthetically generated for educational, portfolio, and data engineering purposes.
