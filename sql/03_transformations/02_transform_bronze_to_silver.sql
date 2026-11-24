-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Bronze -> Silver Transformation (All 10 Tables, Deduplicated)
-- ============================================================

TRUNCATE TABLE silver.shipping,
silver.packing,
silver.picking,
silver.order_items,
silver.orders,
silver.inventory,
silver.locations,
silver.product_master,
silver.customers,
silver.calendar CASCADE;

-- ============================================================
-- 1. CALENDAR
-- ============================================================

INSERT INTO silver.calendar (
    date, year, month, week, weekday,
    is_weekend, is_public_holiday, holiday_name,
    is_school_holiday, school_holiday_name,
    is_school_free_day, school_free_day_name,
    is_vacation_period, season,
    demand_multiplier, warehouse_capacity_multiplier, is_buffer_period
)
SELECT DISTINCT ON (NULLIF(TRIM(date), '')::DATE)
    NULLIF(TRIM(date), '')::DATE,
    NULLIF(TRIM(year), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(month), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(week), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(weekday), ''),
    CASE WHEN UPPER(TRIM(is_weekend)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(is_weekend)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    CASE WHEN UPPER(TRIM(is_public_holiday)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(is_public_holiday)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    NULLIF(TRIM(holiday_name), ''),
    CASE WHEN UPPER(TRIM(is_school_holiday)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(is_school_holiday)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    NULLIF(TRIM(school_holiday_name), ''),
    CASE WHEN UPPER(TRIM(is_school_free_day)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(is_school_free_day)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    NULLIF(TRIM(school_free_day_name), ''),
    CASE WHEN UPPER(TRIM(is_vacation_period)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(is_vacation_period)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    UPPER(NULLIF(TRIM(season), '')),
    NULLIF(TRIM(demand_multiplier), '')::NUMERIC,
    NULLIF(TRIM(warehouse_capacity_multiplier), '')::NUMERIC,
    CASE WHEN UPPER(TRIM(is_buffer_period)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(is_buffer_period)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END
FROM bronze.calendar
WHERE NULLIF(TRIM(date), '') IS NOT NULL
ORDER BY NULLIF(TRIM(date), '')::DATE;

-- ============================================================
-- 2. CUSTOMERS
-- ============================================================

INSERT INTO
    silver.customers (
        customer_id,
        customer_type,
        status
    )
SELECT DISTINCT
    ON (NULLIF(TRIM(customer_id), '')) NULLIF(TRIM(customer_id), ''),
    UPPER(
        NULLIF(TRIM(customer_type), '')
    ),
    UPPER(NULLIF(TRIM(status), ''))
FROM bronze.customers
WHERE
    NULLIF(TRIM(customer_id), '') IS NOT NULL
ORDER BY NULLIF(TRIM(customer_id), ''), (
        NULLIF(TRIM(customer_type), '') IS NULL
    ), (
        NULLIF(TRIM(status), '') IS NULL
    );

-- ============================================================
-- 3. PRODUCT MASTER
-- ============================================================

INSERT INTO silver.product_master (
    product_id, article_number, ean, type,
    short_description, long_description,
    sales_unit, min_order_quantity, base_unit, included_quantity,
    unit_weight_kg, width_m, height_m, length_m,
    pack_qty_1, pack_type_1, pack_gross_weight_1,
    pack_qty_2, pack_type_2, pack_gross_weight_2,
    pack_qty_3, pack_type_3, pack_gross_weight_3
)
SELECT DISTINCT ON (NULLIF(TRIM(product_id), ''))
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(article_number), ''),
    NULLIF(TRIM(ean), ''),
    NULLIF(TRIM(type), ''),
    NULLIF(TRIM(short_description), ''),
    NULLIF(TRIM(long_description), ''),
    UPPER(NULLIF(TRIM(sales_unit), '')),
    NULLIF(TRIM(min_order_quantity), '')::NUMERIC,
    UPPER(NULLIF(TRIM(base_unit), '')),
    NULLIF(TRIM(included_quantity), '')::NUMERIC,
    NULLIF(TRIM(unit_weight_kg), '')::NUMERIC,
    NULLIF(TRIM(width_m), '')::NUMERIC,
    NULLIF(TRIM(height_m), '')::NUMERIC,
    NULLIF(TRIM(length_m), '')::NUMERIC,
    NULLIF(TRIM(pack_qty_1), '')::NUMERIC,
    UPPER(NULLIF(TRIM(pack_type_1), '')),
    NULLIF(TRIM(pack_gross_weight_1), '')::NUMERIC,
    NULLIF(TRIM(pack_qty_2), '')::NUMERIC,
    UPPER(NULLIF(TRIM(pack_type_2), '')),
    NULLIF(TRIM(pack_gross_weight_2), '')::NUMERIC,
    NULLIF(TRIM(pack_qty_3), '')::NUMERIC,
    UPPER(NULLIF(TRIM(pack_type_3), '')),
    NULLIF(TRIM(pack_gross_weight_3), '')::NUMERIC
FROM bronze.product_master
WHERE NULLIF(TRIM(product_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(product_id), ''),
    (NULLIF(TRIM(unit_weight_kg), '') IS NULL),
    (NULLIF(TRIM(short_description), '') IS NULL);

-- ============================================================
-- 4. LOCATIONS
-- ============================================================

INSERT INTO silver.locations (
    location_id, hall_id, zone_nr, storage_type,
    picking_method, position, level, side
)
SELECT DISTINCT ON (NULLIF(TRIM(location_id), ''))
    NULLIF(TRIM(location_id), ''),
    UPPER(NULLIF(TRIM(hall_id), '')),
    NULLIF(TRIM(zone_nr), '')::NUMERIC::INTEGER,
    UPPER(NULLIF(TRIM(storage_type), '')),
    UPPER(NULLIF(TRIM(picking_method), '')),
    NULLIF(TRIM(position), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(level), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(side), '')::NUMERIC::INTEGER
FROM bronze.locations
WHERE NULLIF(TRIM(location_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(location_id), ''),
    (NULLIF(TRIM(storage_type), '') IS NULL),
    (NULLIF(TRIM(picking_method), '') IS NULL);

-- ============================================================
-- 5. INVENTORY
-- ============================================================

INSERT INTO silver.inventory (
    inventory_id, product_id, location_id, hall_id, zone_nr,
    storage_type, picking_method, quantity,
    container_type, container_id, status, last_updated
)
SELECT DISTINCT ON (NULLIF(TRIM(inventory_id), ''))
    NULLIF(TRIM(inventory_id), ''),
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(location_id), ''),
    UPPER(NULLIF(TRIM(hall_id), '')),
    NULLIF(TRIM(zone_nr), '')::NUMERIC::INTEGER,
    UPPER(NULLIF(TRIM(storage_type), '')),
    UPPER(NULLIF(TRIM(picking_method), '')),
    NULLIF(TRIM(quantity), '')::NUMERIC::INTEGER,
    UPPER(NULLIF(TRIM(container_type), '')),
    NULLIF(TRIM(container_id), ''),
    UPPER(NULLIF(TRIM(status), '')),
    NULLIF(TRIM(last_updated), '')::TIMESTAMP
FROM bronze.inventory
WHERE NULLIF(TRIM(inventory_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(inventory_id), ''),
    (NULLIF(TRIM(quantity), '') IS NULL),
    (NULLIF(TRIM(status), '') IS NULL);

-- ============================================================
-- 6. ORDERS
-- ============================================================

INSERT INTO silver.orders (
    order_id, customer_id, order_datetime, order_status,
    delivery_priority, order_weight_class,
    requested_delivery_datetime, total_items, total_weight_kg
)
SELECT DISTINCT ON (NULLIF(TRIM(order_id), ''))
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(customer_id), ''),
    NULLIF(TRIM(order_datetime), '')::TIMESTAMP,
    UPPER(NULLIF(TRIM(order_status), '')),
    UPPER(NULLIF(TRIM(delivery_priority), '')),
    UPPER(NULLIF(TRIM(order_weight_class), '')),
    NULLIF(TRIM(requested_delivery_datetime), '')::TIMESTAMP,
    NULLIF(TRIM(total_items), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(total_weight_kg), '')::NUMERIC
FROM bronze.orders
WHERE NULLIF(TRIM(order_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(order_id), ''),
    (NULLIF(TRIM(order_datetime), '') IS NULL),
    (NULLIF(TRIM(delivery_priority), '') IS NULL);

-- ============================================================
-- 7. ORDER ITEMS
-- ============================================================

INSERT INTO silver.order_items (
    order_item_id, order_id, line_number, product_id,
    requested_quantity, unit_weight_kg, weight_source, total_weight_kg,
    picked_quantity, packed_quantity, shipped_quantity, item_status
)
SELECT DISTINCT ON (NULLIF(TRIM(order_item_id), ''))
    NULLIF(TRIM(order_item_id), ''),
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(line_number), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(requested_quantity), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(unit_weight_kg), '')::NUMERIC,
    UPPER(NULLIF(TRIM(weight_source), '')),
    NULLIF(TRIM(total_weight_kg), '')::NUMERIC,
    NULLIF(TRIM(picked_quantity), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(packed_quantity), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(shipped_quantity), '')::NUMERIC::INTEGER,
    UPPER(NULLIF(TRIM(item_status), ''))
FROM bronze.order_items
WHERE NULLIF(TRIM(order_item_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(order_item_id), ''),
    (NULLIF(TRIM(requested_quantity), '') IS NULL),
    (NULLIF(TRIM(item_status), '') IS NULL);

-- ============================================================
-- 8. PICKING
-- ============================================================

INSERT INTO silver.picking (
    picking_id, order_item_id, order_id, product_id,
    inventory_id, location_id, hall_id, zone_nr,
    picking_method, storage_type, picked_quantity,
    container_type, container_id,
    location_scan, container_scan, pick_status, pick_datetime
)
SELECT DISTINCT ON (NULLIF(TRIM(picking_id), ''))
    NULLIF(TRIM(picking_id), ''),
    NULLIF(TRIM(order_item_id), ''),
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(inventory_id), ''),
    NULLIF(TRIM(location_id), ''),
    UPPER(NULLIF(TRIM(hall_id), '')),
    NULLIF(TRIM(zone_nr), '')::NUMERIC::INTEGER,
    UPPER(NULLIF(TRIM(picking_method), '')),
    UPPER(NULLIF(TRIM(storage_type), '')),
    NULLIF(TRIM(picked_quantity), '')::NUMERIC::INTEGER,
    UPPER(NULLIF(TRIM(container_type), '')),
    NULLIF(TRIM(container_id), ''),
    CASE WHEN UPPER(TRIM(location_scan)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(location_scan)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    CASE WHEN UPPER(TRIM(container_scan)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(container_scan)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    UPPER(NULLIF(TRIM(pick_status), '')),
    NULLIF(TRIM(pick_datetime), '')::TIMESTAMP
FROM bronze.picking
WHERE NULLIF(TRIM(picking_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(picking_id), ''),
    (NULLIF(TRIM(pick_datetime), '') IS NULL),
    (NULLIF(TRIM(pick_status), '') IS NULL);

-- ============================================================
-- 9. PACKING
-- ============================================================

INSERT INTO silver.packing (
    packing_id, order_id, packing_type, packing_area, packing_station,
    station_capacity_factor, package_type, workload_units,
    container_id, container_type, container_count, article_count,
    total_quantity, order_weight_kg, container_scan, order_complete,
    packing_status, packing_started_at, packing_completed_at
)
SELECT DISTINCT ON (NULLIF(TRIM(packing_id), ''))
    NULLIF(TRIM(packing_id), ''),
    NULLIF(TRIM(order_id), ''),
    UPPER(NULLIF(TRIM(packing_type), '')),
    UPPER(NULLIF(TRIM(packing_area), '')),
    UPPER(NULLIF(TRIM(packing_station), '')),
    NULLIF(TRIM(station_capacity_factor), '')::NUMERIC,
    UPPER(NULLIF(TRIM(package_type), '')),
    NULLIF(TRIM(workload_units), '')::NUMERIC,
    NULLIF(TRIM(container_id), ''),
    UPPER(NULLIF(TRIM(container_type), '')),
    NULLIF(TRIM(container_count), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(article_count), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(total_quantity), '')::NUMERIC::INTEGER,
    NULLIF(TRIM(order_weight_kg), '')::NUMERIC,
    CASE WHEN UPPER(TRIM(container_scan)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(container_scan)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    CASE WHEN UPPER(TRIM(order_complete)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(order_complete)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    UPPER(NULLIF(TRIM(packing_status), '')),
    NULLIF(TRIM(packing_started_at), '')::TIMESTAMP,
    NULLIF(TRIM(packing_completed_at), '')::TIMESTAMP
FROM bronze.packing
WHERE NULLIF(TRIM(packing_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(packing_id), ''),
    (NULLIF(TRIM(packing_completed_at), '') IS NULL),
    (NULLIF(TRIM(packing_type), '') IS NULL);

-- ============================================================
-- 10. SHIPPING
-- ============================================================

INSERT INTO silver.shipping (
    shipment_id, order_id, packing_id, package_type,
    shipping_method, transport_mode, vehicle_type, carrier,
    origin_country, destination_country, destination_region, carrier_type,
    tracking_number, container_id, container_type, shipment_status,
    packing_completed_at, shipped_at, requested_delivery_datetime, delivered_at,
    transit_hours, shipping_preparation_minutes, fulfillment_hours,
    delivery_margin_hours, on_time_delivery, delivery_priority
)
SELECT DISTINCT ON (NULLIF(TRIM(shipment_id), ''))
    NULLIF(TRIM(shipment_id), ''),
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(packing_id), ''),
    UPPER(NULLIF(TRIM(package_type), '')),
    UPPER(NULLIF(TRIM(shipping_method), '')),
    UPPER(NULLIF(TRIM(transport_mode), '')),
    UPPER(NULLIF(TRIM(vehicle_type), '')),
    UPPER(NULLIF(TRIM(carrier), '')),
    UPPER(NULLIF(TRIM(origin_country), '')),
    UPPER(NULLIF(TRIM(destination_country), '')),
    NULLIF(TRIM(destination_region), ''),
    UPPER(NULLIF(TRIM(carrier_type), '')),
    NULLIF(TRIM(tracking_number), ''),
    NULLIF(TRIM(container_id), ''),
    UPPER(NULLIF(TRIM(container_type), '')),
    UPPER(NULLIF(TRIM(shipment_status), '')),
    NULLIF(TRIM(packing_completed_at), '')::TIMESTAMP,
    NULLIF(TRIM(shipped_at), '')::TIMESTAMP,
    NULLIF(TRIM(requested_delivery_datetime), '')::TIMESTAMP,
    NULLIF(TRIM(delivered_at), '')::TIMESTAMP,
    NULLIF(TRIM(transit_hours), '')::NUMERIC,
    NULLIF(TRIM(shipping_preparation_minutes), '')::NUMERIC,
    NULLIF(TRIM(fulfillment_hours), '')::NUMERIC,
    NULLIF(TRIM(delivery_margin_hours), '')::NUMERIC,
    CASE WHEN UPPER(TRIM(on_time_delivery)) IN ('TRUE', 'T', '1', 'YES') THEN TRUE
         WHEN UPPER(TRIM(on_time_delivery)) IN ('FALSE', 'F', '0', 'NO') THEN FALSE END,
    UPPER(NULLIF(TRIM(delivery_priority), ''))
FROM bronze.shipping
WHERE NULLIF(TRIM(shipment_id), '') IS NOT NULL
ORDER BY
    NULLIF(TRIM(shipment_id), ''),
    (NULLIF(TRIM(delivered_at), '') IS NULL),
    (NULLIF(TRIM(carrier), '') IS NULL);

SELECT 'calendar' AS table_name, COUNT(*) AS row_count
FROM silver.calendar
UNION ALL
SELECT 'customers', COUNT(*)
FROM silver.customers
UNION ALL
SELECT 'product_master', COUNT(*)
FROM silver.product_master
UNION ALL
SELECT 'locations', COUNT(*)
FROM silver.locations
UNION ALL
SELECT 'inventory', COUNT(*)
FROM silver.inventory
UNION ALL
SELECT 'orders', COUNT(*)
FROM silver.orders
UNION ALL
SELECT 'order_items', COUNT(*)
FROM silver.order_items
UNION ALL
SELECT 'picking', COUNT(*)
FROM silver.picking
UNION ALL
SELECT 'packing', COUNT(*)
FROM silver.packing
UNION ALL
SELECT 'shipping', COUNT(*)
FROM silver.shipping
ORDER BY table_name;