# -*- coding: utf-8 -*-
"""Refresh-only realtime notifications for the car-wash dashboard.

The bus payload intentionally contains no customer, vehicle, accounting, stock,
or service details. It is only a signal telling an already-authorized browser to
fetch a fresh dashboard payload through normal Odoo ACLs.
"""

from odoo import api, fields, models


BUS_TYPE = 'car_wash_dashboard_refresh'


def _channel(company_id):
    return f'car_wash_dashboard_company_{int(company_id)}'


def _record_company_ids(records):
    ids = set()
    for record in records:
        if 'company_id' in record._fields and record.company_id:
            ids.add(record.company_id.id)
        elif 'production_id' in record._fields and record.production_id and record.production_id.company_id:
            ids.add(record.production_id.company_id.id)
    return ids


def _record_ids(records):
    return [int(record_id) for record_id in records.ids if record_id]


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def _cw_emit_dashboard_refresh(self, reason='workorder_changed'):
        model_name = self._name
        record_ids = _record_ids(self)
        timestamp = fields.Datetime.to_string(fields.Datetime.now())
        for company_id in _record_company_ids(self):
            # Keep this payload intentionally minimal and non-sensitive.
            self.env['bus.bus']._sendone(
                _channel(company_id),
                BUS_TYPE,
                {
                    'company_id': company_id,
                    'reason': reason,
                    'model': model_name,
                    'record_ids': record_ids,
                    'timestamp': timestamp,
                },
            )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._cw_emit_dashboard_refresh('workorder_created')
        return records

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & {'state', 'workcenter_id', 'date_start', 'date_finished', 'duration'}:
            self._cw_emit_dashboard_refresh('workorder_changed')
        return result

    def unlink(self):
        companies = _record_company_ids(self)
        record_ids = _record_ids(self)
        result = super().unlink()
        timestamp = fields.Datetime.to_string(fields.Datetime.now())
        for company_id in companies:
            self.env['bus.bus']._sendone(
                _channel(company_id),
                BUS_TYPE,
                {
                    'company_id': company_id,
                    'reason': 'workorder_removed',
                    'model': 'mrp.workorder',
                    'record_ids': record_ids,
                    'timestamp': timestamp,
                },
            )
        return result


class MrpProductionRealtime(models.Model):
    _inherit = 'mrp.production'

    def _cw_emit_production_refresh(self, reason='production_changed'):
        timestamp = fields.Datetime.to_string(fields.Datetime.now())
        for company_id in _record_company_ids(self):
            self.env['bus.bus']._sendone(
                _channel(company_id),
                BUS_TYPE,
                {
                    'company_id': company_id,
                    'reason': reason,
                    'model': self._name,
                    'record_ids': _record_ids(self),
                    'timestamp': timestamp,
                },
            )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._cw_emit_production_refresh('production_created')
        return records

    def write(self, vals):
        result = super().write(vals)
        # Some project automations set the textual Sale Order reference only
        # after creating the MO. Re-sync the explicit Small/Large field at
        # that moment without deriving it from legacy vehicle_type.
        if 'x_cc_sale_order_ref' in vals and hasattr(self, '_cw_sync_vehicle_size_from_sale'):
            self._cw_sync_vehicle_size_from_sale()
        watched = {
            'state', 'date_start', 'date_finished', 'car_wash_vehicle_size',
            'x_cc_service_product_id', 'x_cc_sale_order_ref',
            'x_cc_customer_name', 'x_cc_customer_phone',
            'x_cc_vehicle_plate', 'x_cc_vehicle_model', 'x_cc_vehicle_color', 'x_cc_vehicle_notes',
        }
        if set(vals) & watched:
            self._cw_emit_production_refresh('production_changed')
        return result


class MrpWorkcenterRealtime(models.Model):
    _inherit = 'mrp.workcenter'

    def write(self, vals):
        result = super().write(vals)
        if set(vals) & {
            'active', 'name', 'car_wash_enabled', 'car_wash_station_type',
            'car_wash_sequence', 'company_id',
        }:
            timestamp = fields.Datetime.to_string(fields.Datetime.now())
            for company_id in _record_company_ids(self):
                self.env['bus.bus']._sendone(
                    _channel(company_id),
                    BUS_TYPE,
                    {
                        'company_id': company_id,
                        'reason': 'station_configuration_changed',
                        'model': self._name,
                        'record_ids': _record_ids(self),
                        'timestamp': timestamp,
                    },
                )
        return result


class SaleOrderRealtime(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        result = super().write(vals)
        watched = {
            'car_wash_vehicle_size', 'vehicle_type', 'x_cc_customer_phone',
            'x_cc_vehicle_plate', 'x_cc_vehicle_make', 'x_cc_vehicle_model',
            'x_cc_vehicle_year', 'x_cc_vehicle_color', 'x_cc_vehicle_notes',
        }
        if set(vals) & watched:
            timestamp = fields.Datetime.to_string(fields.Datetime.now())
            for company_id in _record_company_ids(self):
                self.env['bus.bus']._sendone(
                    _channel(company_id),
                    BUS_TYPE,
                    {
                        'company_id': company_id,
                        'reason': 'sale_vehicle_changed',
                        'model': self._name,
                        'record_ids': _record_ids(self),
                        'timestamp': timestamp,
                    },
                )
        return result
