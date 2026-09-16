# Crystal Clean Station Dashboard

Odoo 18 Enterprise frontend addon.

## Purpose
Adds a new "المحطات المباشرة" client action under the existing Crystal Clean car wash app.

## Dependency
Requires the existing `car_wash_dashboard` addon because the UI reads its backend methods:
- `mrp.production.get_operations_data()`
- fallback: `mrp.production.get_dashboard_data()`

## Safety
This addon does not modify MRP, POS, Accounting, Stock, Work Orders, or business records.
It is a frontend/read-only dashboard addon.

## Install
1. Copy `crystal_clean_station_dashboard` to your custom addons path.
2. Restart Odoo.
3. Update Apps List.
4. Install "Crystal Clean Station Dashboard".
