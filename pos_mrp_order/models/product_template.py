# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create MOs through procurement rules, exactly like Sales.
from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    to_make_mrp = fields.Boolean(
        string='To Create MRP Order',
        help="Create a Manufacturing Order when this product is sold in POS.")

    @api.onchange('to_make_mrp')
    def _onchange_to_make_mrp(self):
        if self.to_make_mrp and not self.bom_count:
            return {'warning': {
                'title': _('No Bill of Materials'),
                'message': _('Please set a Bill of Materials for this product, '
                             'otherwise no Manufacturing Order can be created.'),
            }}
