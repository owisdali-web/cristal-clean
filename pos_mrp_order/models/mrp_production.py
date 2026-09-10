# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>
#    Author: Gayathri V (odoo@cybrosys.com)
#
#    you can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models


class MrpProduction(models.Model):
    """ Extends MRP Production model for creating manufacturing orders from POS
    orders."""
    _inherit = 'mrp.production'

    def create_mrp_from_pos(self, products):
        """ Create manufacturing orders for the POS order lines.

        The manufacturing order is created in ``draft`` state so that Odoo's
        own computed fields build the component moves (``move_raw_ids``) *and*
        the work orders / operations (``workorder_ids``) from the Bill of
        Material. ``action_confirm()`` then confirms those moves and work
        orders and links them together, exactly like a manually created MO.
        """
        if not products:
            return True

        # Aggregate the quantities of identical products across order lines.
        product_ids = []
        for product in products:
            if not self.env['product.product'].browse(
                    int(product['id'])).to_make_mrp:
                continue
            existing = next(
                (p for p in product_ids if p['id'] == product['id']), False)
            if existing:
                existing['qty'] += product['qty']
            else:
                product_ids.append(dict(product))

        for prod in product_ids:
            if prod['qty'] <= 0:
                continue

            product_template_id = self.env['product.product'].browse(
                int(prod['id'])).product_tmpl_id.id

            # A BoM tied to this exact variant wins over a template level BoM.
            bom_prod = self.env['mrp.bom'].search([
                ('product_id', '=', prod['id'])], limit=1)
            bom_temp = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', product_template_id),
                ('product_id', '=', False)], limit=1)
            bom = bom_prod or bom_temp
            if not bom:
                continue

            # Create the MO in draft: Odoo now computes move_raw_ids AND
            # workorder_ids (the operations) from the BoM automatically.
            mrp_order = self.sudo().create({
                'origin': 'POS-' + prod['pos_reference'],
                'product_id': prod['id'],
                'product_uom_id': prod['uom_id'],
                'product_qty': prod['qty'],
                'bom_id': bom.id,
            })

            # Confirm the MO: this confirms the component moves and the work
            # orders and links each move to its operation.
            mrp_order.action_confirm()

        return True
