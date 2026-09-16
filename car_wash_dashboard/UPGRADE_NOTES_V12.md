# Crystal Clean Dashboard 18.0.12.0 — Digital Twin

- Real station codes A1..A10.
- A1..A8 are flexible wash stations.
- A9 is fixed for automatic wash.
- A10 is fixed for polish/shine.
- No dashboard sidebar; premium top navigation only: لوحة، زبائن، مواد ومالية، فريق، عملاء.
- Odoo navbar/control panel are hidden only while this dashboard component is mounted and restored on exit.
- Main page is station-first and designed to fit in one desktop viewport.
- Real Crystal Clean photos are bundled as local assets for hero, stations, lounge, team and customer pages.
- Customer lounge page is intentionally low-information and fullscreen-ready.
- Larger heavy Arabic typography: Cairo when browser/network can load it, with bundled Odoo Tajawal as safe fallback.
- Optional HR/customer/finance payloads are defensive so an unavailable optional model should not crash the whole dashboard RPC.
- Realtime bus remains refresh-only and does not mutate POS/MRP/accounting operations.
