# Car Wash Dashboard 18.0.5.0 — Crystal Clean Concept Replica

- Rebuilds the client action to mirror the supplied `crystal-clean-dashboard-concept (2).html` visual language.
- Uses the supplied concept's embedded vehicle artwork as a bundled local WebP asset.
- Three tabs: Operations, Materials & Accounting, Customer Lounge.
- Live MRP/work-order/material/accounting values are read from the existing dashboard backend.
- POS tile intentionally remains unlinked until the upcoming POS migration phase; no fake POS numbers are shown.
- Visual scene controls (wait/wash/inspect/ready/delay) are presentation-only and never mutate operations.
- Keeps the proven 18.0.3.1 backend logic; no bus/realtime registry experiment is included in this visual-only release.
- 30-second read-only refresh remains active.
- Old SCSS files are left in the module for rollback/reference but are not loaded by `web.assets_backend`.
