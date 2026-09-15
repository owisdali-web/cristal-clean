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
        """Function for creating manufacturing orders from POS orders."""
        product_ids = []
        if products:
            for product in products:
                if self.env['product.product'].browse(int(product['id'])).to_make_mrp:
                    flag = 1
                    if product_ids:
                        for product_id in product_ids:
                            if product_id['id'] == product['id']:
                                product_id['qty'] += product['qty']
                                flag = 0
                    if flag:
                        product_ids.append(product)

            for prod in product_ids:
                if prod['qty'] > 0:
                    product_template_id = self.env['product.product'].browse(
                        prod['id']).product_tmpl_id.id
                    bom_count = self.env['mrp.bom'].search(
                        [('product_tmpl_id', '=', product_template_id)])
                    if bom_count:
                        bom_temp = self.env['mrp.bom'].search([
                            ('product_tmpl_id', '=', product_template_id),
                            ('product_id', '=', False)
                        ])
                        bom_prod = self.env['mrp.bom'].search(
                            [('product_id', '=', prod['id'])])
                        if bom_prod:
                            bom = bom_prod[0]
                        elif bom_temp:
                            bom = bom_temp[0]
                        else:
                            bom = []

                        if bom:
                            # Safely get the routing ID (if the field exists)
                            routing_id = getattr(bom, 'routing_id', False)
                            routing_id = routing_id.id if routing_id else False

                            vals = {
                                'origin': 'POS-' + prod['pos_reference'],
                                'state': 'confirmed',
                                'product_tmpl_id': product_template_id,
                                'product_id': prod['id'],
                                'product_uom_id': prod['uom_id'],
                                'product_qty': prod['qty'],
                                'bom_id': bom.id,
                                'routing_id': routing_id,
                            }
                            mrp_order = self.sudo().create(vals)

                            # Generate work orders if a routing is set
                            if mrp_order.routing_id:
                                mrp_order._generate_workorders()

                            # --- USE THE STANDARD POS METHOD FOR CREATING THE DELIVERY ORDER ---
                            # Find the POS order that triggered this
                            pos_order = self.env['pos.order'].search([
                                ('pos_reference', '=', prod['pos_reference'])
                            ], limit=1)

                            if pos_order:
                                # Get the delivery picking type from the POS config
                                picking_type = pos_order.config_id.picking_type_id

                                # Create the picking using the standard method
                                pos_order._create_picking_from_pos_order_lines(
                                    location_dest_id=picking_type.default_location_dest_id.id,
                                    lines=pos_order.lines,
                                    picking_type=picking_type,
                                    partner=pos_order.partner_id,
                                )

        return True
