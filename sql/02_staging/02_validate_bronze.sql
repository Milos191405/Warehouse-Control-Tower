-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Bronze Layer Validation (All 10 Tables)
-- ============================================================

-- ------------------------------------------------------------
-- 1. ROW COUNTS
-- ------------------------------------------------------------
SELECT 'calendar' AS table_name, COUNT(*) AS row_count
FROM bronze.calendar
UNION ALL
SELECT 'customers', COUNT(*)
FROM bronze.customers
UNION ALL
SELECT 'product_master', COUNT(*)
FROM bronze.product_master
UNION ALL
SELECT 'locations', COUNT(*)
FROM bronze.locations
UNION ALL
SELECT 'inventory', COUNT(*)
FROM bronze.inventory
UNION ALL
SELECT 'orders', COUNT(*)
FROM bronze.orders
UNION ALL
SELECT 'order_items', COUNT(*)
FROM bronze.order_items
UNION ALL
SELECT 'picking', COUNT(*)
FROM bronze.picking
UNION ALL
SELECT 'packing', COUNT(*)
FROM bronze.packing
UNION ALL
SELECT 'shipping', COUNT(*)
FROM bronze.shipping
ORDER BY table_name;

-- ------------------------------------------------------------
-- 2. MISSING PRIMARY / FOREIGN KEYS (Expected: 0)
-- ------------------------------------------------------------
SELECT
    'calendar' AS table_name,
    COUNT(*) FILTER (
        WHERE
            date IS NULL
            OR TRIM(date) = ''
    ) AS missing_pk,
    0 AS missing_fk
FROM bronze.calendar
UNION ALL
SELECT 'customers', COUNT(*) FILTER (
        WHERE
            customer_id IS NULL
            OR TRIM(customer_id) = ''
    ), 0
FROM bronze.customers
UNION ALL
SELECT 'product_master', COUNT(*) FILTER (
        WHERE
            product_id IS NULL
            OR TRIM(product_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            article_number IS NULL
            OR TRIM(article_number) = ''
    )
FROM bronze.product_master
UNION ALL
SELECT 'locations', COUNT(*) FILTER (
        WHERE
            location_id IS NULL
            OR TRIM(location_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            hall_id IS NULL
            OR TRIM(hall_id) = ''
    )
FROM bronze.locations
UNION ALL
SELECT 'inventory', COUNT(*) FILTER (
        WHERE
            inventory_id IS NULL
            OR TRIM(inventory_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            product_id IS NULL
            OR TRIM(product_id) = ''
    )
FROM bronze.inventory
UNION ALL
SELECT 'orders', COUNT(*) FILTER (
        WHERE
            order_id IS NULL
            OR TRIM(order_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            customer_id IS NULL
            OR TRIM(customer_id) = ''
    )
FROM bronze.orders
UNION ALL
SELECT 'order_items', COUNT(*) FILTER (
        WHERE
            order_item_id IS NULL
            OR TRIM(order_item_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            order_id IS NULL
            OR TRIM(order_id) = ''
    )
FROM bronze.order_items
UNION ALL
SELECT 'picking', COUNT(*) FILTER (
        WHERE
            picking_id IS NULL
            OR TRIM(picking_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            order_item_id IS NULL
            OR TRIM(order_item_id) = ''
    )
FROM bronze.picking
UNION ALL
SELECT 'packing', COUNT(*) FILTER (
        WHERE
            packing_id IS NULL
            OR TRIM(packing_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            order_id IS NULL
            OR TRIM(order_id) = ''
    )
FROM bronze.packing
UNION ALL
SELECT 'shipping', COUNT(*) FILTER (
        WHERE
            shipment_id IS NULL
            OR TRIM(shipment_id) = ''
    ), COUNT(*) FILTER (
        WHERE
            order_id IS NULL
            OR TRIM(order_id) = ''
    )
FROM bronze.shipping;

-- ------------------------------------------------------------
-- 3. INJECTED DATA QUALITY ISSUES (Whitespace & Missing Non-Keys)
-- ------------------------------------------------------------
SELECT
    'orders.delivery_priority' AS field,
    COUNT(*) FILTER (
        WHERE
            delivery_priority <> TRIM(delivery_priority)
    ) AS whitespace_issues,
    COUNT(*) FILTER (
        WHERE
            delivery_priority IS NULL
            OR TRIM(delivery_priority) = ''
    ) AS missing_values
FROM bronze.orders
UNION ALL
SELECT 'orders.order_datetime', COUNT(*) FILTER (
        WHERE
            order_datetime <> TRIM(order_datetime)
    ), COUNT(*) FILTER (
        WHERE
            order_datetime IS NULL
            OR TRIM(order_datetime) = ''
    )
FROM bronze.orders
UNION ALL
SELECT 'customers.customer_type', COUNT(*) FILTER (
        WHERE
            customer_type <> TRIM(customer_type)
    ), COUNT(*) FILTER (
        WHERE
            customer_type IS NULL
            OR TRIM(customer_type) = ''
    )
FROM bronze.customers
UNION ALL
SELECT 'packing.packing_type', COUNT(*) FILTER (
        WHERE
            packing_type <> TRIM(packing_type)
    ), COUNT(*) FILTER (
        WHERE
            packing_type IS NULL
            OR TRIM(packing_type) = ''
    )
FROM bronze.packing
UNION ALL
SELECT 'shipping.carrier', COUNT(*) FILTER (
        WHERE
            carrier <> TRIM(carrier)
    ), COUNT(*) FILTER (
        WHERE
            carrier IS NULL
            OR TRIM(carrier) = ''
    )
FROM bronze.shipping;

-- ------------------------------------------------------------
-- 4. DUPLICATE BUSINESS KEYS (Expected: ~0.5% except calendar = 0)
-- ------------------------------------------------------------
SELECT 'calendar.date' AS field, COUNT(*) - COUNT(DISTINCT date) AS duplicate_rows
FROM bronze.calendar
UNION ALL
SELECT 'customers.customer_id', COUNT(*) - COUNT(DISTINCT customer_id)
FROM bronze.customers
UNION ALL
SELECT 'product_master.product_id', COUNT(*) - COUNT(DISTINCT product_id)
FROM bronze.product_master
UNION ALL
SELECT 'locations.location_id', COUNT(*) - COUNT(DISTINCT location_id)
FROM bronze.locations
UNION ALL
SELECT 'inventory.inventory_id', COUNT(*) - COUNT(DISTINCT inventory_id)
FROM bronze.inventory
UNION ALL
SELECT 'orders.order_id', COUNT(*) - COUNT(DISTINCT order_id)
FROM bronze.orders
UNION ALL
SELECT 'order_items.order_item_id', COUNT(*) - COUNT(DISTINCT order_item_id)
FROM bronze.order_items
UNION ALL
SELECT 'picking.picking_id', COUNT(*) - COUNT(DISTINCT picking_id)
FROM bronze.picking
UNION ALL
SELECT 'packing.packing_id', COUNT(*) - COUNT(DISTINCT packing_id)
FROM bronze.packing
UNION ALL
SELECT 'shipping.shipment_id', COUNT(*) - COUNT(DISTINCT shipment_id)
FROM bronze.shipping;

-- ------------------------------------------------------------
-- 5. CATEGORY / CASING ANOMALIES (Sample)
-- ------------------------------------------------------------
SELECT
    'orders.delivery_priority' AS field,
    delivery_priority AS value,
    COUNT(*) AS row_count
FROM bronze.orders
GROUP BY
    delivery_priority
ORDER BY row_count DESC;

SELECT 'shipping.carrier' AS field, carrier AS value, COUNT(*) AS row_count
FROM bronze.shipping
GROUP BY
    carrier
ORDER BY row_count DESC;

SELECT
    current_database () AS db,
    current_user AS usr,
    inet_server_port () AS port,
    version() AS pg_version;