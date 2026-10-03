# Warehouse Control Tower

A data analytics and warehouse operations project based on a
synthetic simulation of a distribution center in Heidelberg, Germany.

## Project Overview

This project simulates warehouse operations from inventory and
order creation to picking, packing, and shipping.

The goal is to build an end-to-end analytics solution for monitoring
warehouse performance, inventory, order fulfillment, picking,
packing, and shipping operations.

The project is developed incrementally, starting with warehouse
modeling and synthetic data generation and progressing toward
PostgreSQL, SQL analytics, Power BI, and Microsoft Fabric.

## Project Goals

- Model a realistic warehouse structure
- Generate synthetic warehouse data with Python
- Use a real-world product catalog as the product source
- Build a relational data model
- Store and transform data using PostgreSQL
- Develop analytical SQL queries and KPIs
- Build a Power BI Warehouse Control Tower
- Integrate Microsoft Fabric
- Analyze warehouse performance and operational bottlenecks

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

Total modeled storage capacity:

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

## Warehouse Process

The main operational flow is:

**Order → Picking → Packing → Shipping**

The project models:

- Storage locations
- Inventory
- Products
- Customers
- Orders
- Order items
- Containers
- Picking operations
- Packing operations
- Shipping operations

Products can be stored in multiple warehouse locations.

Warehouse locations and containers can be scanned during
the picking and packing processes.

## Packing

The project includes different packing scenarios for:

- Small packages
- Large packages
- Pallet shipments

Packing stations are modeled separately from warehouse
storage locations.

## Technology Stack

| Area | Technology |
|---|---|
| Data Generation | Python, Pandas |
| Database | PostgreSQL |
| Analytics | SQL |
| Business Intelligence | Power BI, DAX |
| Data Platform | Microsoft Fabric |
| Development | Git, GitHub |

## Architecture

The planned architecture is:

**ABB Product Catalog → Python Data Generation → Synthetic Warehouse Data → PostgreSQL → SQL Transformations → Analytical Layer → Power BI → Warehouse Control Tower**

Microsoft Fabric will be introduced as a later stage of the project.

## Project Structure

The project is organized into separate layers for data generation,
database development, analytics, visualization, testing, and documentation.

Main directories:

- `data/` — source, raw, processed, and exported data
- `src/` — Python data generation and validation
- `sql/` — PostgreSQL schemas, transformations, analytics, and KPIs
- `notebooks/` — data quality and exploratory analysis
- `powerbi/` — Power BI documentation and screenshots
- `fabric/` — Microsoft Fabric documentation
- `tests/` — automated tests
- `documentation/` — complete project documentation

## Development Roadmap

### Phase 1 — Warehouse Modeling

- [x] Define warehouse structure
- [x] Define three halls
- [x] Define storage areas
- [x] Calculate storage capacity
- [ ] Implement location generator
- [ ] Generate location master

### Phase 2 — Python Data Generation

- [ ] Product processing
- [ ] Inventory generation
- [ ] Customer generation
- [ ] Order generation
- [ ] Picking simulation
- [ ] Packing simulation
- [ ] Shipping simulation
- [ ] Data validation

### Phase 3 — PostgreSQL & SQL

- [ ] PostgreSQL database
- [ ] Relational data model
- [ ] Staging layer
- [ ] Transformation layer
- [ ] Analytical SQL
- [ ] Warehouse KPIs

### Phase 4 — Power BI

Build the Warehouse Control Tower with dashboards for:

- Warehouse Overview
- Inventory
- Picking
- Packing
- Shipping

### Phase 5 — Microsoft Fabric

- [ ] Lakehouse
- [ ] Data pipelines
- [ ] Data transformation
- [ ] Semantic model
- [ ] Power BI integration

### Phase 6 — Advanced Analytics

Potential future features:

- Demand forecasting
- Inventory optimization
- ABC analysis
- Slotting optimization
- Anomaly detection
- Predictive analytics
- Machine learning

## Project Status

🚧 **In Development**

### Completed

- [x] Warehouse structure defined
- [x] Three halls defined
- [x] Storage capacity calculated
- [x] Picking process documented
- [x] Packing process documented
- [x] Multi-location inventory concept defined
- [x] Container concept defined

### Currently Working On

- [ ] Location generator
- [ ] Location master
- [ ] Warehouse data model

## Documentation

Detailed project documentation is available in the
`documentation/` directory:

- [Complete Project Documentation](documentation/complete_project_documentation.md)

Additional project documentation can be added as the project
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
on a real-world warehouse environment, while the generated
operational data is synthetic.

No company systems, customer data, order data, credentials, or other
confidential business data are included in the project.