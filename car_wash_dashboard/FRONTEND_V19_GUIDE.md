# Crystal Clean Car Wash — Frontend V19

Version: **18.0.19.0**

This release adds a completely new OWL 2 frontend on top of the existing headless backend contracts. No Python model, controller, security, or business-logic file was changed from 18.0.18.1.

## Client actions

- `crystal_clean_ops_center` — Operations Center for staff and managers.
- `crystal_clean_customer_display` — Waiting-room TV display.

## Menus

- Crystal Clean
  - مركز التشغيل
  - شاشة صالة الانتظار

The waiting-room menu is restricted to `car_wash_dashboard.group_car_wash_customer_display`.

## Backend contracts used

Operations Center:
- `get_station_topology()`
- `get_operations_data()`
- `get_queue_data()`
- `get_operational_intelligence_data()`
- `get_station_details(station_id)`
- manager-only: `get_management_data()` and `get_team_data()`

Customer Display:
- `get_customer_display_data()` only
- logo: `/car_wash/customer_display/logo`

## Realtime

The frontend subscribes to `crystal_clean_dashboard_<company_id>` and notification type `crystal_clean_dashboard_refresh`, coalesces bursts, and has a 60-second safety refresh while visible.

## Demo mode

Append `?cc_demo=1` to the URL to use frontend mock data. The mock set includes 12 stations, 16 cars, one overloaded station, and one unreliable ETA.

## Upgrade

Update the addon code, restart Odoo if required by the deployment, then upgrade:

```bash
./odoo-bin -d <database> -u car_wash_dashboard --stop-after-init
```

On Odoo.sh, push the addon and use the normal module upgrade flow.

## TV user

Create an internal user dedicated to the waiting-room screen and assign only the access it actually needs, including:

- `Car Wash Customer Display`

Do not grant Accounting, POS, Inventory, or MRP access solely for the TV screen. The display contract is permission-gated and sanitized by the backend.

Open **Crystal Clean → شاشة صالة الانتظار**, press **بدء العرض**, and the browser will request fullscreen when supported.

## Important semantics

- The dashboard is read-only; it never starts, completes, moves, or reassigns Work Orders.
- `overloaded` means actual occupancy is above configured capacity.
- Unreliable/missing ETA is shown as `قيد التقدير`.
- `operational_balance_today` is labelled `مؤشر تشغيلي وليس ربحاً محاسبياً`.
- Customer Display never renders customer names, phones, prices, payments, or employee names.
