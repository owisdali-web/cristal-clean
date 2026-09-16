# Car Wash Dashboard 18.0.6.0 — Validation & Upgrade Notes

## Scope

This version replaces the previous analytics-heavy dashboard screen with the approved station-centric concept while preserving the existing Odoo operational flow.

The dashboard is intentionally read-only for business state. It does **not** start or finish work orders, consume inventory, post accounting entries, or modify sale orders. Shop Floor remains the operational source of truth.

## What Changed

- One general waiting queue for the entire car wash.
- Ten visual station slots.
- One station can be configured as `Automatic`.
- One station can be configured as `Polishing`.
- Eight stations can be configured as `General`.
- Each real station card shows only the current car whose work order is actually in `progress` in that work center.
- Station details open in a right-side drawer.
- Four KPIs only: Active Cars, Waiting Queue, Available Stations, Finished Today.
- Station configuration is stored on `mrp.workcenter`; database IDs are never hard-coded.
- If no station configuration exists yet, the dashboard uses a non-writing backward-compatible fallback based on current active work centers and station names. It displays a configuration warning until the stations are explicitly configured.
- If fewer than 10 real stations exist, the remaining slots are visual placeholders only; no fake work centers are created.

## Required Post-Upgrade Configuration

Open **Car Wash → Station Configuration** and configure the 10 real work centers:

1. Enable `Show on Car Wash Dashboard` for each real wash room/station.
2. Set `Dashboard Sequence` from 1 to 10.
3. Set exactly one station to `Automatic`.
4. Set exactly one station to `Polishing`.
5. Set the remaining eight stations to `General`.

The module does not create or delete work centers during installation or upgrade.

## Static Validation Performed During Build

- Python source compilation.
- XML/QWeb parsing.
- JavaScript syntax checks with Node.
- Manifest path validation.
- CSS brace validation.
- Security check preventing the old broad `base.group_user` MRP read ACL.
- Read-only source scan for dashboard business mutations.
- Pure dashboard logic tests for vehicle-size normalization, station-type fallback, 10-slot layout, and station conflict grouping.

## Odoo.sh Staging Acceptance

Final runtime acceptance must be performed on a staging/dev branch because this build environment does not contain the Odoo 18 runtime.

### Upgrade

Upgrade the existing module; do not install a second competing dashboard module:

```bash
odoo-bin -d <database_name> -u car_wash_dashboard --stop-after-init
```

On Odoo.sh, normally push the module to Git and use the Apps upgrade flow or the build shell command appropriate to the branch.

### Acceptance Checklist

1. Registry loads with no module error.
2. `car_wash_dashboard` shows installed version `18.0.6.0`.
3. Backend assets compile without SCSS/CSS/JS errors.
4. **Car Wash → Dashboard** opens successfully for an MRP user.
5. Dashboard shows one general queue only.
6. A wash order with no `mrp.workorder` in `progress` appears in the queue.
7. Starting the real Shop Floor work order removes that car from the general queue.
8. The correct work center card shows that car as the current vehicle.
9. The card shows the real service and available vehicle/customer fields without fabricated values.
10. Loading or refreshing the dashboard performs no writes to `mrp.production`, `mrp.workorder`, `stock`, `account.move`, or `sale.order`.
11. Work-center data is limited to the user's active company.
12. A station with two distinct in-progress wash orders shows a conflict state instead of hiding one of the cars.
13. `Open Wash Screen` opens `mrp_workorder.action_mrp_display`.
14. Configure all 10 stations and confirm the configuration warning disappears.
15. Confirm one Automatic, one Polishing, and eight General station badges.

## Important Runtime Note

The dashboard determines **physical occupancy** from `mrp.workorder.state == 'progress'`. Ready/waiting/pending work orders are treated as part of the general queue until a real operation is started. This intentionally prevents the old per-work-center queue model from appearing on the new dashboard.
