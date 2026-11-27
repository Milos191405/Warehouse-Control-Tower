-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Gold Layer - Star Schema (Dimensions & Fact Tables)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.fact_inventory_snapshot CASCADE;

DROP TABLE IF EXISTS gold.fact_picking CASCADE;

DROP TABLE IF EXISTS gold.fact_order_items CASCADE;

DROP TABLE IF EXISTS gold.fact_orders_fulfillment CASCADE;

DROP TABLE IF EXISTS gold.dim_locations CASCADE;

DROP TABLE IF EXISTS gold.dim_products CASCADE;

DROP TABLE IF EXISTS gold.dim_customers CASCADE;

DROP TABLE IF EXISTS gold.dim_calendar CASCADE;

-- ============================================================
-- 1. DIM_CALENDAR
-- ============================================================

CREATE TABLE gold.dim_calendar AS
SELECT
    date,
    year,
    EXTRACT(QUARTER FROM date)::INTEGER AS quarter,
    month,
    TO_CHAR(date, 'YYYY-MM') AS year_month,
    week,
    EXTRACT(ISODOW FROM date)::INTEGER AS weekday_num,
    weekday,
    is_weekend,
    is_public_holiday,
    holiday_name,
    is_school_holiday,
    school_holiday_name,
    is_school_free_day,
    is_vacation_period,
    season,
    demand_multiplier,
    warehouse_capacity_multiplier,
    is_buffer_period
FROM silver.calendar;

ALTER TABLE gold.dim_calendar ADD PRIMARY KEY (date);

-- ============================================================
-- 2. DIM_CUSTOMERS
-- ============================================================

CREATE TABLE gold.dim_customers AS
SELECT
    customer_id,
    COALESCE(customer_type, 'UNKNOWN') AS customer_type,
    COALESCE(status, 'UNKNOWN') AS status
FROM silver.customers;

ALTER TABLE gold.dim_customers ADD PRIMARY KEY (customer_id);

-- ============================================================
-- 3. DIM_PRODUCTS
-- ============================================================

CREATE TABLE gold.dim_products AS
SELECT
    product_id,
    article_number,
    ean,
    type AS product_type,
    short_description,
    sales_unit,
    base_unit,
    min_order_quantity,
    included_quantity,
    unit_weight_kg,
    width_m,
    height_m,
    length_m,
    ROUND((width_m * height_m * length_m)::NUMERIC, 6) AS unit_volume_m3,
    pack_qty_1,
    pack_type_1,
    pack_gross_weight_1
FROM silver.product_master;

ALTER TABLE gold.dim_products ADD PRIMARY KEY (product_id);

-- ============================================================
-- 4. DIM_LOCATIONS
-- ============================================================

CREATE TABLE gold.dim_locations AS
SELECT
    location_id,
    COALESCE(hall_id, 'UNKNOWN') AS hall_id,
    zone_nr,
    COALESCE(storage_type, 'UNKNOWN') AS storage_type,
    COALESCE(picking_method, 'UNKNOWN') AS picking_method,
    position,
    level,
    side
FROM silver.locations;

ALTER TABLE gold.dim_locations ADD PRIMARY KEY (location_id);

-- ============================================================
-- 5. FACT_ORDERS_FULFILLMENT (End-to-End Control Tower)
-- ============================================================

CREATE TABLE gold.fact_orders_fulfillment AS
WITH picking_agg AS (
    SELECT
        order_id,
        COUNT(*) AS pick_tasks_count,
        MIN(pick_datetime) AS first_pick_at,
        MAX(pick_datetime) AS last_pick_at,
        SUM(picked_quantity) AS total_picked_qty
    FROM silver.picking
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    o.order_datetime::DATE AS order_date,
    s.shipped_at::DATE AS shipped_date,
    s.delivered_at::DATE AS delivered_date,
    o.order_datetime,
    o.requested_delivery_datetime,
    p.first_pick_at,
    p.last_pick_at,
    pk.packing_started_at,
    pk.packing_completed_at,
    s.shipped_at,
    s.delivered_at,

-- Status and attributes
COALESCE(
    o.delivery_priority,
    s.delivery_priority,
    'UNKNOWN'
) AS delivery_priority,
COALESCE(o.order_status, 'UNKNOWN') AS order_status,
COALESCE(
    o.order_weight_class,
    'UNKNOWN'
) AS order_weight_class,
COALESCE(pk.packing_type, 'UNKNOWN') AS packing_type,
COALESCE(pk.packing_area, 'UNKNOWN') AS packing_area,
COALESCE(pk.packing_station, 'UNKNOWN') AS packing_station,
COALESCE(s.shipping_method, 'UNKNOWN') AS shipping_method,
COALESCE(s.transport_mode, 'UNKNOWN') AS transport_mode,
COALESCE(s.carrier, 'UNKNOWN') AS carrier,
COALESCE(s.carrier_type, 'UNKNOWN') AS carrier_type,
COALESCE(
    s.destination_country,
    'UNKNOWN'
) AS destination_country,
COALESCE(
    s.destination_region,
    'UNKNOWN'
) AS destination_region,
COALESCE(s.shipment_status, 'UNKNOWN') AS shipment_status,

-- Quantities and workload
o.total_items,
o.total_weight_kg,
p.pick_tasks_count,
p.total_picked_qty,
pk.container_count,
pk.workload_units,
pk.station_capacity_factor,

-- Cycle time metrics (hours / minutes)
ROUND(
    EXTRACT(
        EPOCH
        FROM (
                pk.packing_completed_at - pk.packing_started_at
            )
    ) / 60.0,
    2
) AS packing_duration_minutes,
s.shipping_preparation_minutes,
s.transit_hours,
s.fulfillment_hours,
s.delivery_margin_hours,
s.on_time_delivery
FROM
    silver.orders o
    LEFT JOIN picking_agg p ON o.order_id = p.order_id
    LEFT JOIN silver.packing pk ON o.order_id = pk.order_id
    LEFT JOIN silver.shipping s ON o.order_id = s.order_id;

ALTER TABLE gold.fact_orders_fulfillment ADD PRIMARY KEY (order_id);

ALTER TABLE gold.fact_orders_fulfillment
ADD FOREIGN KEY (customer_id) REFERENCES gold.dim_customers (customer_id);

CREATE INDEX idx_fact_orders_order_date ON gold.fact_orders_fulfillment (order_date);

CREATE INDEX idx_fact_orders_customer ON gold.fact_orders_fulfillment (customer_id);

CREATE INDEX idx_fact_orders_carrier ON gold.fact_orders_fulfillment (carrier);

-- ============================================================
-- 6. FACT_ORDER_ITEMS (Line-Level Fill Rate & Product Demand)
-- ============================================================

CREATE TABLE gold.fact_order_items AS
SELECT
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    o.order_datetime::DATE AS order_date,
    oi.product_id,
    oi.line_number,
    oi.requested_quantity,
    oi.picked_quantity,
    oi.packed_quantity,
    oi.shipped_quantity,
    oi.unit_weight_kg,
    oi.total_weight_kg,
    COALESCE(oi.item_status, 'UNKNOWN') AS item_status,
    CASE
        WHEN oi.requested_quantity > 0
        THEN ROUND(oi.shipped_quantity::NUMERIC / oi.requested_quantity, 4)
        ELSE NULL
    END AS line_fill_rate
FROM silver.order_items oi
JOIN silver.orders o ON oi.order_id = o.order_id;

ALTER TABLE gold.fact_order_items ADD PRIMARY KEY (order_item_id);

ALTER TABLE gold.fact_order_items
ADD FOREIGN KEY (order_id) REFERENCES gold.fact_orders_fulfillment (order_id);

ALTER TABLE gold.fact_order_items
ADD FOREIGN KEY (product_id) REFERENCES gold.dim_products (product_id);

CREATE INDEX idx_fact_oi_order_date ON gold.fact_order_items (order_date);

CREATE INDEX idx_fact_oi_product ON gold.fact_order_items (product_id);

-- ============================================================
-- 7. FACT_PICKING (Warehouse Floor Operations)
-- ============================================================

CREATE TABLE gold.fact_picking AS
SELECT
    pk.picking_id,
    pk.order_item_id,
    pk.order_id,
    pk.product_id,
    pk.location_id,
    pk.pick_datetime::DATE AS pick_date,
    pk.pick_datetime,
    COALESCE(pk.hall_id, 'UNKNOWN') AS hall_id,
    pk.zone_nr,
    COALESCE(pk.picking_method, 'UNKNOWN') AS picking_method,
    COALESCE(pk.storage_type, 'UNKNOWN') AS storage_type,
    pk.picked_quantity,
    pk.location_scan,
    pk.container_scan,
    (pk.location_scan IS TRUE AND pk.container_scan IS TRUE) AS full_scan_compliant,
    COALESCE(pk.pick_status, 'UNKNOWN') AS pick_status
FROM silver.picking pk;

ALTER TABLE gold.fact_picking ADD PRIMARY KEY (picking_id);

ALTER TABLE gold.fact_picking
ADD FOREIGN KEY (product_id) REFERENCES gold.dim_products (product_id);

ALTER TABLE gold.fact_picking
ADD FOREIGN KEY (location_id) REFERENCES gold.dim_locations (location_id);

CREATE INDEX idx_fact_picking_date ON gold.fact_picking (pick_date);

CREATE INDEX idx_fact_picking_location ON gold.fact_picking (location_id);

-- ============================================================
-- 8. FACT_INVENTORY_SNAPSHOT (Current Stock)
-- ============================================================

CREATE TABLE gold.fact_inventory_snapshot AS
SELECT
    i.inventory_id,
    i.product_id,
    i.location_id,
    i.last_updated::DATE AS snapshot_date,
    COALESCE(i.hall_id, 'UNKNOWN') AS hall_id,
    i.zone_nr,
    COALESCE(i.storage_type, 'UNKNOWN') AS storage_type,
    COALESCE(i.picking_method, 'UNKNOWN') AS picking_method,
    i.quantity,
    COALESCE(i.container_type, 'UNKNOWN') AS container_type,
    COALESCE(i.status, 'UNKNOWN') AS inventory_status,
    i.last_updated
FROM silver.inventory i;

ALTER TABLE gold.fact_inventory_snapshot
ADD PRIMARY KEY (inventory_id);

ALTER TABLE gold.fact_inventory_snapshot
ADD FOREIGN KEY (product_id) REFERENCES gold.dim_products (product_id);

ALTER TABLE gold.fact_inventory_snapshot
ADD FOREIGN KEY (location_id) REFERENCES gold.dim_locations (location_id);

CREATE INDEX idx_fact_inv_product ON gold.fact_inventory_snapshot (product_id);

CREATE INDEX idx_fact_inv_location ON gold.fact_inventory_snapshot (location_id);