# Crystal Clean Dashboard 18.0.14.0 — Station Topology Foundation

Backend/behavior foundation only. No dashboard visual redesign.

## Added
- Explicit topology fields on `mrp.workcenter`:
  - `cc_is_car_wash_station`
  - `cc_station_code`
  - `cc_station_order`
  - `cc_station_kind`
  - `cc_station_manual_state`
- Safe bootstrap for existing `CC-WC-A*` Work Centers on install/upgrade.
- Runtime states derived from real Work Orders: available, queued, busy, overloaded, maintenance, closed.
- Capacity/occupancy/queue/over-capacity payload.
- Dedicated `get_station_topology()` backend contract.
- Realtime dashboard refresh when station topology/configuration changes.

## Fixed
- Removed the JS assumption that slots 9/10 define automatic/polish roles.
- Removed fixed 10-slot placeholder construction; stations now follow backend topology order.
- Removed duplicate `selectStation` / `selectedStation` definitions.

## Explicitly untouched
- Work Center IDs/names/native codes/sequences/capacities.
- Existing Work Orders and their historical links.
- BoMs and routing operations.
- POS, Stock, Accounting and MRP business logic.
- Dashboard visual design/CSS/XML.
