-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Load Bronze Layer (run via psql because of \copy)
-- ============================================================

TRUNCATE TABLE bronze.calendar,
bronze.customers,
bronze.product_master,
bronze.locations,
bronze.inventory,
bronze.orders,
bronze.order_items,
bronze.picking,
bronze.packing,
bronze.shipping;

\copy bronze.calendar FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/processed/calendar.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.customers FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/customers.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.product_master FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/product_master.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.locations FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/locations.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.inventory FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/inventory.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.orders FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/orders.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.order_items FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/order_items.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.picking FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/picking.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.packing FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/packing.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\copy bronze.shipping FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/bronze/shipping.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');