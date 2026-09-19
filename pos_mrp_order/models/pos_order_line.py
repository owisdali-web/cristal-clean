# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create Delivery + MO through procurement rules, exactly like Sales.
from odoo import fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    pos_mrp_launched = fields.Boolean(
        copy=False,
        help="Technical: this line was sent to the MTO/Manufacture procurement, "
             "so it must not be added to the standard POS picking.")

    def _is_pos_mrp_line(self):
        self.ensure_one()
        return (self.product_id.to_make_mrp
                and self.product_id.type == 'consu'
                and self.qty > 0)
