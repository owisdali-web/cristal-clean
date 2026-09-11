# -*- coding: utf-8 -*-
"""Realtime refresh signals for the Crystal Clean dashboard.

This file intentionally does NOT automate operational decisions. It never starts,
finishes, moves, cancels, reserves or consumes a wash order. It only emits a tiny
company-scoped bus signal after real Odoo records change. The browser then reloads
the dashboard through normal Odoo access rules.

This means Shop Floor remains the operational source of truth while the dashboard
becomes visually realtime.
"""

from odoo import api, fields, models


NOTIFICATION_TYPE = 'crystal_clean_dashboard_refresh'


def _unique_ints(values):
    return sorted({int(v) for v in values if v})


class CrystalCleanDashboardRealtimeMixin(models.AbstractModel):
    _name = 'crystal.clean.dashboard.realtime.mixin'
    _description = 'Crystal Clean Dashboard Realtime Helper'

    @api.model
    def _cw_emit_dashboard_refresh(self, company_ids, reason, model_name, record_ids=None):
        if 'bus.bus' not in self.env.registry.models:
            return

        company_ids = _unique_ints(company_ids)
        record_ids = _unique_ints(record_ids or [])
        if not company_ids:
            company_ids = [self.env.company.id]

        payload_base = {
            'reason': reason,
            'model': model_name,
            'record_ids': record_ids[:30],
            'timestamp': fields.Datetime.to_string(fields.Datetime.now()),
        }
        bus = self.env['bus.bus']
        production = self.env['mrp.production']
        for company_id in company_ids:
            payload = dict(payload_base, company_id=company_id)
            bus._sendone(
                production._cw_dashboard_channel(company_id),
                NOTIFICATION_TYPE,
                payload,
            )


class MrpProduction(models.Model):
    _inherit = ['mrp.production', 'crystal.clean.dashboard.realtime.mixin']

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
            self._cw_emit_dashboard_refresh(
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
            self._cw_emit_dashboard_refresh(
                company_ids,
                'wash_order_updated',
                self._name,
                self.ids,
            )
        return result

    def unlink(self):
        wash = self.filtered(lambda r: getattr(r, 'x_cc_is_wash_order', False))
        company_ids = wash.mapped('company_id').ids
        ids = wash.ids
        result = super().unlink()
        if company_ids:
            self._cw_emit_dashboard_refresh(
                company_ids,
                'wash_order_removed',
                self._name,
                ids,
            )
        return result


class MrpWorkorder(models.Model):
    _inherit = ['mrp.workorder', 'crystal.clean.dashboard.realtime.mixin']

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
            self._cw_emit_dashboard_refresh(
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
            self._cw_emit_dashboard_refresh(
                company_ids,
                reason,
                self._name,
                self.ids,
            )
        return result

    def unlink(self):
        wash = self._cw_wash_records()
        company_ids = wash.mapped('production_id.company_id').ids
        ids = wash.ids
        result = super().unlink()
        if company_ids:
            self._cw_emit_dashboard_refresh(
                company_ids,
                'stage_removed',
                self._name,
                ids,
            )
        return result


class SaleOrder(models.Model):
    _inherit = ['sale.order', 'crystal.clean.dashboard.realtime.mixin']

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
            self._cw_emit_dashboard_refresh(
                company_ids,
                'sale_updated',
                self._name,
                self.ids,
            )
        return result


class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line', 'crystal.clean.dashboard.realtime.mixin']

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
            self._cw_emit_dashboard_refresh(
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
            self._cw_emit_dashboard_refresh(
                company_ids,
                'sale_line_updated',
                self._name,
                self.ids,
            )
        return result

    def unlink(self):
        wash = self._cw_is_wash_line()
        company_ids = wash.mapped('order_id.company_id').ids
        ids = wash.ids
        result = super().unlink()
        if company_ids:
            self._cw_emit_dashboard_refresh(
                company_ids,
                'sale_line_removed',
                self._name,
                ids,
            )
        return result
