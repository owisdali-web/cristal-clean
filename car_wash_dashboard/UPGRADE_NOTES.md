# Crystal Clean Dashboard — 18.0.7.1

## Owl/QWeb hotfix
- Fixed the dashboard revenue donut crash caused by calling the JavaScript global `Number()` directly from a QWeb/OWL template expression.
- Added `formatAmount(value)` to the dashboard component and routed amount formatting through component methods that OWL can resolve safely.
- Added a regression test to prevent direct `Number()` constructor calls from returning to the QWeb template.

## Upgrade
Upgrade the existing `car_wash_dashboard` module, then hard-refresh the browser so Odoo rebuilds/serves the updated web assets.
