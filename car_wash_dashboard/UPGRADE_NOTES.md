# 18.0.6.9.1 — Report Center Runtime Hotfix

This hotfix fixes the Report Center RPC failure seen immediately after opening the Reports page on Odoo 18.

## Root cause
`pos.order.line.search()` was called with `order='order_id.date_order asc, id asc'`. Odoo 18 does not accept a relational field path in the `order` argument for this model, so the Reports RPC failed with:

`ValueError: Invalid field 'order_id.date_order' on model 'pos.order.line'`

## Fix
- Search POS lines with the valid local field order `id asc`.
- Apply the required chronological order in Python using the related POS order `date_order`, then line `id` as the stable tie-breaker.
- No report formulas, filters, visuals, export routes, POS state rules, MRP logic, stock logic, or accounting logic were changed.

## Upgrade
Upgrade the existing module in place. Do not uninstall it.

## Preserved operational contract
The existing car-wash routing contract is unchanged: one active Work Order is expected for the current wash-service routing flow. This hotfix does not delete routing history; historical Work Orders remain preserved instead of deleting operational records.
