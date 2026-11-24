-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Silver Layer - Create Tables (All 10 Tables with PK & FK)
-- ============================================================

DROP TABLE IF EXISTS silver.shipping CASCADE;

DROP TABLE IF EXISTS silver.packing CASCADE;

DROP TABLE IF EXISTS silver.picking CASCADE;

DROP TABLE IF EXISTS silver.order_items CASCADE;

DROP TABLE IF EXISTS silver.orders CASCADE;

DROP TABLE IF EXISTS silver.inventory CASCADE;

DROP TABLE IF EXISTS silver.locations CASCADE;

DROP TABLE IF EXISTS silver.product_master CASCADE;

DROP TABLE IF EXISTS silver.customers CASCADE;

DROP TABLE IF EXISTS silver.calendar CASCADE;

-- ============================================================
-- CALENDAR
-- ============================================================

CREATE TABLE silver.calendar (
    date DATE PRIMARY KEY,
    year INTEGER,
    month INTEGER,
    week INTEGER,
    weekday TEXT,
    is_weekend BOOLEAN,
    is_public_holiday BOOLEAN,
    holiday_name TEXT,
    is_school_holiday BOOLEAN,
    school_holiday_name TEXT,
    is_school_free_day BOOLEAN,
    school_free_day_name TEXT,
    is_vacation_period BOOLEAN,
    season TEXT,
    demand_multiplier NUMERIC,
    warehouse_capacity_multiplier NUMERIC,
    is_buffer_period BOOLEAN
);

-- ============================================================
-- CUSTOMERS
-- ============================================================

CREATE TABLE silver.customers (
    customer_id TEXT PRIMARY KEY,
    customer_type TEXT,
    status TEXT
);

-- ============================================================
-- PRODUCT MASTER
-- ============================================================

CREATE TABLE silver.product_master (
    product_id TEXT PRIMARY KEY,
    article_number TEXT,
    ean TEXT,
    type TEXT,
    short_description TEXT,
    long_description TEXT,
    sales_unit TEXT,
    min_order_quantity NUMERIC,
    base_unit TEXT,
    included_quantity NUMERIC,
    unit_weight_kg NUMERIC,
    width_m NUMERIC,
    height_m NUMERIC,
    length_m NUMERIC,
    pack_qty_1 NUMERIC,
    pack_type_1 TEXT,
    pack_gross_weight_1 NUMERIC,
    pack_qty_2 NUMERIC,
    pack_type_2 TEXT,
    pack_gross_weight_2 NUMERIC,
    pack_qty_3 NUMERIC,
    pack_type_3 TEXT,
    pack_gross_weight_3 NUMERIC
);

-- ============================================================
-- LOCATIONS
-- ============================================================

CREATE TABLE silver.locations (
    location_id TEXT PRIMARY KEY,
    hall_id TEXT,
    zone_nr INTEGER,
    storage_type TEXT,
    picking_method TEXT,
    position INTEGER,
    level INTEGER,
    side INTEGER
);

-- ============================================================
-- INVENTORY
-- ============================================================

CREATE TABLE silver.inventory (
    inventory_id TEXT PRIMARY KEY,
    product_id TEXT REFERENCES silver.product_master (product_id),
    location_id TEXT REFERENCES silver.locations (location_id),
    hall_id TEXT,
    zone_nr INTEGER,
    storage_type TEXT,
    picking_method TEXT,
    quantity INTEGER,
    container_type TEXT,
    container_id TEXT,
    status TEXT,
    last_updated TIMESTAMP
);

-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE silver.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES silver.customers (customer_id),
    order_datetime TIMESTAMP,
    order_status TEXT,
    delivery_priority TEXT,
    order_weight_class TEXT,
    requested_delivery_datetime TIMESTAMP,
    total_items INTEGER,
    total_weight_kg NUMERIC
);

-- ============================================================
-- ORDER ITEMS
-- ============================================================

CREATE TABLE silver.order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT REFERENCES silver.orders (order_id),
    line_number INTEGER,
    product_id TEXT REFERENCES silver.product_master (product_id),
    requested_quantity INTEGER,
    unit_weight_kg NUMERIC,
    weight_source TEXT,
    total_weight_kg NUMERIC,
    picked_quantity INTEGER,
    packed_quantity INTEGER,
    shipped_quantity INTEGER,
    item_status TEXT
);

-- ============================================================
-- PICKING
-- ============================================================

CREATE TABLE silver.picking (
    picking_id TEXT PRIMARY KEY,
    order_item_id TEXT REFERENCES silver.order_items (order_item_id),
    order_id TEXT REFERENCES silver.orders (order_id),
    product_id TEXT REFERENCES silver.product_master (product_id),
    inventory_id TEXT REFERENCES silver.inventory (inventory_id),
    location_id TEXT REFERENCES silver.locations (location_id),
    hall_id TEXT,
    zone_nr INTEGER,
    picking_method TEXT,
    storage_type TEXT,
    picked_quantity INTEGER,
    container_type TEXT,
    container_id TEXT,
    location_scan BOOLEAN,
    container_scan BOOLEAN,
    pick_status TEXT,
    pick_datetime TIMESTAMP
);

-- ============================================================
-- PACKING
-- ============================================================

CREATE TABLE silver.packing (
    packing_id TEXT PRIMARY KEY,
    order_id TEXT REFERENCES silver.orders (order_id),
    packing_type TEXT,
    packing_area TEXT,
    packing_station TEXT,
    station_capacity_factor NUMERIC,
    package_type TEXT,
    workload_units NUMERIC,
    container_id TEXT,
    container_type TEXT,
    container_count INTEGER,
    article_count INTEGER,
    total_quantity INTEGER,
    order_weight_kg NUMERIC,
    container_scan BOOLEAN,
    order_complete BOOLEAN,
    packing_status TEXT,
    packing_started_at TIMESTAMP,
    packing_completed_at TIMESTAMP
);

-- ============================================================
-- SHIPPING
-- ============================================================

CREATE TABLE silver.shipping (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT REFERENCES silver.orders (order_id),
    packing_id TEXT REFERENCES silver.packing (packing_id),
    package_type TEXT,
    shipping_method TEXT,
    transport_mode TEXT,
    vehicle_type TEXT,
    carrier TEXT,
    origin_country TEXT,
    destination_country TEXT,
    destination_region TEXT,
    carrier_type TEXT,
    tracking_number TEXT,
    container_id TEXT,
    container_type TEXT,
    shipment_status TEXT,
    packing_completed_at TIMESTAMP,
    shipped_at TIMESTAMP,
    requested_delivery_datetime TIMESTAMP,
    delivered_at TIMESTAMP,
    transit_hours NUMERIC,
    shipping_preparation_minutes NUMERIC,
    fulfillment_hours NUMERIC,
    delivery_margin_hours NUMERIC,
    on_time_delivery BOOLEAN,
    delivery_priority TEXT
);