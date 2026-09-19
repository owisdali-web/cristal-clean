# Customers 360 Design

## Goal
Turn the existing Customers sidebar item from a standard Odoo partner list action into an internal, read-only Customer Intelligence page inside the car-wash dashboard.

## Scope
The page is for managers/staff, while Live Car Journey remains the separate public waiting-room screen under Customers.

## Data sources
- Customer identity: `res.partner` from paid car-wash POS orders.
- Revenue/visits/services: paid POS orders/lines scoped to car-wash service products.
- Wash history and station history: `mrp.production` / `mrp.workorder` when linked to the customer through the project’s existing sale/wash references.
- Vehicle information: existing car-wash sale/MO fields; do not invent a new vehicle master in this version.

## UI
1. KPI row: Total Customers, New This Month, Returning, Frequent, Inactive, Average Spend.
2. Search/filter bar: customer/name/phone/plate search; segment filter; service filter; activity period.
3. Customer list/cards: name, phone, visits, total spend, average ticket, last visit, preferred service, known vehicle count, segment badge.
4. Customer 360 panel: identity, KPI summary, known vehicles, POS/wash visit timeline, services, spend, latest activity, and Open Customer in Odoo.
5. Interactive charts: Top Customers by Revenue, Most Frequent Customers, New vs Returning, Service Preferences. Clicking filters the list.
6. Segments: New, Regular, Frequent, High Value, Inactive. Thresholds are deterministic defaults in this version and are shown in backend constants; no settings UI yet.
7. Read-only. No automated WhatsApp or customer mutation in this release.

## Privacy
Internal page may show customer contact data to authorized internal users, but public Customer Display remains privacy-minimized and unchanged.

## Localization
Every new Customers 360 label uses the same English/Arabic localization layer and respects RTL/LTR automatically.

## Success criteria
- Customers sidebar opens the in-dashboard Customers page.
- Live Car Journey remains nested and separately accessible.
- Backend uses paid POS data for revenue/visits.
- KPI/list/detail/chart data is read-only and company-scoped.
- Clicking KPI/chart/customer filters or opens Customer 360 detail without leaving the page; Open in Odoo is explicit.
- All new UI labels have Arabic translations.
