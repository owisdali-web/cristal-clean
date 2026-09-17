# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models

from ..dashboard_logic import (
    build_station_slots,
    calculate_progress_percent,
    group_progress_rows,
    infer_station_type,
    normalize_vehicle_size,
)


WASH_TYPES = [
    ('basic', 'Basic'),
    ('premium', 'Premium'),
    ('deluxe', 'Deluxe'),
]

VEHICLE_SIZE_SELECTION = [
    ('small', 'Small'),
    ('large', 'Large'),
]


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Legacy fields are intentionally preserved so upgrades do not destroy old data.
    license_plate = fields.Char('License Plate')
    wash_type = fields.Selection(WASH_TYPES, string='Wash Type', default='basic')
    car_wash_vehicle_size = fields.Selection(
        VEHICLE_SIZE_SELECTION,
        string='Car Wash Vehicle Size',
        help='Explicit Small/Large size copied from the related car-wash sale order when available.',
    )

    def _cw_sync_vehicle_size_from_sale(self):
        """Copy only the explicit Small/Large value from the linked sale order.

        The legacy ``vehicle_type`` field is deliberately not mapped because
        car/truck/van/pickup is a different classification from Small/Large.
        """
        for production in self:
            if production.car_wash_vehicle_size:
                continue
            sale = production._cw_sale_order(production)
            if sale and 'car_wash_vehicle_size' in sale._fields and sale.car_wash_vehicle_size:
                production.car_wash_vehicle_size = sale.car_wash_vehicle_size
        return True

    @api.model_create_multi
    def create(self, vals_list):
        productions = super().create(vals_list)
        productions._cw_sync_vehicle_size_from_sale()
        return productions

    # ------------------------------------------------------------------
    # Date / time helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_day_bounds(self, offset=0):
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        day = (datetime.now(user_tz) + timedelta(days=offset)).date()
        start_local = user_tz.localize(datetime.combine(day, time.min))
        end_local = start_local + timedelta(days=1)

        def to_utc_string(value):
            utc_value = value.astimezone(pytz.utc).replace(tzinfo=None)
            return fields.Datetime.to_string(utc_value)

        return to_utc_string(start_local), to_utc_string(end_local), day

    @api.model
    def _cw_elapsed_minutes(self, value):
        if not value:
            return False
        now = fields.Datetime.now()
        delta = now - value
        return max(0, int(delta.total_seconds() // 60))

    @api.model
    def _cw_progress_percent(self, elapsed_minutes, expected_minutes):
        """Return presentation-only progress from real Odoo timing values."""
        return calculate_progress_percent(elapsed_minutes, expected_minutes)

    # ------------------------------------------------------------------
    # Source adapters
    # ------------------------------------------------------------------
    @api.model
    def _cw_wash_domain(self):
        domain = [('company_id', '=', self.env.company.id)]
        if 'x_cc_is_wash_order' in self._fields:
            domain.append(('x_cc_is_wash_order', '=', True))
        return domain

    @api.model
    def _cw_first_value(self, record, field_names):
        if not record:
            return False
        for field_name in field_names:
            if field_name in record._fields:
                value = getattr(record, field_name, False)
                if value:
                    return value
        return False

    @api.model
    def _cw_sale_order(self, mo):
        SaleOrder = self.env['sale.order']
        if 'sale_line_id' in mo._fields and mo.sale_line_id:
            return mo.sale_line_id.order_id
        if 'x_cc_sale_order_ref' in mo._fields and mo.x_cc_sale_order_ref:
            return SaleOrder.search([
                ('name', '=', mo.x_cc_sale_order_ref),
                ('company_id', '=', mo.company_id.id),
            ], limit=1)
        return SaleOrder

    @api.model
    def _cw_service(self, mo):
        service = self.env['product.product']
        if 'x_cc_service_product_id' in mo._fields and mo.x_cc_service_product_id:
            service = mo.x_cc_service_product_id
        elif 'sale_line_id' in mo._fields and mo.sale_line_id:
            service = mo.sale_line_id.product_id
        return service

    @api.model
    def _cw_vehicle_visual(self, raw_type, size):
        """Return the presentation family used by the dashboard vehicle renderer.

        Small/Large is the canonical visual split for the car-wash UI. Legacy
        body types remain accepted so historical orders keep a sensible fallback.
        """
        raw = str(raw_type or '').lower()
        if size == 'large':
            return 'large'
        if size == 'small':
            return 'small'
        if raw in {'pickup', 'van', 'truck', 'suv'}:
            return 'large'
        return 'small'

    @api.model
    def _cw_vehicle_payload(self, mo, workorder=False, queue_item=False):
        sale = self._cw_sale_order(mo)
        service = self._cw_service(mo)

        plate = self._cw_first_value(mo, ['x_cc_vehicle_plate']) \
            or self._cw_first_value(sale, ['x_cc_vehicle_plate']) \
            or mo.license_plate \
            or ''
        model = self._cw_first_value(mo, ['x_cc_vehicle_model']) \
            or self._cw_first_value(sale, ['x_cc_vehicle_model']) \
            or ''
        color = self._cw_first_value(mo, ['x_cc_vehicle_color']) \
            or self._cw_first_value(sale, ['x_cc_vehicle_color']) \
            or ''
        notes = self._cw_first_value(mo, ['x_cc_vehicle_notes']) \
            or self._cw_first_value(sale, ['x_cc_vehicle_notes']) \
            or ''
        customer = self._cw_first_value(mo, ['x_cc_customer_name']) \
            or (sale.partner_id.display_name if sale and sale.partner_id else '')
        phone = self._cw_first_value(mo, ['x_cc_customer_phone']) \
            or self._cw_first_value(sale, ['x_cc_customer_phone', 'phone']) \
            or (sale.partner_id.phone if sale and sale.partner_id else '')

        service_name = service.display_name if service else 'Service not specified'
        explicit_vehicle_size = self._cw_first_value(
            mo,
            ['car_wash_vehicle_size', 'x_cc_vehicle_size', 'vehicle_size'],
        ) or self._cw_first_value(
            sale,
            ['car_wash_vehicle_size', 'x_cc_vehicle_size', 'vehicle_size'],
        )
        vehicle_size = normalize_vehicle_size(explicit_vehicle_size, service_name)
        legacy_type = self._cw_first_value(sale, ['vehicle_type'])

        elapsed_minutes = False
        expected_minutes = False
        progress_percent = False
        if workorder:
            started_at = self._cw_first_value(workorder, ['date_start', 'date_start_work'])
            elapsed_minutes = self._cw_elapsed_minutes(started_at)
            expected_minutes = self._cw_first_value(workorder, ['duration_expected']) or False
            progress_percent = self._cw_progress_percent(elapsed_minutes, expected_minutes)

        waiting_minutes = False
        if queue_item:
            waiting_from = mo.create_date or self._cw_first_value(mo, ['date_start'])
            waiting_minutes = self._cw_elapsed_minutes(waiting_from)

        return {
            'id': mo.id,
            'name': mo.name or '',
            'production_id': mo.id,
            'workorder_id': workorder.id if workorder else False,
            'workcenter_id': workorder.workcenter_id.id if workorder and workorder.workcenter_id else False,
            'plate': plate or 'No plate',
            'vehicle_model': model or '',
            'vehicle_color': color or '',
            'vehicle_notes': notes or '',
            'vehicle_size': vehicle_size,
            'vehicle_visual': self._cw_vehicle_visual(legacy_type, vehicle_size),
            'service_id': service.id if service else False,
            'service_name': service_name,
            'customer_name': customer or '',
            'customer_phone': phone or '',
            'elapsed_minutes': elapsed_minutes,
            'expected_minutes': expected_minutes,
            'progress_percent': progress_percent,
            'waiting_minutes': waiting_minutes,
            'stage_name': workorder.name if workorder else '',
        }

    # ------------------------------------------------------------------
    # Work-center discovery
    # ------------------------------------------------------------------
    @api.model
    def _cw_station_records(self):
        Workcenter = self.env['mrp.workcenter']
        company = self.env.company
        company_domain = [('active', '=', True)]
        if 'company_id' in Workcenter._fields:
            company_domain += ['|', ('company_id', '=', False), ('company_id', '=', company.id)]

        configured = Workcenter.search(
            company_domain + [('car_wash_enabled', '=', True)],
            order='car_wash_sequence, sequence, id',
        )
        if configured:
            return configured[:10], 'configured'

        fallback = Workcenter.search(company_domain, order='sequence, id', limit=10)
        return fallback, 'fallback'

    @api.model
    def _cw_station_base_payload(self, workcenter, mode):
        configured_type = workcenter.car_wash_station_type if mode == 'configured' else ''
        return {
            'id': workcenter.id,
            'name': workcenter.name or 'Car Wash Station',
            'station_type': infer_station_type(workcenter.name, configured_type),
            'status': 'available',
            'visual_status': 'available',
            'current_car': False,
            'elapsed_minutes': False,
            'expected_minutes': False,
            'progress_percent': False,
            'conflict_count': 0,
            'is_placeholder': False,
        }

    # ------------------------------------------------------------------
    # Dashboard payload
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        company = self.env.company
        base_domain = self._cw_wash_domain()
        today_start, today_end, _today = self._cw_day_bounds(0)

        active_mos = self.search(
            base_domain + [('state', 'in', ['confirmed', 'progress'])],
            order='create_date asc, id asc',
        )

        Workorder = self.env['mrp.workorder']
        progress_domain = [
            ('production_id.company_id', '=', company.id),
            ('production_id.state', 'not in', ['done', 'cancel']),
            ('state', '=', 'progress'),
        ]
        if 'x_cc_is_wash_order' in self._fields:
            progress_domain.append(('production_id.x_cc_is_wash_order', '=', True))
        progress_wos = Workorder.search(progress_domain, order='date_start asc, id asc')

        progress_rows = [
            {
                'station_id': wo.workcenter_id.id if wo.workcenter_id else False,
                'production_id': wo.production_id.id,
            }
            for wo in progress_wos
            if wo.workcenter_id and wo.production_id
        ]
        progress_grouped = group_progress_rows(progress_rows)
        in_station_mo_ids = set(wo.production_id.id for wo in progress_wos if wo.production_id)

        queue_mos = active_mos.filtered(lambda mo: mo.id not in in_station_mo_ids)
        queue = [self._cw_vehicle_payload(mo, queue_item=True) for mo in queue_mos]
        queue_domain = [('id', 'in', queue_mos.ids)]

        station_records, configuration_mode = self._cw_station_records()
        real_station_payloads = []

        workorders_by_station = {}
        for wo in progress_wos:
            if not wo.workcenter_id:
                continue
            workorders_by_station.setdefault(wo.workcenter_id.id, []).append(wo)

        for station in station_records:
            item = self._cw_station_base_payload(station, configuration_mode)
            grouped = progress_grouped.get(station.id, {'production_ids': [], 'conflict_count': 0})
            production_ids = grouped['production_ids']
            item['conflict_count'] = grouped['conflict_count']

            if len(production_ids) > 1:
                item['status'] = 'conflict'
                item['visual_status'] = 'conflict'
            elif len(production_ids) == 1:
                item['status'] = 'busy'
                production = self.browse(production_ids[0])
                station_wos = workorders_by_station.get(station.id, [])
                current_wo = next((wo for wo in station_wos if wo.production_id.id == production.id), False)
                item['current_car'] = self._cw_vehicle_payload(production, current_wo)
                item['elapsed_minutes'] = item['current_car']['elapsed_minutes']
                item['expected_minutes'] = item['current_car']['expected_minutes']
                item['progress_percent'] = item['current_car']['progress_percent']
                item['visual_status'] = (
                    'finishing'
                    if item['progress_percent'] is not False and item['progress_percent'] >= 85
                    else 'busy'
                )

            real_station_payloads.append(item)

        stations = build_station_slots(real_station_payloads, target=10)

        finished_today_domain = base_domain + [
            ('state', '=', 'done'),
            ('date_finished', '>=', today_start),
            ('date_finished', '<', today_end),
        ]
        finished_today = self.search_count(finished_today_domain)
        finished_today_mos = self.search(
            finished_today_domain,
            order='date_finished desc, id desc',
        )
        finished_today_items = []
        for finished_mo in finished_today_mos:
            finished_item = self._cw_vehicle_payload(finished_mo)
            finished_item['finished_at'] = (
                fields.Datetime.to_string(finished_mo.date_finished)
                if finished_mo.date_finished
                else ''
            )
            finished_today_items.append(finished_item)

        distinct_active_ids = sorted(in_station_mo_ids)
        available_stations = sum(1 for station in real_station_payloads if station['status'] == 'available')

        automatic_count = sum(1 for station in real_station_payloads if station['station_type'] == 'automatic')
        polishing_count = sum(1 for station in real_station_payloads if station['station_type'] == 'polishing')
        general_count = sum(1 for station in real_station_payloads if station['station_type'] == 'general')

        warnings = []
        if configuration_mode == 'fallback':
            warnings.append('Station types are using backward-compatible name detection. Configure dashboard station types.')
        if len(real_station_payloads) != 10:
            warnings.append('The dashboard expects 10 real car-wash stations.')
        if automatic_count != 1:
            warnings.append('Configure exactly one Automatic station.')
        if polishing_count != 1:
            warnings.append('Configure exactly one Polishing station.')
        if general_count != 8:
            warnings.append('Configure eight General stations.')

        user_name = self.env.user.display_name or self.env.user.name or 'Odoo User'
        user_initials = ''.join(
            part[:1].upper() for part in user_name.split() if part
        )[:2] or 'OD'
        user_role = 'Manager' if self.env.user.has_group('mrp.group_mrp_manager') else 'Operator'

        return {
            'dashboard_version': '6.5-business-analytics',
            'company_id': company.id,
            'company_name': company.display_name,
            'user_name': user_name,
            'user_initials': user_initials,
            'user_role': user_role,
            'kpis': {
                'active_cars': len(distinct_active_ids),
                'waiting_queue': len(queue),
                'available_stations': available_stations,
                'finished_today': finished_today,
            },
            'queue': queue,
            'stations': stations,
            'finished_today_items': finished_today_items,
            'queue_domain': queue_domain,
            'finished_today_domain': finished_today_domain,
            'wash_order_domain': base_domain,
            'station_configuration': {
                'mode': configuration_mode,
                'real_station_count': len(real_station_payloads),
                'target_station_count': 10,
                'automatic_count': automatic_count,
                'polishing_count': polishing_count,
                'general_count': general_count,
                'warnings': warnings,
            },
            'shop_floor_action': 'mrp_workorder.action_mrp_display',
            # Compatibility aliases for cached older browser assets during rollout.
            'active_total': len(distinct_active_ids),
            'waiting': len(queue),
            'station_free': available_stations,
            'done_today': finished_today,
            'active_cars': [self._cw_vehicle_payload(mo) for mo in self.browse(distinct_active_ids)],
            'workcenter_load': real_station_payloads,
        }
