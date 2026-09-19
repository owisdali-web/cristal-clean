# Customer Lounge Display Design

## Goal
Add a read-only customer-facing TV page to the existing Crystal Clean dashboard without changing the visual design or behavior of the Operations and Analytics pages.

## Navigation
The page is exposed as **Live Car Journey** as a child item directly under the existing **Customers** entry in the dashboard sidebar.

## Data source
The page reuses only the existing `mrp.production.get_dashboard_data()` payload:
- `queue` -> Waiting
- active station `current_car` -> Washing
- active station with `visual_status == finishing` -> Drying / Finishing
- `finished_today_items` -> Ready for Pickup

No new business records are created and no state-changing RPC is introduced.

## Customer experience
- One featured vehicle rotates every 120 seconds.
- Newly ready vehicles take immediate featured priority and trigger the existing optional success tone.
- Four live columns: Waiting, Washing, Drying / Finishing, Ready for Pickup.
- Vehicle model, plate, short ticket identifier, service, progress, elapsed/expected time, and contextual ETA are shown when available.
- First waiting vehicle receives an Up Next badge.
- Full Screen / TV Mode uses the browser Fullscreen API.
- Both men's and women's lounges use the same page and data source.
- When no vehicles are present, a branded Crystal Clean idle state is shown.

## Privacy
The page omits customer names and phone numbers. Vehicle identification uses model, plate, and a short ticket derived from the wash order id.

## Visual boundary
All new styles are scoped to `.cw-customer-display-page` and `.cw-nav-customer-group`. Existing Operations and Analytics page styling is not changed.
