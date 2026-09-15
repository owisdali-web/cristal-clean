# POS Manual Delivery Validation — Odoo 18

This addon changes only the immediate stock transfer created by Point of Sale.

## Result

After a POS order is paid:

- the POS order remains **Paid**;
- a stock picking is created and linked to the POS order;
- available stock is reserved where possible;
- the picking remains **Ready / Waiting / Partially Available**;
- the picking is **not** marked picked;
- the picking is **not** validated or moved to Done automatically;
- the warehouse user must open Inventory and press **Validate** manually.

This mirrors the operational behavior of a normal Sales delivery order.

## Scope

- Odoo 18
- Point of Sale immediate deliveries
- Positive sales and POS returns are both left pending for warehouse validation
- No settings or menus are added
