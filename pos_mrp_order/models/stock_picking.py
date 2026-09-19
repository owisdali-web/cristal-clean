# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create Delivery + MO through procurement rules, exactly like Sales.
from odoo import api, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        # Used both in real time and at session closing: skip lines already
        # delivered through the Sales-like MTO flow (avoid double stock moves).
        lines = lines.filtered(lambda l: not l.pos_mrp_launched)
        if not lines:
            return self.env['stock.picking']
        return super()._create_picking_from_pos_order_lines(
            location_dest_id, lines, picking_type, partner)
