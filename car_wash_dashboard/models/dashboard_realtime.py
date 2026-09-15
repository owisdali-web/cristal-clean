# -*- coding: utf-8 -*-
"""Realtime refresh signals for Crystal Clean Dashboard V8.

These hooks never advance a wash stage and never modify commercial, stock or accounting
records. They only send a small company-scoped bus signal after normal Odoo writes.
"""
from odoo import api, fields, models

NOTIFICATION_TYPE = 'crystal_clean_dashboard_refresh'


def _send_refresh(env, company_ids, reason, model_name, record_ids):
    if 'bus.bus' not in env.registry.models:
        return
    company_ids = sorted({int(cid) for cid in company_ids if cid})
    if not company_ids:
        company_ids = [env.company.id]
    record_ids = sorted({int(rid) for rid in record_ids if rid})[:30]
    bus = env['bus.bus']
    dashboard = env['mrp.production']
    for company_id in company_ids:
        bus._sendone(
            dashboard._cw_dashboard_channel(company_id),
            NOTIFICATION_TYPE,
            {
                'company_id': company_id,
                'reason': reason,
                'model': model_name,
                'record_ids': record_ids,
                'timestamp': fields.Datetime.to_string(fields.Datetime.now()),
            },
        )


def _wash_mos(records):
    if not records:
        return records
    tmpl = records.env['product.template']
    if 'to_make_mrp' in tmpl._fields:
        return records.filtered(lambda r: bool(r.product_id.product_tmpl_id.to_make_mrp))
    if 'x_cc_is_wash_order' in records._fields:
        return records.filtered(lambda r: bool(r.x_cc_is_wash_order))
    return records.filtered(lambda r: (r.origin or '').startswith('POS-'))


class MrpProductionRealtime(models.Model):
    _inherit = 'mrp.production'

    _CW_WATCH = {
        'state', 'date_start', 'date_finished', 'date_deadline', 'reservation_state',
        'workorder_ids', 'product_id', 'origin', 'x_cc_vehicle_plate',
        'x_cc_vehicle_model', 'x_cc_vehicle_color', 'x_cc_vehicle_notes',
    }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        wash = _wash_mos(records)
        if wash:
            _send_refresh(self.env, wash.mapped('company_id').ids, 'wash_order_created', self._name, wash.ids)
        return records

    def write(self, vals):
        company_ids = _wash_mos(self).mapped('company_id').ids
        result = super().write(vals)
        wash = _wash_mos(self)
        company_ids += wash.mapped('company_id').ids
        if company_ids and (set(vals) & self._CW_WATCH):
            _send_refresh(self.env, company_ids, 'wash_order_updated', self._name, self.ids)
        return result


class MrpWorkorderRealtime(models.Model):
    _inherit = 'mrp.workorder'

    _CW_WATCH = {'state', 'workcenter_id', 'date_start', 'date_finished', 'duration', 'duration_expected'}

    def _cw_realtime_wash(self):
        return self.filtered(lambda w: bool(_wash_mos(w.production_id)))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        wash = records._cw_realtime_wash()
        if wash:
            _send_refresh(self.env, wash.mapped('production_id.company_id').ids, 'stage_created', self._name, wash.ids)
        return records

    def write(self, vals):
        before = self._cw_realtime_wash()
        company_ids = before.mapped('production_id.company_id').ids
        result = super().write(vals)
        after = self._cw_realtime_wash()
        company_ids += after.mapped('production_id.company_id').ids
        if company_ids and (set(vals) & self._CW_WATCH):
            reason = 'stage_changed' if 'state' in vals else 'stage_updated'
            _send_refresh(self.env, company_ids, reason, self._name, self.ids)
        return result


class PosOrderRealtime(models.Model):
    _inherit = 'pos.order'

    _CW_WATCH = {'state', 'partner_id', 'amount_total', 'lines'}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if records:
            _send_refresh(self.env, records.mapped('company_id').ids, 'pos_order_created', self._name, records.ids)
        return records

    def write(self, vals):
        company_ids = self.mapped('company_id').ids
        result = super().write(vals)
        if company_ids and (set(vals) & self._CW_WATCH):
            _send_refresh(self.env, company_ids, 'pos_order_updated', self._name, self.ids)
        return result


class AccountMoveRealtime(models.Model):
    _inherit = 'account.move'

    _CW_WATCH = {'state', 'payment_state', 'amount_total', 'amount_residual', 'invoice_date'}

    def write(self, vals):
        company_ids = self.mapped('company_id').ids
        result = super().write(vals)
        if company_ids and (set(vals) & self._CW_WATCH):
            _send_refresh(self.env, company_ids, 'accounting_updated', self._name, self.ids)
        return result
