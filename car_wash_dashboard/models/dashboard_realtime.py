# -*- coding: utf-8 -*-
"""Realtime refresh signals for the Crystal Clean dashboard.

V4.0.4.1 registry-safe implementation.

IMPORTANT:
- No abstract mixin is inherited by mrp.production / mrp.workorder / sale.order.
- This avoids cloning the parent model field set through multiple _inherit, which
  can make auto-generated Many2many fields collide during Registry.setup_models().
- The helpers below only emit a lightweight refresh signal after real business
  records change. They never move, complete, cancel, reserve, consume or post.
"""

from odoo import api, fields, models


NOTIFICATION_TYPE = 'crystal_clean_dashboard_refresh'


def _unique_ints(values):
    return sorted({int(v) for v in values if v})


def _emit_dashboard_refresh(env, company_ids, reason, model_name, record_ids=None):
    """Emit a company-scoped dashboard refresh signal.

    The payload intentionally contains no customer, plate or vehicle details.
    The browser receives only a refresh hint and then reloads dashboard data
    through normal Odoo ORM/security.
    """
    if 'bus.bus' not in env.registry.models:
        return

    company_ids = _unique_ints(company_ids)
    record_ids = _unique_ints(record_ids or [])
    if not company_ids:
        company_ids = [env.company.id]

    payload_base = {
        'reason': reason,
        'model': model_name,
        'record_ids': record_ids[:30],
        'timestamp': fields.Datetime.to_string(fields.Datetime.now()),
    }
    bus = env['bus.bus']
    production = env['mrp.production']
    for company_id in company_ids:
        payload = dict(payload_base, company_id=company_id)
        bus._sendone(
            production._cw_dashboard_channel(company_id),
            NOTIFICATION_TYPE,
            payload,
        )


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    _CW_DASHBOARD_WATCH_FIELDS = {
        'state', 'date_start', 'date_finished', 'date_deadline',
        'reservation_state', 'workorder_ids', 'sale_line_id',
        'x_cc_is_wash_order', 'x_cc_service_product_id',
        'x_cc_vehicle_plate', 'x_cc_vehicle_model',
        'x_cc_vehicle_color', 'x_cc_vehicle_notes',
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        wash = records.filtered(lambda r: getattr(r, 'x_cc_is_wash_order', False))
        if wash:
            _emit_dashboard_refresh(
                self.env,
                wash.mapped('company_id').ids,
                'wash_order_created',
                self._name,
                wash.ids,
            )
        return records

    def write(self, vals):
        before = self.filtered(lambda r: getattr(r, 'x_cc_is_wash_order', False))
        company_ids = before.mapped('company_id').ids
        result = super().write(vals)
        after = self.filtered(lambda r: getattr(r, 'x_cc_is_wash_order', False))
        company_ids += after.mapped('company_id').ids
        if company_ids and (set(vals) & self._CW_DASHBOARD_WATCH_FIELDS):
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                'wash_order_updated',
                self._name,
                self.ids,
            )
        return result

    def unlink(self):
        wash = self.filtered(lambda r: getattr(r, 'x_cc_is_wash_order', False))
        company_ids = wash.mapped('company_id').ids
        record_ids = wash.ids
        result = super().unlink()
        if company_ids:
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                'wash_order_removed',
                self._name,
                record_ids,
            )
        return result


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    _CW_DASHBOARD_WATCH_FIELDS = {
        'state', 'workcenter_id', 'date_start', 'date_finished',
        'duration', 'duration_expected', 'production_id',
    }

    def _cw_wash_records(self):
        return self.filtered(
            lambda w: w.production_id
            and getattr(w.production_id, 'x_cc_is_wash_order', False)
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        wash = records._cw_wash_records()
        if wash:
            _emit_dashboard_refresh(
                self.env,
                wash.mapped('production_id.company_id').ids,
                'stage_created',
                self._name,
                wash.ids,
            )
        return records

    def write(self, vals):
        before = self._cw_wash_records()
        company_ids = before.mapped('production_id.company_id').ids
        result = super().write(vals)
        after = self._cw_wash_records()
        company_ids += after.mapped('production_id.company_id').ids
        if company_ids and (set(vals) & self._CW_DASHBOARD_WATCH_FIELDS):
            reason = 'stage_state_changed' if 'state' in vals else 'stage_updated'
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                reason,
                self._name,
                self.ids,
            )
        return result

    def unlink(self):
        wash = self._cw_wash_records()
        company_ids = wash.mapped('production_id.company_id').ids
        record_ids = wash.ids
        result = super().unlink()
        if company_ids:
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                'stage_removed',
                self._name,
                record_ids,
            )
        return result


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    _CW_DASHBOARD_WATCH_FIELDS = {
        'state', 'date_order', 'partner_id',
        'x_cc_vehicle_plate', 'x_cc_vehicle_make',
        'x_cc_vehicle_model', 'x_cc_vehicle_year',
        'x_cc_vehicle_color', 'x_cc_vehicle_notes',
    }

    def _cw_has_wash_service(self):
        template_model = self.env['product.template']
        if 'x_cc_recipe_bom_id' not in template_model._fields:
            return self.browse()
        return self.filtered(
            lambda order: any(
                line.product_id
                and line.product_id.product_tmpl_id.x_cc_recipe_bom_id
                for line in order.order_line
                if not line.display_type
            )
        )

    def write(self, vals):
        before = self._cw_has_wash_service()
        company_ids = before.mapped('company_id').ids
        result = super().write(vals)
        after = self._cw_has_wash_service()
        company_ids += after.mapped('company_id').ids
        if company_ids and (set(vals) & self._CW_DASHBOARD_WATCH_FIELDS):
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                'sale_updated',
                self._name,
                self.ids,
            )
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _cw_is_wash_line(self):
        template_model = self.env['product.template']
        if 'x_cc_recipe_bom_id' not in template_model._fields:
            return self.browse()
        return self.filtered(
            lambda line: bool(
                line.product_id
                and line.product_id.product_tmpl_id.x_cc_recipe_bom_id
                and not line.display_type
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        wash = records._cw_is_wash_line()
        if wash:
            _emit_dashboard_refresh(
                self.env,
                wash.mapped('order_id.company_id').ids,
                'sale_line_created',
                self._name,
                wash.ids,
            )
        return records

    def write(self, vals):
        before = self._cw_is_wash_line()
        company_ids = before.mapped('order_id.company_id').ids
        result = super().write(vals)
        after = self._cw_is_wash_line()
        company_ids += after.mapped('order_id.company_id').ids
        if company_ids:
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                'sale_line_updated',
                self._name,
                self.ids,
            )
        return result

    def unlink(self):
        wash = self._cw_is_wash_line()
        company_ids = wash.mapped('order_id.company_id').ids
        record_ids = wash.ids
        result = super().unlink()
        if company_ids:
            _emit_dashboard_refresh(
                self.env,
                company_ids,
                'sale_line_removed',
                self._name,
                record_ids,
            )
        return result
