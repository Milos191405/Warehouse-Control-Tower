-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Bronze -> Silver Transformation
-- ============================================================

-- ============================================================
-- 1. PRODUCT MASTER
-- ============================================================

INSERT INTO silver.product_master
SELECT
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(article_number), ''),
    NULLIF(TRIM(ean), ''),
    NULLIF(TRIM(type), ''),
    NULLIF(TRIM(short_description), ''),
    NULLIF(TRIM(long_description), ''),
    NULLIF(TRIM(sales_unit), ''),
    NULLIF(TRIM(min_order_quantity), '')::NUMERIC,
    NULLIF(TRIM(base_unit), ''),
    NULLIF(TRIM(included_quantity), '')::NUMERIC,
    NULLIF(TRIM(unit_weight_kg), '')::NUMERIC,
    NULLIF(TRIM(width_m), '')::NUMERIC,
    NULLIF(TRIM(height_m), '')::NUMERIC,
    NULLIF(TRIM(length_m), '')::NUMERIC,
    NULLIF(TRIM(pack_qty_1), '')::NUMERIC,
    NULLIF(TRIM(pack_type_1), ''),
    NULLIF(TRIM(pack_gross_weight_1), '')::NUMERIC,
    NULLIF(TRIM(pack_qty_2), '')::NUMERIC,
    NULLIF(TRIM(pack_type_2), ''),
    NULLIF(TRIM(pack_gross_weight_2), '')::NUMERIC,
    NULLIF(TRIM(pack_qty_3), '')::NUMERIC,
    NULLIF(TRIM(pack_type_3), ''),
    NULLIF(TRIM(pack_gross_weight_3), '')::NUMERIC
FROM bronze.product_master;

-- ============================================================
-- 2. LOCATIONS
-- ============================================================

INSERT INTO silver.locations
SELECT
    NULLIF(TRIM(location_id), ''),
    NULLIF(TRIM(hall_id), ''),
    NULLIF(TRIM(zone_nr), '')::INTEGER,
    CASE
        WHEN NULLIF(TRIM(storage_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(storage_type))
    END,
    CASE
        WHEN NULLIF(TRIM(picking_method), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(picking_method))
    END,
    NULLIF(TRIM(position), '')::INTEGER,
    NULLIF(TRIM(level), '')::INTEGER,
    NULLIF(TRIM(side), '')::INTEGER
FROM bronze.locations;

-- ============================================================
-- 3. INVENTORY
-- ============================================================


INSERT INTO silver.inventory
SELECT
    NULLIF(TRIM(inventory_id), ''),
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(location_id), ''),
    NULLIF(TRIM(hall_id), ''),
    NULLIF(TRIM(zone_nr), '')::INTEGER,

    CASE
        WHEN NULLIF(TRIM(storage_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(storage_type))
    END,

    CASE
        WHEN NULLIF(TRIM(picking_method), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(picking_method))
    END,

    NULLIF(TRIM(quantity), '')::INTEGER,

    CASE
        WHEN NULLIF(TRIM(container_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(container_type))
    END,

    NULLIF(TRIM(container_id), ''),

    CASE
        WHEN NULLIF(TRIM(status), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(status))
    END,

    NULLIF(TRIM(last_updated), '')::TIMESTAMP

FROM bronze.inventory;

-- ============================================================
-- 4. ORDERS
-- ============================================================


INSERT INTO silver.orders
SELECT
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(customer_id), ''),
    NULLIF(TRIM(order_datetime), '')::TIMESTAMP,
    NULLIF(TRIM(requested_delivery_datetime), '')::TIMESTAMP,

    CASE
        WHEN NULLIF(TRIM(delivery_priority), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(delivery_priority))
    END,

    CASE
        WHEN NULLIF(TRIM(order_status), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(order_status))
    END,

    CASE
        WHEN NULLIF(TRIM(order_weight_class), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(order_weight_class))
    END,

    NULLIF(TRIM(total_items), '')::INTEGER,
    NULLIF(TRIM(total_weight_kg), '')::NUMERIC

FROM bronze.orders;

-- ============================================================
-- 5. ORDER ITEMS
-- ============================================================


INSERT INTO silver.order_items
SELECT
    NULLIF(TRIM(order_item_id), ''),
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(line_number), '')::INTEGER,
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(requested_quantity), '')::INTEGER,
    NULLIF(TRIM(unit_weight_kg), '')::NUMERIC,

    CASE
        WHEN NULLIF(TRIM(weight_source), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(weight_source))
    END,

    NULLIF(TRIM(total_weight_kg), '')::NUMERIC,
    NULLIF(TRIM(picked_quantity), '')::INTEGER,
    NULLIF(TRIM(packed_quantity), '')::INTEGER,
    NULLIF(TRIM(shipped_quantity), '')::INTEGER,

    CASE
        WHEN NULLIF(TRIM(item_status), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(item_status))
    END

FROM bronze.order_items;

-- ============================================================
-- 6. PICKING
-- ============================================================


INSERT INTO silver.picking
SELECT
    NULLIF(TRIM(picking_id), ''),
    NULLIF(TRIM(order_item_id), ''),
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(product_id), ''),
    NULLIF(TRIM(inventory_id), ''),
    NULLIF(TRIM(location_id), ''),
    NULLIF(TRIM(hall_id), ''),
    NULLIF(TRIM(zone_nr), '')::INTEGER,

    CASE
        WHEN NULLIF(TRIM(picking_method), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(picking_method))
    END,

    CASE
        WHEN NULLIF(TRIM(storage_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(storage_type))
    END,

    NULLIF(TRIM(picked_quantity), '')::INTEGER,

    CASE
        WHEN NULLIF(TRIM(container_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(container_type))
    END,

    NULLIF(TRIM(container_id), ''),

    CASE
        WHEN UPPER(TRIM(location_scan)) IN ('TRUE', 'T', '1', 'YES')
            THEN TRUE
        WHEN UPPER(TRIM(location_scan)) IN ('FALSE', 'F', '0', 'NO')
            THEN FALSE
        ELSE NULL
    END,

    CASE
        WHEN UPPER(TRIM(container_scan)) IN ('TRUE', 'T', '1', 'YES')
            THEN TRUE
        WHEN UPPER(TRIM(container_scan)) IN ('FALSE', 'F', '0', 'NO')
            THEN FALSE
        ELSE NULL
    END,

    CASE
        WHEN NULLIF(TRIM(pick_status), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(pick_status))
    END,

    NULLIF(TRIM(pick_datetime), '')::TIMESTAMP

FROM bronze.picking;

-- ============================================================
-- 7. PACKING
-- ============================================================


INSERT INTO silver.packing
SELECT
    NULLIF(TRIM(packing_id), ''),
    NULLIF(TRIM(order_id), ''),

    CASE
        WHEN NULLIF(TRIM(packing_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(packing_type))
    END,

    NULLIF(TRIM(packing_area), ''),
    NULLIF(TRIM(packing_station), ''),
    NULLIF(TRIM(container_id), ''),

    CASE
        WHEN NULLIF(TRIM(container_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(container_type))
    END,

    NULLIF(TRIM(container_count), '')::INTEGER,
    NULLIF(TRIM(article_count), '')::INTEGER,
    NULLIF(TRIM(total_quantity), '')::INTEGER,
    NULLIF(TRIM(order_weight_kg), '')::NUMERIC,

    CASE
        WHEN UPPER(TRIM(container_scan)) IN ('TRUE', 'T', '1', 'YES')
            THEN TRUE
        WHEN UPPER(TRIM(container_scan)) IN ('FALSE', 'F', '0', 'NO')
            THEN FALSE
        ELSE NULL
    END,

    CASE
        WHEN UPPER(TRIM(order_complete)) IN ('TRUE', 'T', '1', 'YES')
            THEN TRUE
        WHEN UPPER(TRIM(order_complete)) IN ('FALSE', 'F', '0', 'NO')
            THEN FALSE
        ELSE NULL
    END,

    CASE
        WHEN NULLIF(TRIM(packing_status), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(packing_status))
    END,

    NULLIF(TRIM(packing_started_at), '')::TIMESTAMP,
    NULLIF(TRIM(packing_completed_at), '')::TIMESTAMP,

    NULLIF(TRIM(station_capacity_factor), '')::NUMERIC,

    CASE
        WHEN NULLIF(TRIM(package_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(package_type))
    END,

    NULLIF(TRIM(workload_units), '')::NUMERIC

FROM bronze.packing;

-- ============================================================
-- 8. SHIPPING
-- ============================================================


INSERT INTO silver.shipping
SELECT
    NULLIF(TRIM(shipment_id), ''),
    NULLIF(TRIM(order_id), ''),
    NULLIF(TRIM(packing_id), ''),

    CASE
        WHEN NULLIF(TRIM(package_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(package_type))
    END,

    CASE
        WHEN NULLIF(TRIM(shipping_method), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(shipping_method))
    END,

    CASE
        WHEN NULLIF(TRIM(transport_mode), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(transport_mode))
    END,

    CASE
        WHEN NULLIF(TRIM(vehicle_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(vehicle_type))
    END,

    CASE
        WHEN NULLIF(TRIM(carrier), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(carrier))
    END,

    NULLIF(TRIM(origin_country), ''),
    NULLIF(TRIM(destination_country), ''),
    NULLIF(TRIM(destination_region), ''),

    CASE
        WHEN NULLIF(TRIM(carrier_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(carrier_type))
    END,

    NULLIF(TRIM(tracking_number), ''),
    NULLIF(TRIM(container_id), ''),

    CASE
        WHEN NULLIF(TRIM(container_type), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(container_type))
    END,

    CASE
        WHEN NULLIF(TRIM(shipment_status), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(shipment_status))
    END,

    NULLIF(TRIM(packing_completed_at), '')::TIMESTAMP,
    NULLIF(TRIM(shipped_at), '')::TIMESTAMP,
    NULLIF(TRIM(requested_delivery_datetime), '')::TIMESTAMP,
    NULLIF(TRIM(delivered_at), '')::TIMESTAMP,

    NULLIF(TRIM(transit_hours), '')::NUMERIC,
    NULLIF(TRIM(shipping_preparation_minutes), '')::NUMERIC,
    NULLIF(TRIM(fulfillment_hours), '')::NUMERIC,
    NULLIF(TRIM(delivery_margin_hours), '')::NUMERIC,

    CASE
        WHEN UPPER(TRIM(on_time_delivery)) IN ('TRUE', 'T', '1', 'YES')
            THEN TRUE
        WHEN UPPER(TRIM(on_time_delivery)) IN ('FALSE', 'F', '0', 'NO')
            THEN FALSE
        ELSE NULL
    END,

    CASE
        WHEN NULLIF(TRIM(delivery_priority), '') IS NULL
            THEN NULL
        ELSE UPPER(TRIM(delivery_priority))
    END

FROM bronze.shipping;