# Upgrade to 18.0.6.1 — Concept-Exact Station Dashboard

This release upgrades the existing `car_wash_dashboard` module in place. Do **not** uninstall the previous version.

## Approved operating model

- One general waiting queue for the whole car wash.
- Ten physical rooms: A1-A8 General, A9 Automatic, A10 Polishing.
- One customer service creates **one active Work Order in one physical station**.
- The car remains in that station until the service is completed.
- Shop Floor remains the operational source of truth for starting/finishing work.

## Post-migration behavior

When a company contains the complete A1-A10 set, the migration:

1. Reactivates A1-A10.
2. Enables all ten stations on the dashboard and assigns sequence 1..10.
3. Configures A1-A8 as `General`, A9 as `Automatic`, and A10 as `Polishing`.
4. Configures A1-A8 as mutual Odoo alternative work centers so a General service can be planned in any General room.
5. Keeps A9 and A10 restricted by clearing their alternative work-center lists.
6. Consolidates only the nine confirmed `CC-OPS-*` operational BoMs to one active operation:
   - `CC-OPS-AUTO` → A9
   - `CC-OPS-PASTE` / `CC-OPS-SHINE` → A10
   - the other confirmed wash services → one General operation
7. Archives extra operations instead of deleting them.
8. Moves any component/by-product operation references from archived operations to the retained operation so material links are preserved.

Unknown/custom BoMs are not modified. Existing already-generated Work Orders are not rewritten; the new routing applies to Work Orders generated after the upgrade.

## Vehicle size

`car_wash_vehicle_size` is a new explicit `Small / Large` field on Sale Order and Manufacturing Order. It is not guessed from legacy `vehicle_type` values (`car`, `truck`, `van`, `pickup`). Old records may still use an explicit small/large phrase in the service name as a display fallback.

## Realtime

Odoo Bus sends only a company-scoped refresh signal. The browser then refetches `get_dashboard_data()` using normal ACLs. A 30-second polling fallback remains enabled.

The Bus does not start/finish Work Orders, change stock, post accounting, or carry customer/vehicle details.

## Frontend

The dashboard was rebuilt around the approved reference images:

- CleanDrive sidebar
- header/search/user/date area
- four KPI cards
- one Waiting Queue panel
- 5×2 Work Center card grid on wide screens
- docked right-side station detail panel
- explicit internal vertical scrolling in the Odoo client action
- responsive layouts for narrower screens

## Upgrade rules

- Do **not** uninstall the existing module.
- Do **not** delete the existing POS/MRP automations.
- Upgrade `car_wash_dashboard` in place.
- Validate on Odoo.sh staging before Live.
