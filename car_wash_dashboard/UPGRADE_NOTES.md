# Crystal Clean Dashboard — 18.0.7.0

## Premium dashboard redesign
- Rebuilt the dashboard shell to match the approved full-screen premium concept.
- Added an internal left sidebar for Overview, Automatic Wash, Manual Wash, and Reports.
- Added a top toolbar with search, refresh, fullscreen, current user, and company identity.
- Rebuilt the overview with five KPI cards, large automatic/manual wash feature scenes, station status, queue, average service time, and revenue split.
- Automatic/manual comparison data is loaded from separate filtered Odoo payloads; no demo revenue or vehicle counts are used.
- Added real small/large vehicle counts by grouping the existing Odoo vehicle types (`car` vs `truck/van/pickup`).
- Preserved the existing `wash_method` model, menu actions, automatic/manual detailed dashboards, reports, and legacy compatibility.
- No historical `wash_type` values are changed.
