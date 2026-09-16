# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create MOs through procurement rules, exactly like Sales.
from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    pos_order_id = fields.Many2one(
        'pos.order', string='POS Order',
        related='procurement_group_id.pos_order_id', store=True, index=True)

    def action_view_pos_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order',
            'res_id': self.pos_order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }
