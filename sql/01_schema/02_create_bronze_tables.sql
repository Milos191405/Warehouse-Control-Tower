-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Recreate Bronze Layer Tables
-- ============================================================

DROP TABLE IF EXISTS bronze.product_master CASCADE;

DROP TABLE IF EXISTS bronze.locations CASCADE;

DROP TABLE IF EXISTS bronze.inventory CASCADE;

DROP TABLE IF EXISTS bronze.orders CASCADE;

DROP TABLE IF EXISTS bronze.order_items CASCADE;

DROP TABLE IF EXISTS bronze.picking CASCADE;

DROP TABLE IF EXISTS bronze.packing CASCADE;

DROP TABLE IF EXISTS bronze.shipping CASCADE;

-- ============================================================
-- PRODUCT MASTER
-- ============================================================

CREATE TABLE bronze.product_master (
    product_id TEXT,
    article_number TEXT,
    ean TEXT,
    type TEXT,
    short_description TEXT,
    long_description TEXT,
    sales_unit TEXT,
    min_order_quantity TEXT,
    base_unit TEXT,
    included_quantity TEXT,
    unit_weight_kg TEXT,
    width_m TEXT,
    height_m TEXT,
    length_m TEXT,
    pack_qty_1 TEXT,
    pack_type_1 TEXT,
    pack_gross_weight_1 TEXT,
    pack_qty_2 TEXT,
    pack_type_2 TEXT,
    pack_gross_weight_2 TEXT,
    pack_qty_3 TEXT,
    pack_type_3 TEXT,
    pack_gross_weight_3 TEXT
);

-- ============================================================
-- LOCATIONS
-- ============================================================

CREATE TABLE bronze.locations (
    location_id TEXT,
    hall_id TEXT,
    zone_nr TEXT,
    storage_type TEXT,
    picking_method TEXT,
    position TEXT,
    level TEXT,
    side TEXT
);

-- ============================================================
-- INVENTORY
-- ============================================================

CREATE TABLE bronze.inventory (
    inventory_id TEXT,
    product_id TEXT,
    location_id TEXT,
    hall_id TEXT,
    zone_nr TEXT,
    storage_type TEXT,
    picking_method TEXT,
    quantity TEXT,
    container_type TEXT,
    container_id TEXT,
    status TEXT,
    last_updated TEXT
);

-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE bronze.orders (
    order_id TEXT,
    customer_id TEXT,
    order_datetime TEXT,
    requested_delivery_datetime TEXT,
    delivery_priority TEXT,
    order_status TEXT,
    order_weight_class TEXT,
    total_items TEXT,
    total_weight_kg TEXT
);

-- ============================================================
-- ORDER ITEMS
-- ============================================================

CREATE TABLE bronze.order_items (
    order_item_id TEXT,
    order_id TEXT,
    line_number TEXT,
    product_id TEXT,
    requested_quantity TEXT,
    unit_weight_kg TEXT,
    weight_source TEXT,
    total_weight_kg TEXT,
    picked_quantity TEXT,
    packed_quantity TEXT,
    shipped_quantity TEXT,
    item_status TEXT
);

-- ============================================================
-- PICKING
-- ============================================================

CREATE TABLE bronze.picking (
    picking_id TEXT,
    order_item_id TEXT,
    order_id TEXT,
    product_id TEXT,
    inventory_id TEXT,
    location_id TEXT,
    hall_id TEXT,
    zone_nr TEXT,
    picking_method TEXT,
    storage_type TEXT,
    picked_quantity TEXT,
    container_type TEXT,
    container_id TEXT,
    location_scan TEXT,
    container_scan TEXT,
    pick_status TEXT,
    pick_datetime TEXT
);

-- ============================================================
-- PACKING
-- ============================================================

CREATE TABLE bronze.packing (
    packing_id TEXT,
    order_id TEXT,
    packing_type TEXT,
    packing_area TEXT,
    packing_station TEXT,
    container_id TEXT,
    container_type TEXT,
    container_count TEXT,
    article_count TEXT,
    total_quantity TEXT,
    order_weight_kg TEXT,
    container_scan TEXT,
    order_complete TEXT,
    packing_status TEXT,
    packing_started_at TEXT,
    packing_completed_at TEXT,
    station_capacity_factor TEXT,
    package_type TEXT,
    workload_units TEXT
);

-- ============================================================
-- SHIPPING
-- ============================================================

CREATE TABLE bronze.shipping (
    shipment_id TEXT,
    order_id TEXT,
    packing_id TEXT,
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
    packing_completed_at TEXT,
    shipped_at TEXT,
    requested_delivery_datetime TEXT,
    delivered_at TEXT,
    transit_hours TEXT,
    shipping_preparation_minutes TEXT,
    fulfillment_hours TEXT,
    delivery_margin_hours TEXT,
    on_time_delivery TEXT,
    delivery_priority TEXT
);