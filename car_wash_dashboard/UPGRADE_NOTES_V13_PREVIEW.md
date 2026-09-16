# Crystal Clean Dashboard 18.0.13.0 — PREVIEW

This is a review build, not a final client release.

## Preview focus
- Rebuilt A1–A10 station cards as modern operational control cards.
- A9 is fixed as automatic wash; A10 is fixed as polish/shine.
- Larger Cairo-first typography with Tajawal fallback.
- Dark / light theme toggle persisted per Odoo user.
- Station detail drawer: customer, phone, vehicle, plate, service, operations, timing, queue, completed-today, amount.
- Premium restrained animations: live pulse, active-station scan, progress transitions, customer lounge motion.
- Main page remains station-first, with only compact activity/material/team/alert panels underneath.
- Existing MRP/POS/stock/accounting business logic is not mutated by the visual preview.

## Important
- Static source validation passed, but this build still needs runtime review on the target Odoo.sh database before it is considered deliverable.
- Cairo is requested through the existing web-font link in the template; Tajawal remains the safe packaged Odoo fallback.
