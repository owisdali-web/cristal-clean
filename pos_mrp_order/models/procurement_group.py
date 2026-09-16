# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create MOs through procurement rules, exactly like Sales.
from odoo import fields, models


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    # Same idea as sale_id on procurement.group in sale_stock
    pos_order_id = fields.Many2one('pos.order', string='POS Order', index=True, copy=False)
