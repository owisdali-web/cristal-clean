# Crystal Clean Dashboard 18.0.10.0

## Scope
- Preserves the approved main/home dashboard screen.
- Adds internal Sidebar pages matching the approved multi-screen reference: Vehicles, Appointments, Stations, Customers, Materials & Accounts, POS, Customer Screen, Reports, Maintenance.
- Pages use live Odoo data. No sample business records are created.
- Maintenance page degrades safely when the Maintenance app is not installed.
- Tajawal typography and FontAwesome isolation from V9.6 are preserved.

## Backend additions
- Customer visit/spend analytics from paid POS wash-service orders.
- 30-day material burn-rate and estimated days remaining from completed MRP raw-material moves.
- Workcenter efficiency / completed count.
- Optional maintenance equipment/request health summary.
- Report payload reusing real wash/POS/workcenter data.

## Deployment
Upgrade the existing module. Do not uninstall. Hard-refresh the browser after upgrade.
