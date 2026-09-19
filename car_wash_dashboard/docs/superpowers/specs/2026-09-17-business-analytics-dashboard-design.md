# Car Wash Business Analytics Dashboard Design

## Goal
Add a second, management-oriented dashboard page to the existing Odoo 18 Enterprise car-wash dashboard. The page must closely reproduce the approved CleanDrive analytics concept while using real Odoo data and safe empty states when a metric is unavailable.

## Navigation
The existing operational dashboard remains the default page. A new **Analytics** item appears in the custom left sidebar. Clicking it switches the client action to the analytics page without opening a separate Odoo list view. Clicking **Dashboard** returns to the operational station dashboard.

## Visual Contract
The analytics page follows the approved concept: white/blue CleanDrive visual language, rounded cards, compact spacing, soft shadows, consistent iconography, responsive grids, and no default Odoo list/form styling inside the analytics canvas.

The page contains:

1. KPI row: Today's Revenue, Monthly Revenue, Total Washes Today, Active Customers, Average Ticket.
2. Daily Washes line chart.
3. Popular Services bar chart.
4. Station Utilization donut with station legend.
5. Top Customers ranked list.
6. Supplies Near Depletion ranked list with quantity and threshold progress.
7. Revenue Trend bar chart for the current month.
8. New vs Returning Customers donut.
9. Revenue by Service Category donut.
10. Recent Activity list.

## Data Sources
- Wash counts and service popularity: `mrp.production` records flagged with `x_cc_is_wash_order=True`.
- Station utilization: `mrp.workorder` timing records attached to car-wash productions and dashboard-enabled work centers.
- Revenue, average ticket, customer counts, customer frequency, revenue trend, and category revenue: paid/done/invoiced `pos.order` and `pos.order.line` records for the current company.
- Low supplies: BOM component products used by operations assigned to car-wash work centers. A product is considered low only when a real replenishment minimum exists through a stock orderpoint. No arbitrary low-stock threshold is invented.
- Recent activity: recent wash MOs and POS payments, sorted by timestamp.

## Time Semantics
All period boundaries use the current Odoo user's timezone. "Today" means the user's local calendar day. "Monthly" means the user's current local calendar month. Comparisons use the previous local day or previous calendar month.

## Utilization Definition
Per-station utilization is busy work-order minutes divided by available capacity minutes during the selected period. If the work center has an Odoo resource calendar, its work hours are used for capacity; otherwise elapsed period minutes are used as a fallback. The percentage is capped at 100%.

## Interaction
Analytics is read-only. Charts and cards do not create, modify, start, finish, reserve, consume, invoice, or delete business records. The existing UI tone/toast feedback is preserved for navigation. The page provides a period selector for Today / This Month and refreshes analytics when the selection changes.

## Error and Empty States
Backend analytics retrieval is isolated from operational dashboard retrieval. If analytics cannot load, the operational dashboard remains usable and a notification is shown. Individual cards return zero/empty arrays instead of fabricating values. Low-stock shows an explicit empty state when no car-wash supply has a configured replenishment minimum.

## Compatibility
Target: Odoo 18 Enterprise. Existing operational dashboard behavior, MRP routing, Shop Floor behavior, realtime station refresh, vehicle visuals, and KPI drill-down behavior must remain unchanged.
