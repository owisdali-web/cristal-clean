# 18.0.6.9.2 — Dynamic Work Centers

- The operational Dashboard no longer pads the work-center area to 10 visual slots.
- Only active Odoo work centers with `car_wash_enabled = True` are returned and rendered.
- `Work Centers (N)` and `Available Stations: X of N` now use the real configured count.
- The station grid adapts automatically to 1–6+ configured centers and remains responsive on tablet/mobile.
- Fixed-count warnings (10 total / 8 general) were removed; adding or archiving/enabling a work center changes the Dashboard without code changes.
- Reports, Analytics, Customer Display, POS/MRP business logic, stock, and accounting were not changed by this release.

## Preserved routing guarantees

- Each car-wash service remains designed to produce **one active Work Order** for the current operation flow.
- Upgrade/migration logic **does not delete** historical MRP production or Work Order history; inactive legacy routing records are preserved instead of deleting operational history.
