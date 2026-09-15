# Crystal Clean Dashboard 18.0.8.0 — V8 LIVE SHOW

## New application pages
- Main operations control center focused on 10 wash stations.
- Customer lounge screen with automatic rotating vehicle spotlight and fullscreen mode.
- Materials & Accounts page with stock, POS sales, invoices, receivables/payables, expenses and recent accounting moves.
- POS page with today's wash orders, service mix, hourly sales and direct Odoo POS navigation.

## Station show
- Each station shows only the actual vehicle size (small or large).
- All unfinished requested operations appear as chips; one operation is automatically spotlighted every ~2.8 seconds.
- Animated operation layers: water, foam, automatic brushes, interior/vacuum effect and polish sparkles.
- Automatic wash and polish stations receive dedicated visual treatment.

## Realtime automation
- Company-scoped Odoo bus refresh signals from normal MRP, Work Order, POS and accounting writes.
- Signals never start/finish stages or mutate operational data.
- 15-second polling remains a fallback.

## Safety
- No inventory consumption, accounting posting, POS validation, MRP completion or workorder transition is automated by the dashboard.
- Shop Floor and POS remain sources of truth.
- No AbstractModel multi-inheritance is used.
