# 18.0.7.1 — Grid Layout Hotfix

## Root cause
The V7 template renders `.cc7-sidebar` before `.cc7-dashboard-scroll`.
The CSS used:

`grid-template-columns: 1fr 144px`

without explicit grid placement. In the affected browser/layout direction, the first
auto-placed child (sidebar) received the flexible `1fr` track, while the dashboard
was squeezed into the 144px track.

## Fix
- Named grid areas: `main side`
- Sidebar explicitly uses `grid-area: side`
- Dashboard explicitly uses `grid-area: main`
- `min-width: 0` added to the main grid item
- Responsive sidebar widths added
- No business logic, MRP, POS, inventory, accounting, automations or data changed.
