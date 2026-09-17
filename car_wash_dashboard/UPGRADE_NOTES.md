# 18.0.6.7.2 — Frontend Arabic Translation Bundle Fix

This release fixes the root cause found by the Odoo Shell Arabic translation audit.

## Root cause fixed

Odoo 18 only sends JavaScript/OWL translations to the browser for modules returned by `ir.http._get_translation_frontend_modules_name()` (or its domain companion). `car_wash_dashboard` was not in that list, so `_t()` correctly existed in the source but the browser did not receive this module's Arabic catalog.

## Changes

- Added `models/ir_http.py` inheriting `ir.http`.
- Registered `car_wash_dashboard` in `_get_translation_frontend_modules_name()` while preserving the parent list and avoiding duplicates.
- Imported the new model from `models/__init__.py`.
- Added the missing lowercase `Station details` Arabic translation.
- Kept the existing Arabic RTL, English LTR, Crystal Clean identity, Light/Dark theme, operations dashboard, analytics, and drill-down behavior unchanged.
- The existing one active Work Order operating model remains unchanged; this translation fix does not delete or rewrite routing, and it never deletes historical Work Orders.
- Bumped the addon version to `18.0.6.7.2`.

## Expected Odoo Shell result after upgrade

The translation diagnostic should now include:

```text
PASS | car_wash_dashboard exposed to JS translation bundle | car_wash_dashboard
```

The current user's language must also be Arabic (for example `ar_001`) when visually verifying the Arabic dashboard in the browser.

---

# 18.0.6.7.1 — Full Arabic Translation Fix

- Routes every user-visible OWL template literal through Odoo runtime translation.
- Keeps Crystal Clean as the language-neutral brand name.
- Translates operational KPIs, queue, station cards/details, configuration warnings, Analytics, drill-down panels, tooltips, empty states, and filters.
- Preserves automatic RTL/LTR behavior from the Odoo user language.
- No changes to MRP, POS, stock, accounting, or dashboard data calculations.


## 18.0.6.4 — Interactive dashboard

- KPI cards are interactive filters inside the dashboard: active cars, waiting queue, available stations, and finished-today rows.
- Work Centers in the sidebar now opens an in-dashboard station directory; Settings remains the configuration action.
- Grid View toggles between grid and list presentation without leaving the dashboard.
- Station, KPI, navigation, refresh, and detail actions provide lightweight audible/visual feedback. Sound can be muted from the dashboard header.
- Finished Today now exposes the real completed-order rows for drill-down while preserving the existing KPI count.
- No Shop Floor, stock, accounting, or work-order mutation is introduced by these interactions.

# Upgrade Notes — Reference-Exact Station Dashboard

This release upgrades the existing `car_wash_dashboard` module in place. Do **not** uninstall the previous version.

V6.2 keeps the V6.1 operational migration and tightens the interface against the two approved reference images. It adds timing-backed progress presentation only when Odoo has a real expected Work Order duration; no demonstration percentages are invented.

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

The dashboard is locked to the approved reference images:

- CleanDrive sidebar
- header/search/user/date area
- four KPI cards
- one Waiting Queue panel
- 5×2 Work Center card grid on wide screens
- docked right-side station detail panel
- explicit internal vertical scrolling in the Odoo client action
- responsive layouts for narrower screens
- reference-derived sidebar wash artwork from the approved concept
- real Work Order elapsed/expected-duration progress bars in the wide layout
- `Finishing` visual state when real elapsed/expected progress reaches 85% or more
- progress bars are hidden in docked-detail mode to preserve the compact second reference layout

## Upgrade rules

- Do **not** uninstall the existing module.
- Do **not** delete the existing POS/MRP automations.
- Upgrade `car_wash_dashboard` in place.
- Validate on Odoo.sh staging before Live.

## 18.0.6.3 — Reference-style Small/Large vehicle renders

- Replaces the dashboard's cartoon pickup fallback with two high-quality reference-style vehicle renders.
- `Small` wash orders use `vehicle_small.webp`; `Large` wash orders use `vehicle_large.webp`.
- Queue, station cards, and the station detail panel share one resolver so the same vehicle stays visually consistent everywhere.
- Legacy pickup/van/truck/suv classifications gracefully fall back to the Large render; historical sedan/car records fall back to Small.
- This release changes presentation only; it does not start/finish Work Orders or change stock/accounting behavior.

## 18.0.6.4.1 — KPI interaction hotfix

- Fixes KPI card clicks raising `TypeError: Cannot read properties of undefined (reading 'state')`.
- Root cause: the KPI callback invoked `activateFocus()` without preserving the dashboard component instance.
- `activateFocus` is now explicitly bound during OWL setup.
- No MRP, stock, accounting, routing, or dashboard payload logic changed.

## 18.0.6.4.2 — Interactive callback binding hotfix

- Fixes OWL callback context loss for dashboard interactions, including opening a wash order from KPI focus results, queue rows, and station details.
- Binds all interactive dashboard handlers once during `setup()` so callbacks invoked by child components or inline OWL handlers retain the `CarWashDashboard` instance.
- No MRP, routing, inventory, accounting, or dashboard data-contract changes.

## 18.0.6.5 — Business Analytics Dashboard

- Added a second **Business Analytics** page inside the existing CleanDrive client action and sidebar.
- Added real POS-based revenue KPIs: today's revenue, monthly revenue, average ticket, washes today, and active customers.
- Added Daily Washes, Popular Services, Station Utilization, Top Customers, Revenue Trend, New vs Returning Customers, Revenue by Service Category, Recent Activity, and Supplies Near Depletion cards matching the approved CleanDrive analytics concept.
- Analytics revenue/service/customer metrics are restricted to products connected to car-wash work-center BoMs, avoiding unrelated POS sales.
- Low-stock warnings use real `stock.warehouse.orderpoint` minimum quantities only; no artificial threshold is introduced.
- Day/month boundaries follow the logged-in user's timezone.
- Analytics is read-only: no create/write/unlink business operations are performed by the analytics RPC or UI.
- Added `point_of_sale` as an explicit dependency because the management dashboard reads POS financial and customer metrics.

## 18.0.6.6 — Interactive Analytics Drill-down

- Business Analytics is no longer read-only presentation: KPI cards, chart points/bars, station utilization rows, customers, low-stock supplies, customer-mix segments, revenue categories, and recent activity now open a contextual drill-down panel inside the dashboard.
- Added read-only RPC `mrp.production.get_business_analytics_detail(detail_type, key, period)` with on-demand filtering so the summary payload stays compact.
- Drill-down rows can optionally open their original Odoo record (POS order, wash MO/work order, customer, supply product, or work center).
- Added stable click identifiers to analytics summary data (`bucket_key`, `product_id`, `week_index`, `category_id`, and recent-activity record references).
- No analytics interaction starts/finishes work orders or writes stock/accounting data.

## 18.0.6.7 — Crystal Clean identity, Arabic/English, Light/Dark

- Replaced the internal CleanDrive brand with the supplied **Crystal Clean** logo and `Crystal Clean / WASH CENTER` identity in the dashboard sidebar.
- The dashboard now follows the logged-in Odoo interface language: English stays LTR; Arabic uses the `ar_001` catalog and RTL layout.
- Expanded Arabic translations across Operations, Analytics, drill-down panels, statuses, navigation, empty states, feedback messages, and analytics backend detail labels.
- Added a dashboard-local **Light / Dark** toggle in the header. Light remains the default; the selected theme is persisted in browser storage when available.
- Dark mode is scoped to `.cw-dashboard-app` and does not change the rest of the Odoo backend appearance.
- Date, time, and currency formatting use the active document/Odoo locale where supported.
- No MRP, POS, stock, routing, accounting, or dashboard data-source logic is changed by this release.

## Translation extraction hardening in 18.0.6.7.2

- Added a literal UI translation catalog for every `tr(...)` string used by the OWL templates, eliminating dynamic `_t(variable)` calls from dashboard components.
- Removed the unused local Chart.js minified source that was not part of the addon asset bundle and caused a false-positive `_t()` diagnostic.

## 18.0.6.8 — Customer Lounge Display
- Added **Live Car Journey** as a child entry under **Customers** in the internal dashboard sidebar.
- Added a read-only customer lounge / TV display using the existing operational dashboard payload only.
- Added four customer-facing stages: Waiting, Washing, Drying / Finishing, Ready for Pickup.
- Added featured-vehicle rotation every two minutes, with newly ready vehicles taking immediate priority.
- Added ETA/progress/elapsed/expected presentation where real Odoo timing data exists.
- Added an **Up Next** badge for the first waiting vehicle.
- Added browser Full Screen / TV Mode for unattended large-screen use.
- Men's and women's waiting rooms use the same page/data source; no lounge-specific business logic was introduced.
- Added customer privacy boundary: customer names and phone numbers are not shown on the lounge screen.
- No business mutation RPC was added; POS/MRP/Stock/Accounting remain untouched by this page.
