# Crystal Clean Dashboard 18.0.15.0

## Scope
Backend only. No visual redesign.

## Added
- `get_operations_data()` lightweight live-operations contract.
- `get_queue_data()` read-only queue contract.
- `get_station_details(station_id)` station drill-down contract.
- Company-scoped queue logic derived from real MRP Work Orders.
- Diagnostics for overloaded stations, unassigned Work Orders, and Work Orders assigned outside the explicit car-wash topology.

## Explicit non-goals
- No Work Order reassignment.
- No automatic stage start/finish.
- No BOM/routing changes.
- No POS, Stock, Accounting, or Sale business-logic changes.
- No UI redesign.
