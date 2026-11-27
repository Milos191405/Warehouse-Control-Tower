-- ============================================================
-- WAREHOUSE CONTROL TOWER
-- Gold Layer - Fire Protection & Safety Inspections
-- ============================================================

CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.fact_fire_safety CASCADE;

CREATE TABLE gold.fact_fire_safety (
    device_id                  VARCHAR(40) PRIMARY KEY,
    device_type                VARCHAR(30) NOT NULL,
    hall_id                    INTEGER NOT NULL,
    zone_nr                    INTEGER NOT NULL,
    area_label                 VARCHAR(80) NOT NULL,
    x_coord                    NUMERIC(6, 2) NOT NULL,
    y_coord                    NUMERIC(6, 2) NOT NULL,
    installation_date          DATE NOT NULL,
    inspection_frequency_days  INTEGER NOT NULL,
    last_inspection_date       DATE NOT NULL,
    next_inspection_due        DATE NOT NULL,
    days_until_due             INTEGER NOT NULL,
    inspection_status          VARCHAR(20) NOT NULL,
    inspector_id               VARCHAR(40) NOT NULL,
    pressure_bar               NUMERIC(5, 2) NOT NULL,
    notes                      TEXT
);

-- Load directly from processed CSV (run via psql because of \copy)
\copy gold.fact_fire_safety FROM 'C:/Users/milos/Desktop/milos/Projects/Warehouse Control Tower/data/processed/fire_safety.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

CREATE INDEX idx_fact_fire_hall_zone
    ON gold.fact_fire_safety (hall_id, zone_nr);

CREATE INDEX idx_fact_fire_status
    ON gold.fact_fire_safety (inspection_status);
