# Car Wash Dashboard 18.0.6.1 — Validation & Staging Checklist

## Scope

V6.1 reproduces the approved station-centric concept while keeping Shop Floor authoritative for operational transitions.

The dashboard itself remains a read/command-navigation layer: it displays live Odoo state and opens the real Shop Floor / orders. It does not expose fake "finish" actions that bypass Odoo workflow.

## Expected post-upgrade station configuration

- A1-A8: Active, Dashboard Enabled, `General`
- A9: Active, Dashboard Enabled, `Automatic`
- A10: Active, Dashboard Enabled, `Polishing`
- Dashboard Sequence: A1=1 ... A10=10
- A1-A8: mutually configured as alternative General work centers
- A9/A10: no General alternative work centers

## Expected routing model

For the nine confirmed `CC-OPS-*` BoMs there must be one active routing operation after migration. Extra prior operations are archived, not deleted. Existing work orders created before the upgrade are intentionally left untouched.

Component and by-product operation references formerly attached to archived operations must point to the retained operation.

## Static build validation

Run from the addon directory:

```bash
python tests/test_v61_static.py -v
python -m compileall -q .
```

Also verify:

- XML/QWeb parsing
- JavaScript syntax
- CSS structural integrity
- manifest asset paths
- one top-level addon directory in the delivery ZIP

## Odoo.sh upgrade

Upgrade the existing module; do not install a second copy:

```bash
odoo-bin -d <database_name> -u car_wash_dashboard --stop-after-init
```

## Staging acceptance checklist

1. Registry loads with no module error.
2. Installed version = `18.0.6.1`.
3. Backend assets compile with no CSS/JS error.
4. Dashboard opens and vertical scrolling works from top to bottom.
5. All 10 real stations appear; no placeholder station remains.
6. A1-A8 show General, A9 Automatic, A10 Polishing.
7. One general queue is shown for all waiting cars.
8. A car with no in-progress Work Order appears in the queue.
9. Starting its Work Order in Shop Floor moves it from the queue to its station card after Bus refresh (or within the 30-second fallback period).
10. Only the current in-progress car appears inside a station.
11. Clicking a station opens the docked detail panel and keeps the page scroll usable.
12. Search filters station/queue content without changing Odoo records.
13. `Open Wash Screen` opens the standard Shop Floor action.
14. `Small / Large` is displayed only from explicit size data or the documented old-record service-name fallback.
15. New MOs linked to a Sale Order copy the explicit Small/Large value.
16. A late `x_cc_sale_order_ref` write also re-syncs the explicit size.
17. New MOs for the known service BoMs generate one active Work Order, not the old multi-station chain.
18. Automatic Wash routes to A9.
19. Paste/Shine routes to A10.
20. General services can be planned to A1-A8 via General alternatives.
21. No unknown/custom BoM was modified by migration.
22. Existing pre-upgrade Work Orders were not rewritten.
23. Bus messages contain only refresh metadata, not customer/vehicle details.
24. Today-based KPIs follow the logged-in user's Odoo timezone; configure the real user timezone correctly in Odoo.
25. Multi-company results are limited to the active company.

## Important note

The local build environment can statically validate the addon but cannot substitute for an actual Odoo 18 Enterprise registry upgrade. Treat the staging upgrade and checks above as the final runtime acceptance gate before Live.
