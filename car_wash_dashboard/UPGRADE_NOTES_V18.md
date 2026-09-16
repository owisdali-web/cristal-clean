# 18.0.18.0 — Management Backend Contracts

Backend-only release. No dashboard JS/XML/CSS redesign.

## Added contracts

- `get_management_data()`
- `get_materials_data()`
- `get_customers_data()`
- `get_team_data()`

## Semantics corrected

- `operational_balance_today` is explicitly POS wash-service sales minus posted expenses. It is **not** accounting profit.
- Team analytics distinguish `currently_checked_in` from `worked_today`; neither is presented as an HR performance score.
- Customer metrics use `customers_served_today` and `active_customers_month`; they are not mislabeled as newly acquired customers.
- Station revenue is intentionally not allocated because one vehicle can pass through multiple Work Centers.
- Materials inventory is explicitly scoped to all internal company locations until a dedicated car-wash stock location is configured.

## Security

- Added `group_car_wash_manager` as an explicit API boundary.
- The group grants no direct model ACLs.
- System administrators remain authorized for diagnostics/deployment.

## Safety

No POS, MRP, Stock, Accounting, Work Order, Work Center, BOM, customer or HR records are created/updated/deleted by these contracts.
