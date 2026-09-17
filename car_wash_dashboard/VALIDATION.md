
## V6.4 Interactive validation

- KPI cards drill down inside the dashboard to active cars, waiting cars, available stations, or completed-today orders.
- Work Centers opens an in-dashboard station directory; Settings remains the Odoo configuration action.
- Grid/List view toggling is client-side and does not mutate operational records.
- A lightweight Web Audio tone and a visual toast provide click feedback; sound can be muted from the header.
- Finished Today detail rows are sourced from the same company-scoped/date-scoped MRP domain as the KPI.
- No interactive dashboard handler starts, finishes, cancels, creates, writes, or unlinks MRP/stock/accounting records.

# Car Wash Dashboard 18.0.6.3 — Validation & Staging Checklist

## Scope

V6.2 reproduces the approved station-centric reference images while keeping Shop Floor authoritative for operational transitions.

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
python tests/test_v62_static.py -v
python tests/test_v62_visual_contract.py -v
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
2. Installed version = `18.0.6.3`.
3. Backend assets compile with no CSS/JS error.
4. Dashboard opens and vertical scrolling works from top to bottom.
5. Wide layout visually follows the approved reference: 210px sidebar, four KPI cards, one queue column, 5×2 station grid.
6. When a station is selected, the 330px docked details panel appears and the station cards compact like the second reference image.
7. Progress percentages appear only when the Work Order has a real positive `duration_expected`; no fake percentage is shown.
8. All 10 real stations appear; no placeholder station remains.
9. A1-A8 show General, A9 Automatic, A10 Polishing.
10. One general queue is shown for all waiting cars.
11. A car with no in-progress Work Order appears in the queue.
12. Starting its Work Order in Shop Floor moves it from the queue to its station card after Bus refresh (or within the 30-second fallback period).
13. Only the current in-progress car appears inside a station.
14. Clicking a station opens the docked detail panel and keeps the page scroll usable.
15. Search filters station/queue content without changing Odoo records.
16. `Open Wash Screen` opens the standard Shop Floor action.
17. `Small / Large` is displayed only from explicit size data or the documented old-record service-name fallback.
18. New MOs linked to a Sale Order copy the explicit Small/Large value.
19. A late `x_cc_sale_order_ref` write also re-syncs the explicit size.
20. New MOs for the known service BoMs generate one active Work Order, not the old multi-station chain.
21. Automatic Wash routes to A9.
22. Paste/Shine routes to A10.
23. General services can be planned to A1-A8 via General alternatives.
24. No unknown/custom BoM was modified by migration.
25. Existing pre-upgrade Work Orders were not rewritten.
26. Bus messages contain only refresh metadata, not customer/vehicle details.
27. Today-based KPIs follow the logged-in user's Odoo timezone; configure the real user timezone correctly in Odoo.
28. Multi-company results are limited to the active company.

## Important note

The local build environment can statically validate the addon but cannot substitute for an actual Odoo 18 Enterprise registry upgrade. Treat the staging upgrade and checks above as the final runtime acceptance gate before Live.

## 18.0.6.5 Business Analytics validation

- Business analytics static contract tests cover backend payload keys, POS dependency, sidebar navigation, analytics RPC wiring, approved chart/card sections, and analytics CSS classes.
- The analytics backend is read-only and has no `.create()`, `.write()`, or `.unlink()` calls.
- Charts are rendered with OWL/QWeb + SVG/CSS and do not add a new runtime chart dependency.
- Existing operations dashboard remains the default page and keeps station KPI drill-down, realtime bus refresh, sound feedback, and station detail behavior.
