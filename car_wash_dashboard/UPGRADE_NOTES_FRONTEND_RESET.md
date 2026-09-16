# 18.0.18.1 — Frontend Reset / Headless Handoff

Backend-only cleanup release for rebuilding the UI from zero.

- Removed all legacy dashboard frontend assets and visual prototypes.
- Removed old dashboard client action and menus on upgrade.
- Removed dashboard theme preference field/setter.
- Removed old dashboard frontend HTTP endpoint.
- Preserved V14–V18 backend contracts, station topology, realtime signals, security and business extensions.
- No POS, Stock, Accounting, MRP, BoM, Work Order or historical record business logic is changed by this release.
