# -*- coding: utf-8 -*-
from odoo import models

class MrpProduction(models.Model):
    """ Extends MRP Production model for creating manufacturing orders from POS
    orders."""
    _inherit = 'mrp.production'

    def create_mrp_from_pos(self, products):
        """ Function for creating manufacturing orders with standard v18 logic."""
        product_ids = []
        if products:
            for product in products:
                if self.env['product.product'].browse(
                        int(product['id'])).to_make_mrp:
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
                    product_template_id = self.env['product.product'].browse(prod['id']).product_tmpl_id.id
                    bom_count = self.env['mrp.bom'].search([
                        ('product_tmpl_id', '=', product_template_id)])
                    
                    if bom_count:
                        bom_temp = self.env['mrp.bom'].search([
                            ('product_tmpl_id', '=', product_template_id),
                            ('product_id', '=', False)])
                        bom_prod = self.env['mrp.bom'].search([
                            ('product_id', '=', prod['id'])])
                        
                        if bom_prod:
                            bom = bom_prod[0]
                        elif bom_temp:
                            bom = bom_temp[0]
                        else:
                            bom = []
                        
                        if bom:
                            # 1. Gather all default values to prevent missing fields in v18
                            vals = {
                                'origin': 'POS-' + prod['pos_reference'],
                                'product_tmpl_id': product_template_id,
                                'product_id': prod['id'],
                                'product_uom_id': prod['uom_id'],
                                'product_qty': prod['qty'],
                                'bom_id': bom.id,
                            }
                            
                            # 2. Use Odoo virtual record cache to natively trigger operations/routing calculations
                            mo_cache = self.env['mrp.production'].new(vals)
                            mo_cache._onchange_product_id()  # Sets picking types, locations, and structural properties
                            mo_cache._onchange_bom_id()      # Pulls operations from BoM into virtual memory
                            
                            # Convert virtual data back into standard writable dictionary values
                            final_vals = mo_cache._convert_to_write(mo_cache._cache)
                            
                            # Ensure the fields are set cleanly
                            final_vals.update({
                                'origin': vals['origin'],
                                'product_qty': vals['product_qty'],
                            })
                            
                            # 3. Create the physical Manufacturing Order record in the database
                            mrp_order = self.sudo().create(final_vals)
                            
                            # 4. Generate the proper background Move Raw/Finished lines
                            mrp_order._pre_button_plan()
                            
                            # 5. Confirm and plan work centers into the Odoo Shop Floor app
                            mrp_order.action_confirm()
                            if mrp_order.workorder_ids:
                                mrp_order.button_plan()
                                
        return True
