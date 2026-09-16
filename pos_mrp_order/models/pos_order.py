# -*- coding: utf-8 -*-
# Based on "Make MRP Orders from POS" by Cybrosys Technologies (AGPL-3).
# Reworked to create MOs through procurement rules, exactly like Sales.
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.addons.stock.models.stock_rule import ProcurementException

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    mrp_production_count = fields.Integer(compute='_compute_mrp_production_count')

    def _compute_mrp_production_count(self):
        data = dict(self.env['mrp.production']._read_group(
            [('pos_order_id', 'in', self.ids)], ['pos_order_id'], ['__count']))
        for order in self:
            order.mrp_production_count = data.get(order, 0)

    # ------------------------------------------------------------------
    # Hook: called by the standard POS flow once the order is paid/synced
    # ------------------------------------------------------------------
    def _create_order_picking(self):
        res = super()._create_order_picking()
        # "Ship later" orders already go through lines._launch_stock_rule()
        # (the sales-like flow): products with MTO + Manufacture routes get
        # their MO from the standard rules, so we skip them to avoid duplicates.
        if not self.shipping_date:
            self._pos_launch_manufacture()
        return res

    def _pos_get_procurement_group(self):
        self.ensure_one()
        has_field = 'procurement_group_id' in self._fields
        group = self.procurement_group_id if has_field else self.env['procurement.group']
        if not group:
            group = self.env['procurement.group'].create({
                'name': self.name,
                'move_type': 'direct',
                'partner_id': self.partner_id.id,
                'pos_order_id': self.id,
            })
            if has_field:
                self.procurement_group_id = group
        elif not group.pos_order_id:
            group.pos_order_id = self.id
        return group

    def _pos_launch_manufacture(self):
        self.ensure_one()
        lines = self.lines.filtered(
            lambda l: l.product_id.to_make_mrp
            and l.product_id.type == 'consu'
            and l.qty > 0)
        if not lines:
            return

        order = self.sudo().with_company(self.company_id)
        route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
        picking_type = order.config_id.picking_type_id
        warehouse = picking_type.warehouse_id or self.env['stock.warehouse'].sudo().search(
            [('company_id', '=', order.company_id.id)], limit=1)
        if not route or not warehouse:
            _logger.warning("POS MRP: no Manufacture route/warehouse for %s", order.name)
            return

        location = picking_type.default_location_src_id or warehouse.lot_stock_id
        group = order._pos_get_procurement_group()
        now = fields.Datetime.now()
        ProcurementGroup = self.env['procurement.group'].sudo().with_company(order.company_id)

        procurements = []
        for line in lines:
            values = {
                'group_id': group,
                'date_planned': now,
                'date_deadline': now,
                'route_ids': route,
                'warehouse_id': warehouse,
                'partner_id': order.partner_id.id,
                'company_id': order.company_id,
            }
            procurements.append(ProcurementGroup.Procurement(
                line.product_id,
                line.qty,
                line.product_uom_id or line.product_id.uom_id,
                location,
                line.full_product_name or line.product_id.display_name,
                order.name,          # MO origin = POS order name (like SO name)
                order.company_id,
                values,
            ))

        # Never block the cashier: a missing BoM must not fail the POS sync.
        try:
            with self.env.cr.savepoint():
                ProcurementGroup.run(procurements)
        except (UserError, ProcurementException) as e:
            msg = str(getattr(e, 'procurement_exceptions', e))
            _logger.warning("POS MRP: could not create MO for %s: %s", order.name, msg)
            order.message_post(body=_("Manufacturing Order could not be created: %s", msg))

    def action_view_mrp_productions(self):
        self.ensure_one()
        productions = self.env['mrp.production'].search([('pos_order_id', '=', self.id)])
        action = self.env['ir.actions.act_window']._for_xml_id('mrp.mrp_production_action')
        action['context'] = {}
        if len(productions) == 1:
            action.update({
                'view_mode': 'form',
                'views': [(self.env.ref('mrp.mrp_production_form_view').id, 'form')],
                'res_id': productions.id,
            })
        else:
            action['domain'] = [('id', 'in', productions.ids)]
        return action
