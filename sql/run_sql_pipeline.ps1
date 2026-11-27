# ============================================================
# WAREHOUSE CONTROL TOWER
# Run full PostgreSQL pipeline: Bronze -> Silver -> Gold
# Usage (from project root, VS Code terminal):
#   .\sql\run_sql_pipeline.ps1
#   .\sql\run_sql_pipeline.ps1 -User postgres -Database warehouse_control_tower
# ============================================================

param(
    [string]$User = "postgres",
    [string]$Database = "warehouse_control_tower",
    [string]$DbHost = "localhost",
    [int]$Port = 5432,
    [int]$FromStep = 1
)

$ErrorActionPreference = "Stop"
$env:PGCLIENTENCODING = "UTF8"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$files = @(
    "sql/01_schema/01_create_schemas.sql",
    "sql/01_schema/02_create_bronze_tables.sql",
    "sql/02_staging/01_load_bronze.sql",
    "sql/02_staging/02_validate_bronze.sql",
    "sql/03_transformations/01_create_silver_tables.sql",
    "sql/03_transformations/02_transform_bronze_to_silver.sql",
    "sql/04_analytics/01_create_gold_star_schema.sql",
    "sql/04_analytics/02_create_gold_fire_safety.sql"
)

# Ask for password once (not stored anywhere, only for this session)
if (-not $env:PGPASSWORD) {
    $secure = Read-Host "Postgres password for user '$User'" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    )
}

try {
    # Create database if it does not exist
    $exists = psql -h $DbHost -p $Port -U $User -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$Database'"
    if ($LASTEXITCODE -ne 0) { throw "Cannot connect to PostgreSQL at ${DbHost}:${Port} as '$User'." }
    if (-not $exists) {
        Write-Host "Creating database '$Database' ..." -ForegroundColor Yellow
        psql -h $DbHost -p $Port -U $User -d postgres -c "CREATE DATABASE $Database"
    }

    $total = [Diagnostics.Stopwatch]::StartNew()
    $i = 0
    foreach ($f in $files) {
        $i++
        if ($i -lt $FromStep) {
            Write-Host "[$i/$($files.Count)] $f (skipped)" -ForegroundColor DarkGray
            continue
        }
        Write-Host ""
        Write-Host "[$i/$($files.Count)] $f" -ForegroundColor Cyan
        $sw = [Diagnostics.Stopwatch]::StartNew()
        psql -h $DbHost -p $Port -U $User -d $Database -v ON_ERROR_STOP=1 -q -f $f
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED at $f" -ForegroundColor Red
            exit 1
        }
        Write-Host ("  OK ({0:N1}s)" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Row counts (gold):" -ForegroundColor Cyan
    psql -h $DbHost -p $Port -U $User -d $Database -c @"
SELECT 'dim_calendar' AS table_name, COUNT(*) FROM gold.dim_calendar
UNION ALL SELECT 'dim_customers', COUNT(*) FROM gold.dim_customers
UNION ALL SELECT 'dim_products', COUNT(*) FROM gold.dim_products
UNION ALL SELECT 'dim_locations', COUNT(*) FROM gold.dim_locations
UNION ALL SELECT 'fact_orders_fulfillment', COUNT(*) FROM gold.fact_orders_fulfillment
UNION ALL SELECT 'fact_order_items', COUNT(*) FROM gold.fact_order_items
UNION ALL SELECT 'fact_picking', COUNT(*) FROM gold.fact_picking
UNION ALL SELECT 'fact_inventory_snapshot', COUNT(*) FROM gold.fact_inventory_snapshot
UNION ALL SELECT 'fact_fire_safety', COUNT(*) FROM gold.fact_fire_safety;
"@
    Write-Host ("DONE in {0:N1}s" -f $total.Elapsed.TotalSeconds) -ForegroundColor Green
}
finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
