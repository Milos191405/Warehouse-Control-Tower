-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Bronze Layer Validation
-- ============================================================

-- ------------------------------------------------------------
-- 1. ROW COUNTS
-- ------------------------------------------------------------

SELECT 'product_master' AS table_name, COUNT(*) AS row_count
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
-- 2. MISSING VALUES
-- ------------------------------------------------------------

SELECT
    'product_master' AS table_name,
    COUNT(*) FILTER (
        WHERE
            product_id IS NULL
            OR TRIM(product_id) = ''
    ) AS missing_product_id,
    COUNT(*) FILTER (
        WHERE
            article_number IS NULL
            OR TRIM(article_number) = ''
    ) AS missing_article_number
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
-- 3. WHITESPACE ISSUES
-- ------------------------------------------------------------

SELECT 'orders.order_id' AS field, COUNT(*) AS whitespace_issues
FROM bronze.orders
WHERE
    order_id <> TRIM(order_id)
UNION ALL
SELECT 'inventory.product_id', COUNT(*)
FROM bronze.inventory
WHERE
    product_id <> TRIM(product_id)
UNION ALL
SELECT 'picking.order_id', COUNT(*)
FROM bronze.picking
WHERE
    order_id <> TRIM(order_id)
UNION ALL
SELECT 'packing.order_id', COUNT(*)
FROM bronze.packing
WHERE
    order_id <> TRIM(order_id)
UNION ALL
SELECT 'shipping.order_id', COUNT(*)
FROM bronze.shipping
WHERE
    order_id <> TRIM(order_id);

-- ------------------------------------------------------------
-- 4. DUPLICATE BUSINESS KEYS
-- ------------------------------------------------------------

SELECT 'product_master.product_id' AS field, COUNT(*) - COUNT(DISTINCT product_id) AS duplicate_rows
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
-- 5. CATEGORY / STATUS VALUES
-- ------------------------------------------------------------

SELECT
    'orders.delivery_priority' AS field,
    delivery_priority AS value,
    COUNT(*) AS row_count
FROM bronze.orders
GROUP BY
    delivery_priority
ORDER BY row_count DESC;

SELECT 'inventory.storage_type' AS field, storage_type AS value, COUNT(*) AS row_count
FROM bronze.inventory
GROUP BY
    storage_type
ORDER BY row_count DESC;

SELECT 'inventory.picking_method' AS field, picking_method AS value, COUNT(*) AS row_count
FROM bronze.inventory
GROUP BY
    picking_method
ORDER BY row_count DESC;

SELECT 'shipping.shipping_method' AS field, shipping_method AS value, COUNT(*) AS row_count
FROM bronze.shipping
GROUP BY
    shipping_method
ORDER BY row_count DESC;