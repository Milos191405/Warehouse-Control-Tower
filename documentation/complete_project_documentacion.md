# Warehouse Control Tower

A data analytics and warehouse operations project based on a
synthetic simulation of a distribution center in Heidelberg, Germany.

## Project Overview

This project simulates warehouse operations from inventory and
order creation to picking, packing, and shipping.

The goal is to build a realistic data platform and analytics
solution that can be used to monitor warehouse performance,
inventory, picking, packing, and order fulfillment.

The project is developed incrementally, starting with warehouse
modeling and synthetic data generation and progressing toward
PostgreSQL, SQL analytics, Power BI, and Microsoft Fabric.

## Project Goals

- Model a realistic warehouse structure
- Generate synthetic warehouse data with Python
- Use a real-world product catalog as the product source
- Build a relational data model
- Store and transform data using PostgreSQL
- Build analytical SQL queries and KPIs
- Create a Power BI Warehouse Control Tower
- Integrate Microsoft Fabric
- Analyze warehouse performance and operational bottlenecks
- Demonstrate an end-to-end analytics workflow

## Project Background

The warehouse model is based on a real-world industrial warehouse
environment and uses its storage capacity as a reference for the
synthetic simulation.

The project does not include company systems, customer data, order
data, credentials, or other confidential business data.

All operational data generated for the project is synthetic.

## Warehouse

The simulated warehouse consists of three halls:

- Hall 1
- Hall 2
- Hall 3

Total warehouse storage capacity currently modeled:

**24,180 storage positions**

The warehouse model includes:

- High racks
- Low picking areas
- Vertical lifts
- Handwagen picking areas
- Cart picking
- Stapler picking
- Packing stations
- Boxes and containers
- Carts
- Pallets

## Warehouse Processes

The main simulated process is:

```text
Order
  ↓
Picking
  ↓
Packing
  ↓
Shipping
```

The project also models:

- Storage locations
- Inventory
- Products
- Customers
- Orders
- Order items
- Boxes and containers
- Carts
- Pallets
- Picking operations
- Packing operations
- Shipping operations

## Picking

Warehouse locations are scanned during picking.

Depending on the storage area, products may be stored in
individual boxes with barcodes.

Products can exist in multiple warehouse locations.

The same product may therefore be stored in several locations
and containers.

Picking can be performed using:

- Hand carts
- Staplers
- Pallets
- Boxes / containers

The project models different picking scenarios, including
cart-based picking and pallet-based picking.

## Containers

Physical warehouse containers are modeled separately from
warehouse storage locations.

The project includes:

- Boxes
- Carts
- Pallets

Containers can have their own identifiers and barcodes.

A picking container can be associated with an order and its
picked items during the picking process.

## Packing Rules

Current simplified packing rules:

- 1–4 articles → Small Package / Klein Packen
- 5+ articles and ≤ 30 kg → Large Package / Groß Packen
- > 30 kg → Pallet Shipment

The packing process verifies the contents of the picking container
and whether the order has been completely picked.

## Packing Stations

The warehouse model includes packing stations used for different
packing processes.

### Hall 1

- 5 Klein Packen stations
- 9 large / pallet packing stations

### Hall 3

- 2 Groß Packen stations

Packing stations are modeled as operational resources and are not
included in the 24,180 warehouse storage positions.

## Technology Stack

### Data Generation

- Python
- Pandas

### Database

- PostgreSQL
- SQL

### Business Intelligence

- Microsoft Power BI
- DAX

### Cloud / Data Platform

- Microsoft Fabric

### Development

- Git
- GitHub

## Project Architecture

The planned project architecture is:

```text
ABB Product Catalog
        ↓
Python Data Generation
        ↓
Synthetic Warehouse Data
        ↓
PostgreSQL
        ↓
SQL Transformations
        ↓
Analytical Layer
        ↓
Power BI
        ↓
Warehouse Control Tower
```

Microsoft Fabric will be introduced as a later stage of the
project.

## Project Structure

The project is organized into separate layers for data generation,
database development, analytics, visualization, testing, and
documentation.

Current project structure:

```text
warehouse-control-tower/
│
├── data/
│   ├── source/
│   │   └── abb/
│   ├── raw/
│   ├── processed/
│   └── exports/
│
├── src/
│   ├── __init__.py
│   ├── README.md
│   ├── config.py
│   ├── generator.py
│   ├── validation.py
│   │
│   └── generators/
│       ├── __init__.py
│       ├── locations.py
│       ├── products.py
│       ├── customers.py
│       ├── orders.py
│       ├── order_items.py
│       ├── containers.py
│       ├── picking.py
│       ├── packing.py
│       └── shipping.py
│
├── sql/
│   ├── README.md
│   ├── 01_schema/
│   ├── 02_staging/
│   ├── 03_transformations/
│   ├── 04_analytics/
│   └── 05_kpis/
│
├── notebooks/
│   ├── 01_data_quality.ipynb
│   ├── 02_exploratory_analysis.ipynb
│   └── 03_kpi_validation.ipynb
│
├── powerbi/
│   ├── README.md
│   ├── screenshots/
│   └── documentation/
│
├── fabric/
│   └── README.md
│
├── tests/
│   ├── __init__.py
│   ├── test_generators.py
│   └── test_validation.py
│
├── documentation/
│   └── complete_project_documentation.md
│
├── README.md
├── requirements.txt
└── LICENSE
```

## Development Roadmap

The project is divided into several development phases.

### Phase 1 — Warehouse Modeling

Define and model the physical warehouse structure.

- [x] Define warehouse
- [x] Define three halls
- [x] Define storage areas
- [x] Calculate storage capacity
- [x] Define storage location concept
- [x] Define location ID concept
- [ ] Implement location generator
- [ ] Generate location master
- [ ] Validate generated locations

Current modeled capacity:

**24,180 storage positions**

### Phase 2 — Python Data Generation

Build a modular Python data generation pipeline.

Planned components:

- Location generation
- Product processing
- Customer generation
- Order generation
- Order item generation
- Inventory generation
- Container generation
- Picking simulation
- Packing simulation
- Shipping simulation
- Data validation

### Phase 3 — Product & Inventory Modeling

Build the product and inventory layer.

- [ ] Import ABB product catalog
- [ ] Inspect source structure
- [ ] Clean product data
- [ ] Standardize product fields
- [ ] Create product master
- [ ] Model packaging information
- [ ] Generate inventory
- [ ] Assign products to locations
- [ ] Support multi-location inventory
- [ ] Model box-level inventory
- [ ] Validate inventory

### Phase 4 — Order & Picking Simulation

Simulate customer orders and warehouse picking.

- [ ] Generate customers
- [ ] Generate orders
- [ ] Generate order items
- [ ] Generate picking tasks
- [ ] Simulate location scanning
- [ ] Simulate box scanning
- [ ] Simulate cart picking
- [ ] Simulate stapler picking
- [ ] Simulate pallet picking
- [ ] Track picked quantities
- [ ] Track incomplete orders
- [ ] Track picking timestamps
- [ ] Calculate picking duration

### Phase 5 — Packing & Shipping Simulation

Simulate the final stages of the warehouse process.

#### Packing

- [ ] Implement packing rules
- [ ] Assign orders to packing stations
- [ ] Simulate container scanning
- [ ] Verify order completeness
- [ ] Simulate Klein Packen
- [ ] Simulate Groß Packen
- [ ] Simulate pallet packing
- [ ] Track packing timestamps
- [ ] Track packing queues

#### Shipping

- [ ] Generate shipments
- [ ] Assign shipping methods
- [ ] Generate shipment timestamps
- [ ] Track shipment status
- [ ] Calculate fulfillment time
- [ ] Calculate shipping performance

### Phase 6 — PostgreSQL

Move the generated data into a relational database.

- [ ] Create PostgreSQL database
- [ ] Create database schemas
- [ ] Create tables
- [ ] Define primary keys
- [ ] Define foreign keys
- [ ] Load raw data
- [ ] Create staging layer
- [ ] Create transformation layer
- [ ] Create analytical layer
- [ ] Add indexes
- [ ] Add constraints
- [ ] Validate database

### Phase 7 — SQL Analytics

Build the analytical layer using SQL.

#### Inventory Analytics

- [ ] Total inventory
- [ ] Inventory by product
- [ ] Inventory by hall
- [ ] Inventory by location
- [ ] Inventory by storage type
- [ ] Products stored in multiple locations
- [ ] Low-stock analysis
- [ ] Storage utilization

#### Order Analytics

- [ ] Orders per day
- [ ] Orders by status
- [ ] Orders by priority
- [ ] Average order size
- [ ] Order backlog

#### Picking Analytics

- [ ] Picking volume
- [ ] Items picked
- [ ] Picking duration
- [ ] Picks per hour
- [ ] Incomplete orders
- [ ] Picking workload by hall
- [ ] Picking workload by picker type

#### Packing Analytics

- [ ] Orders ready for packing
- [ ] Orders packed
- [ ] Packing throughput
- [ ] Packing queue
- [ ] Packing workload by station
- [ ] Average packing time

#### Shipping Analytics

- [ ] Shipments per day
- [ ] Shipping volume
- [ ] Fulfillment time
- [ ] Shipment status
- [ ] Shipping performance

### Phase 8 — Power BI

Build the Warehouse Control Tower.

Planned dashboard pages:

#### Warehouse Overview

- Total Inventory
- Storage Utilization
- Open Orders
- Orders in Picking
- Orders Ready for Packing
- Orders Packed
- Orders Shipped

#### Inventory

- Inventory by Hall
- Inventory by Storage Type
- Inventory by Product
- Inventory by Location
- Multi-location Products
- Low Stock
- Stock Distribution

#### Picking

- Picking Volume
- Picking Performance
- Picks by Hall
- Picks by Picker Type
- Incomplete Orders
- Average Picking Time
- Picking Workload

#### Packing

- Packing Queue
- Orders Packed
- Packing Throughput
- Packing Station Utilization
- Average Packing Time
- Incomplete Orders

#### Shipping

- Shipment Volume
- Shipment Status
- Fulfillment Time
- Daily Shipping Performance

### Phase 9 — Microsoft Fabric

Extend the project into a modern cloud data platform.

Planned components:

- [ ] Fabric workspace
- [ ] Lakehouse
- [ ] Data ingestion
- [ ] Data pipelines
- [ ] Data transformation
- [ ] Data engineering
- [ ] Semantic model
- [ ] Power BI integration

Planned architecture:

```text
Source Data
    ↓
Fabric Data Pipeline
    ↓
Lakehouse
    ↓
Transformation
    ↓
Semantic Model
    ↓
Power BI
```

### Phase 10 — Advanced Analytics

Advanced analytics will be considered after the core data platform
and reporting solution are complete.

Potential future features:

- Demand forecasting
- Inventory optimization
- ABC analysis
- Slotting optimization
- Pick-path optimization
- Anomaly detection
- Operational alerts
- Predictive analytics
- Machine learning

## Planned KPIs

The final Warehouse Control Tower will contain operational KPIs
covering:

### Warehouse

- Storage Utilization
- Inventory Volume
- Inventory Distribution
- Active Locations

### Orders

- Open Orders
- Orders in Picking
- Orders Ready for Packing
- Orders Packed
- Orders Shipped

### Picking

- Picking Volume
- Picking Duration
- Picks per Hour
- Incomplete Orders
- Picking Workload

### Packing

- Packing Queue
- Packing Throughput
- Packing Station Utilization
- Average Packing Time

### Shipping

- Shipment Volume
- Fulfillment Time
- Shipment Status
- Shipping Performance

## Data Quality

Data quality is an important part of the project.

Validation checks will include:

- Duplicate location IDs
- Invalid location IDs
- Missing products
- Invalid quantities
- Negative inventory
- Duplicate barcodes
- Orders without order items
- Picking quantities exceeding available inventory
- Orders marked complete with missing items
- Invalid packing assignments
- Invalid shipment status transitions

Example:

```text
Expected storage positions: 24,180
Generated storage positions: 24,180

Status: PASS
```

## Testing

The Python data generation layer will include automated tests.

Planned tests include:

```text
test_location_count()
test_location_id_format()
test_unique_location_ids()
test_valid_sides()
test_valid_levels()
test_positive_inventory()
test_order_item_quantities()
```

The goal is to ensure that generated data follows the defined
warehouse structure and business rules.

## Development Approach

The project is intentionally developed step by step.

The goal is not to generate a large amount of random data immediately.

Instead, the development follows this sequence:

```text
Understand the Warehouse
        ↓
Model the Warehouse
        ↓
Generate Valid Data
        ↓
Validate the Data
        ↓
Store the Data
        ↓
Transform the Data
        ↓
Analyze the Data
        ↓
Build Dashboards
        ↓
Add Data Engineering
        ↓
Add Advanced Analytics
```

Business rules are defined before they are implemented in code.

The synthetic data should behave like realistic warehouse data
rather than being completely random.

## Project Status

🚧 **In Development**

### Completed

- [x] Warehouse structure defined
- [x] Three halls defined
- [x] Storage areas defined
- [x] Storage capacity calculated
- [x] Picking processes documented
- [x] Packing rules documented
- [x] Multi-location inventory concept defined
- [x] Box / cart / pallet concept defined

### In Progress

- [x] Location generator
- [x] Location master
- [ ] Warehouse data model

### Planned

- Product master
- Inventory generation
- Order generation
- Picking simulation
- Packing simulation
- Shipping simulation
- PostgreSQL
- SQL analytics
- Power BI
- Microsoft Fabric

## Documentation

This file contains the complete project documentation.

The main project README provides a shorter overview for portfolio
and GitHub presentation.

Additional phase-specific documentation can be added as the project
develops.

## Data Source

The product master is based on publicly available ABB product
master data downloaded from the official ABB website.

The ABB source data is used as the product reference for the
synthetic warehouse simulation, including product identifiers,
descriptions, packaging information, weights, and dimensions.

The operational warehouse data generated in this project is
synthetic and is not based on ABB operational or transactional data.

Source:

- [ABB Article Master Data](https://new.abb.com/low-voltage/de/artikelstammdaten/niederspannung)

## Disclaimer

This project is a synthetic simulation created for educational,
portfolio, data analytics, and data engineering purposes.

The warehouse structure and operational processes are modeled based
on a real-world warehouse scenario, while the generated operational
data is synthetic.

No confidential operational data is included in the project.

The project does not represent actual company performance or actual
production warehouse data.