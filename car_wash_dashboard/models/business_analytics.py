# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models


PAID_POS_STATES = ('paid', 'done', 'invoiced')


class MrpProductionBusinessAnalytics(models.Model):
    _inherit = 'mrp.production'

    # ------------------------------------------------------------------
    # Period helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_analytics_timezone(self):
        try:
            return pytz.timezone(self.env.user.tz or 'UTC')
        except pytz.UnknownTimeZoneError:
            return pytz.UTC

    @api.model
    def _cw_analytics_to_utc_string(self, local_value):
        return fields.Datetime.to_string(
            local_value.astimezone(pytz.UTC).replace(tzinfo=None)
        )

    @api.model
    def _cw_analytics_day_bounds(self, offset=0):
        user_tz = self._cw_analytics_timezone()
        local_now = datetime.now(user_tz)
        day = local_now.date() + timedelta(days=offset)
        start_local = user_tz.localize(datetime.combine(day, time.min))
        end_local = start_local + timedelta(days=1)
        return {
            'start': self._cw_analytics_to_utc_string(start_local),
            'end': self._cw_analytics_to_utc_string(end_local),
            'start_local': start_local,
            'end_local': end_local,
            'label': day.isoformat(),
        }

    @api.model
    def _cw_analytics_month_bounds(self, month_offset=0):
        user_tz = self._cw_analytics_timezone()
        local_now = datetime.now(user_tz)
        month_index = (local_now.year * 12 + (local_now.month - 1)) + month_offset
        year = month_index // 12
        month = month_index % 12 + 1
        next_index = month_index + 1
        next_year = next_index // 12
        next_month = next_index % 12 + 1
        start_local = user_tz.localize(datetime(year, month, 1))
        end_local = user_tz.localize(datetime(next_year, next_month, 1))
        return {
            'start': self._cw_analytics_to_utc_string(start_local),
            'end': self._cw_analytics_to_utc_string(end_local),
            'start_local': start_local,
            'end_local': end_local,
            'label': f"{_(start_local.strftime('%B'))} {year}",
        }

    @api.model
    def _cw_analytics_period_bounds(self, period='today'):
        if period == 'month':
            return self._cw_analytics_month_bounds(0)
        return self._cw_analytics_day_bounds(0)

    @api.model
    def _cw_analytics_growth(self, current, previous):
        current = float(current or 0.0)
        previous = float(previous or 0.0)
        if not previous:
            return False
        return round(((current - previous) / previous) * 100.0, 1)

    @api.model
    def _cw_analytics_local_datetime(self, value):
        if not value:
            return False
        user_tz = self._cw_analytics_timezone()
        if value.tzinfo:
            utc_value = value.astimezone(pytz.UTC)
        else:
            utc_value = pytz.UTC.localize(value)
        return utc_value.astimezone(user_tz)

    # ------------------------------------------------------------------
    # Source helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_analytics_wash_product_ids(self):
        """Return POS/service products whose BoM operations belong to car-wash stations."""
        Workcenter = self.env['mrp.workcenter'].sudo()
        Operation = self.env['mrp.routing.workcenter'].sudo()
        ProductTemplate = self.env['product.template'].sudo()

        workcenters = Workcenter.search([
            ('car_wash_enabled', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
        ])
        operations = Operation.with_context(active_test=False).search([
            ('workcenter_id', 'in', workcenters.ids),
        ])
        boms = operations.mapped('bom_id').exists()
        template_ids = set(boms.mapped('product_tmpl_id').ids)

        if 'x_cc_operation_bom_id' in ProductTemplate._fields and boms:
            mapped_templates = ProductTemplate.with_context(active_test=False).search([
                ('x_cc_operation_bom_id', 'in', boms.ids),
            ])
            template_ids.update(mapped_templates.ids)

        templates = ProductTemplate.with_context(active_test=False).browse(list(template_ids)).exists()
        return templates.mapped('product_variant_ids').ids

    @api.model
    def _cw_analytics_line_amount(self, line):
        amount_field = 'price_subtotal_incl' if 'price_subtotal_incl' in line._fields else 'price_subtotal'
        return float(getattr(line, amount_field, 0.0) or 0.0)

    @api.model
    def _cw_analytics_pos_orders(self, bounds):
        PosLine = self.env['pos.order.line'].sudo()
        wash_product_ids = self._cw_analytics_wash_product_ids()
        if not wash_product_ids:
            return self.env['pos.order'].sudo()
        lines = PosLine.search([
            ('product_id', 'in', wash_product_ids),
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.state', 'in', list(PAID_POS_STATES)),
            ('order_id.date_order', '>=', bounds['start']),
            ('order_id.date_order', '<', bounds['end']),
        ], order='order_id, id')
        return lines.mapped('order_id').sorted(key=lambda order: (order.date_order or fields.Datetime.now(), order.id))

    @api.model
    def _cw_analytics_wash_mos(self, bounds, states=None):
        domain = self._cw_wash_domain()
        if states:
            domain.append(('state', 'in', states))
        if 'date_finished' in self._fields and states and 'done' in states:
            domain += [
                ('date_finished', '>=', bounds['start']),
                ('date_finished', '<', bounds['end']),
            ]
        else:
            domain += [
                ('create_date', '>=', bounds['start']),
                ('create_date', '<', bounds['end']),
            ]
        return self.search(domain, order='create_date asc, id asc')

    @api.model
    def _cw_analytics_pos_lines(self, orders):
        if not orders:
            return self.env['pos.order.line'].sudo()
        wash_product_ids = self._cw_analytics_wash_product_ids()
        if not wash_product_ids:
            return self.env['pos.order.line'].sudo()
        return self.env['pos.order.line'].sudo().search([
            ('order_id', 'in', orders.ids),
            ('product_id', 'in', wash_product_ids),
        ], order='id asc')

    @api.model
    def _cw_analytics_station_utilization(self, bounds):
        Workcenter = self.env['mrp.workcenter'].sudo()
        Workorder = self.env['mrp.workorder'].sudo()
        stations = Workcenter.search([
            ('active', '=', True),
            ('car_wash_enabled', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
        ], order='car_wash_sequence, sequence, id')

        now_utc = fields.Datetime.now()
        start_utc = fields.Datetime.from_string(bounds['start'])
        end_utc = min(fields.Datetime.from_string(bounds['end']), now_utc)
        span_minutes = max(1.0, (end_utc - start_utc).total_seconds() / 60.0)

        rows = []
        total_busy = 0.0
        total_capacity = 0.0
        for station in stations:
            workorders = Workorder.search([
                ('workcenter_id', '=', station.id),
                ('production_id.company_id', '=', self.env.company.id),
                ('production_id.x_cc_is_wash_order', '=', True),
                ('date_start', '<', bounds['end']),
                '|', ('date_finished', '=', False), ('date_finished', '>=', bounds['start']),
            ])

            busy_minutes = 0.0
            for workorder in workorders:
                started = workorder.date_start or start_utc
                finished = workorder.date_finished or now_utc
                clipped_start = max(started, start_utc)
                clipped_end = min(finished, end_utc)
                if clipped_end > clipped_start:
                    busy_minutes += (clipped_end - clipped_start).total_seconds() / 60.0

            capacity_minutes = span_minutes
            calendar = getattr(station, 'resource_calendar_id', False)
            if calendar and hasattr(calendar, 'get_work_hours_count'):
                try:
                    aware_start = pytz.UTC.localize(start_utc)
                    aware_end = pytz.UTC.localize(end_utc)
                    work_hours = calendar.get_work_hours_count(
                        aware_start,
                        aware_end,
                        compute_leaves=False,
                    )
                    if work_hours:
                        capacity_minutes = max(1.0, float(work_hours) * 60.0)
                except Exception:
                    capacity_minutes = span_minutes

            utilization = min(100.0, (busy_minutes / capacity_minutes) * 100.0)
            rows.append({
                'id': station.id,
                'name': station.name,
                'sequence': station.car_wash_sequence,
                'station_type': station.car_wash_station_type,
                'utilization': round(utilization, 1),
                'busy_minutes': round(busy_minutes, 1),
                'capacity_minutes': round(capacity_minutes, 1),
            })
            total_busy += busy_minutes
            total_capacity += capacity_minutes

        overall = min(100.0, (total_busy / total_capacity) * 100.0) if total_capacity else 0.0
        return {
            'overall': round(overall, 1),
            'stations': rows,
        }

    @api.model
    def _cw_analytics_low_supplies(self):
        Workcenter = self.env['mrp.workcenter'].sudo()
        Operation = self.env['mrp.routing.workcenter'].sudo()
        Orderpoint = self.env['stock.warehouse.orderpoint'].sudo()

        workcenters = Workcenter.search([
            ('car_wash_enabled', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
        ])
        operations = Operation.with_context(active_test=False).search([
            ('workcenter_id', 'in', workcenters.ids),
        ])
        boms = operations.mapped('bom_id')
        products = boms.mapped('bom_line_ids.product_id').exists()
        if not products:
            return []

        orderpoint_domain = [('product_id', 'in', products.ids)]
        if 'company_id' in Orderpoint._fields:
            orderpoint_domain += ['|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
        orderpoints = Orderpoint.search(orderpoint_domain)

        threshold_by_product = defaultdict(float)
        for orderpoint in orderpoints:
            threshold_by_product[orderpoint.product_id.id] = max(
                threshold_by_product[orderpoint.product_id.id],
                float(orderpoint.product_min_qty or 0.0),
            )

        rows = []
        for product in products:
            threshold = threshold_by_product.get(product.id, 0.0)
            if threshold <= 0:
                continue
            company_product = product.with_company(self.env.company)
            if 'free_qty' in product._fields:
                available = float(company_product.free_qty or 0.0)
            else:
                available = float(company_product.qty_available or 0.0)
            if available > threshold:
                continue
            ratio = min(100.0, max(0.0, (available / threshold) * 100.0))
            rows.append({
                'product_id': product.id,
                'name': product.display_name,
                'available_qty': round(available, 2),
                'minimum_qty': round(threshold, 2),
                'uom': product.uom_id.display_name if product.uom_id else '',
                'remaining_percent': round(ratio, 1),
            })

        rows.sort(key=lambda item: (item['remaining_percent'], item['available_qty'], item['name']))
        return rows[:5]

    # ------------------------------------------------------------------
    # Interactive analytics drill-down helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_analytics_money_text(self, value):
        currency = self.env.company.currency_id
        return f"{float(value or 0.0):,.2f} {currency.name}"

    @api.model
    def _cw_analytics_order_row(self, order):
        lines = self._cw_analytics_pos_lines(order)
        amount = sum(self._cw_analytics_line_amount(line) for line in lines)
        services = ', '.join(dict.fromkeys(lines.mapped('product_id').mapped('display_name')))
        partner = order.partner_id
        local_dt = self._cw_analytics_local_datetime(order.date_order)
        return {
            'id': f'pos-{order.id}',
            'primary': order.name,
            'secondary': partner.display_name if partner else _('Walk-in customer'),
            'detail': services or _('Car wash service'),
            'timestamp': local_dt.strftime('%Y-%m-%d %H:%M') if local_dt else '',
            'amount': round(amount, 2),
            'metric': self._cw_analytics_money_text(amount),
            'model': 'pos.order',
            'res_id': order.id,
            'icon': 'fa-credit-card',
        }

    @api.model
    def _cw_analytics_partner_orders(self, orders, partner_id):
        return orders.filtered(lambda order: order.partner_id.id == partner_id)

    @api.model
    def _cw_analytics_detail_payload(self, detail_type, title, subtitle='', rows=None, summary=None):
        translated_rows = []
        for row in rows or []:
            item = dict(row)
            for field_name in ('secondary', 'detail', 'metric'):
                if isinstance(item.get(field_name), str):
                    item[field_name] = _(item[field_name])
            translated_rows.append(item)

        translated_summary = []
        for item in summary or []:
            translated = dict(item)
            if isinstance(translated.get('label'), str):
                translated['label'] = _(translated['label'])
            translated_summary.append(translated)

        return {
            'detail_type': detail_type,
            'title': _(title) if title else '',
            'subtitle': _(subtitle) if subtitle else '',
            'summary': translated_summary,
            'rows': translated_rows,
        }

    @api.model
    def get_business_analytics_detail(self, detail_type, key=False, period='today'):
        """Return read-only drill-down rows for one analytics surface."""
        period = 'month' if period == 'month' else 'today'
        selected_bounds = self._cw_analytics_period_bounds(period)
        today_bounds = self._cw_analytics_day_bounds(0)
        month_bounds = self._cw_analytics_month_bounds(0)
        selected_orders = self._cw_analytics_pos_orders(selected_bounds)
        today_orders = self._cw_analytics_pos_orders(today_bounds)
        month_orders = self._cw_analytics_pos_orders(month_bounds)

        if detail_type in ('today_revenue', 'washes_today', 'average_ticket'):
            orders = today_orders
            rows = [self._cw_analytics_order_row(order) for order in orders]
            revenue = sum(row['amount'] for row in rows)
            titles = {
                'today_revenue': _('Today\'s Revenue'),
                'washes_today': _('Total Washes Today'),
                'average_ticket': _('Average Ticket'),
            }
            summary = [
                {'label': _('Wash visits'), 'value': str(len(rows))},
                {'label': _('Revenue'), 'value': self._cw_analytics_money_text(revenue)},
            ]
            if detail_type == 'average_ticket':
                average = revenue / len(rows) if rows else 0.0
                summary.append({'label': _('Average'), 'value': self._cw_analytics_money_text(average)})
            return self._cw_analytics_detail_payload(
                detail_type, titles[detail_type], _('Paid car-wash POS visits today.'), rows, summary,
            )

        if detail_type == 'monthly_revenue':
            rows = [self._cw_analytics_order_row(order) for order in month_orders]
            revenue = sum(row['amount'] for row in rows)
            return self._cw_analytics_detail_payload(
                detail_type,
                _('Monthly Revenue'),
                month_bounds['label'],
                rows,
                [
                    {'label': _('Wash visits'), 'value': str(len(rows))},
                    {'label': _('Revenue'), 'value': self._cw_analytics_money_text(revenue)},
                ],
            )

        if detail_type == 'active_customers':
            customers = today_orders.mapped('partner_id').exists()
            rows = []
            for partner in customers:
                partner_orders = self._cw_analytics_partner_orders(today_orders, partner.id)
                revenue = sum(self._cw_analytics_order_row(order)['amount'] for order in partner_orders)
                rows.append({
                    'id': f'partner-{partner.id}',
                    'primary': partner.display_name,
                    'secondary': partner.phone or partner.mobile or '',
                    'detail': _('%(count)s wash visit(s) today', count=len(partner_orders)),
                    'metric': self._cw_analytics_money_text(revenue),
                    'amount': round(revenue, 2),
                    'model': 'res.partner',
                    'res_id': partner.id,
                    'icon': 'fa-user',
                })
            rows.sort(key=lambda row: (-row['amount'], row['primary']))
            return self._cw_analytics_detail_payload(
                detail_type,
                _('Active Customers'),
                _('Customers with paid car-wash visits today.'),
                rows,
                [{'label': _('Customers'), 'value': str(len(rows))}],
            )

        if detail_type == 'daily_washes':
            try:
                bucket_index = max(0, min(7, int(key)))
            except (TypeError, ValueError):
                bucket_index = 0
            orders = today_orders.filtered(
                lambda order: self._cw_analytics_local_datetime(order.date_order)
                and min(7, self._cw_analytics_local_datetime(order.date_order).hour // 3) == bucket_index
            )
            rows = [self._cw_analytics_order_row(order) for order in orders]
            start_hour = bucket_index * 3
            return self._cw_analytics_detail_payload(
                detail_type,
                f"{_('Daily Washes')} · {start_hour:02d}:00–{(start_hour + 3) % 24:02d}:00",
                _('Paid car-wash visits in this time bucket.'),
                rows,
                [{'label': _('Washes'), 'value': str(len(rows))}],
            )

        if detail_type == 'popular_service':
            try:
                product_id = int(key)
            except (TypeError, ValueError):
                product_id = 0
            lines = self._cw_analytics_pos_lines(selected_orders).filtered(
                lambda line: line.product_id.id == product_id
            )
            orders = lines.mapped('order_id')
            rows = [self._cw_analytics_order_row(order) for order in orders]
            product = self.env['product.product'].sudo().browse(product_id).exists()
            quantity = sum(float(getattr(line, 'qty', 0.0) or 0.0) for line in lines)
            revenue = sum(self._cw_analytics_line_amount(line) for line in lines)
            return self._cw_analytics_detail_payload(
                detail_type,
                product.display_name if product else _('Service'),
                _('Service usage in the selected analytics period.'),
                rows,
                [
                    {'label': _('Quantity'), 'value': f'{quantity:g}'},
                    {'label': _('Revenue'), 'value': self._cw_analytics_money_text(revenue)},
                ],
            )

        if detail_type == 'station_overall':
            station_data = self._cw_analytics_station_utilization(selected_bounds)
            rows = []
            for station_row in station_data['stations']:
                rows.append({
                    'id': f"station-{station_row['id']}",
                    'primary': station_row['name'],
                    'secondary': _(station_row['station_type'].title()),
                    'detail': _('%(busy)s busy min / %(capacity)s capacity min', busy=round(station_row['busy_minutes']), capacity=round(station_row['capacity_minutes'])),
                    'metric': f"{station_row['utilization']}%",
                    'model': 'mrp.workcenter',
                    'res_id': station_row['id'],
                    'icon': 'fa-building-o',
                })
            rows.sort(key=lambda row: row['primary'])
            return self._cw_analytics_detail_payload(
                detail_type,
                _('Station Utilization'),
                _('Utilization for all configured car-wash stations.'),
                rows,
                [{'label': _('Overall utilization'), 'value': f"{station_data['overall']}%"}],
            )

        if detail_type == 'station':
            try:
                station_id = int(key)
            except (TypeError, ValueError):
                station_id = 0
            station = self.env['mrp.workcenter'].sudo().browse(station_id).exists()
            if not station:
                return self._cw_analytics_detail_payload(detail_type, _('Station'), _('Station not found.'))
            workorders = self.env['mrp.workorder'].sudo().search([
                ('workcenter_id', '=', station.id),
                ('production_id.company_id', '=', self.env.company.id),
                ('production_id.x_cc_is_wash_order', '=', True),
                ('date_start', '<', selected_bounds['end']),
                '|', ('date_finished', '=', False), ('date_finished', '>=', selected_bounds['start']),
            ], order='date_start desc, id desc')
            rows = []
            for workorder in workorders:
                mo = workorder.production_id
                started = self._cw_analytics_local_datetime(workorder.date_start)
                elapsed = float(getattr(workorder, 'duration', 0.0) or 0.0)
                if not elapsed and workorder.date_start:
                    finished = workorder.date_finished or fields.Datetime.now()
                    elapsed = max(0.0, (finished - workorder.date_start).total_seconds() / 60.0)
                rows.append({
                    'id': f'wo-{workorder.id}',
                    'primary': self._cw_first_value(mo, ['x_cc_vehicle_plate']) or mo.name,
                    'secondary': self._cw_first_value(mo, ['x_cc_customer_name']) or '',
                    'detail': self._cw_first_value(mo, ['x_cc_service_product_id']).display_name if self._cw_first_value(mo, ['x_cc_service_product_id']) else workorder.name,
                    'timestamp': started.strftime('%Y-%m-%d %H:%M') if started else '',
                    'metric': f"{round(elapsed)} {_('min')}",
                    'model': 'mrp.workorder',
                    'res_id': workorder.id,
                    'icon': 'fa-car',
                })
            station_data = self._cw_analytics_station_utilization(selected_bounds)
            util_row = next((row for row in station_data['stations'] if row['id'] == station.id), {})
            return self._cw_analytics_detail_payload(
                detail_type,
                station.name,
                _('%(type)s station activity.', type=_(station.car_wash_station_type.title())),
                rows,
                [
                    {'label': _('Utilization'), 'value': f"{util_row.get('utilization', 0)}%"},
                    {'label': _('Busy time'), 'value': f"{round(util_row.get('busy_minutes', 0))} {_('min')}"},
                    {'label': _('Wash operations'), 'value': str(len(rows))},
                ],
            )

        if detail_type == 'top_customer':
            try:
                partner_id = int(key)
            except (TypeError, ValueError):
                partner_id = 0
            partner = self.env['res.partner'].sudo().browse(partner_id).exists()
            orders = self._cw_analytics_partner_orders(selected_orders, partner_id)
            rows = [self._cw_analytics_order_row(order) for order in orders]
            revenue = sum(row['amount'] for row in rows)
            return self._cw_analytics_detail_payload(
                detail_type,
                partner.display_name if partner else _('Customer'),
                _('Car-wash history in the selected analytics period.'),
                rows,
                [
                    {'label': _('Washes'), 'value': str(len(rows))},
                    {'label': _('Revenue'), 'value': self._cw_analytics_money_text(revenue)},
                ],
            )

        if detail_type == 'supply':
            try:
                product_id = int(key)
            except (TypeError, ValueError):
                product_id = 0
            product = self.env['product.product'].sudo().browse(product_id).exists()
            if not product:
                return self._cw_analytics_detail_payload(detail_type, _('Supply'), _('Supply not found.'))
            orderpoints = self.env['stock.warehouse.orderpoint'].sudo().search([
                ('product_id', '=', product.id),
                '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
            ])
            minimum = max(orderpoints.mapped('product_min_qty') or [0.0])
            company_product = product.with_company(self.env.company)
            available = float(company_product.free_qty if 'free_qty' in product._fields else company_product.qty_available or 0.0)
            boms = self.env['mrp.bom'].sudo().with_context(active_test=False).search([
                ('bom_line_ids.product_id', '=', product.id),
            ])
            rows = [{
                'id': f'product-{product.id}',
                'primary': product.display_name,
                'secondary': product.uom_id.display_name if product.uom_id else '',
                'detail': ', '.join(boms.mapped('display_name')[:5]) or _('No linked car-wash BoM'),
                'metric': f"{available:g} {_('available')}",
                'model': 'product.product',
                'res_id': product.id,
                'icon': 'fa-flask',
            }]
            return self._cw_analytics_detail_payload(
                detail_type,
                product.display_name,
                _('Current supply level and linked car-wash recipes.'),
                rows,
                [
                    {'label': _('Available'), 'value': f'{available:g} {product.uom_id.display_name if product.uom_id else ""}'.strip()},
                    {'label': _('Reorder minimum'), 'value': f'{minimum:g}'},
                ],
            )

        if detail_type == 'revenue_week':
            try:
                week_index = max(0, min(4, int(key)))
            except (TypeError, ValueError):
                week_index = 0
            orders = month_orders.filtered(
                lambda order: self._cw_analytics_local_datetime(order.date_order)
                and min(4, (self._cw_analytics_local_datetime(order.date_order).day - 1) // 7) == week_index
            )
            rows = [self._cw_analytics_order_row(order) for order in orders]
            revenue = sum(row['amount'] for row in rows)
            return self._cw_analytics_detail_payload(
                detail_type,
                f"{_('Revenue Trend')} · {_('Week')} {week_index + 1}",
                month_bounds['label'],
                rows,
                [
                    {'label': _('Wash visits'), 'value': str(len(rows))},
                    {'label': _('Revenue'), 'value': self._cw_analytics_money_text(revenue)},
                ],
            )

        if detail_type == 'customer_mix_overall':
            partner_ids = set(selected_orders.mapped('partner_id').ids)
            older_orders = self.env['pos.order'].sudo().search([
                ('company_id', '=', self.env.company.id),
                ('state', 'in', list(PAID_POS_STATES)),
                ('partner_id', 'in', list(partner_ids) or [0]),
                ('date_order', '<', selected_bounds['start']),
            ])
            returning_ids = set(older_orders.mapped('partner_id').ids)
            partners = self.env['res.partner'].sudo().browse(list(partner_ids)).exists()
            rows = []
            for partner in partners:
                orders = self._cw_analytics_partner_orders(selected_orders, partner.id)
                segment = _('Returning') if partner.id in returning_ids else _('New')
                rows.append({
                    'id': f'partner-{partner.id}',
                    'primary': partner.display_name,
                    'secondary': segment,
                    'detail': _('%(count)s wash visit(s)', count=len(orders)),
                    'metric': self._cw_analytics_money_text(sum(self._cw_analytics_order_row(order)['amount'] for order in orders)),
                    'model': 'res.partner',
                    'res_id': partner.id,
                    'icon': 'fa-user',
                })
            rows.sort(key=lambda row: (row['secondary'], row['primary']))
            return self._cw_analytics_detail_payload(
                detail_type,
                _('New vs Returning Customers'),
                _('Customer classification for the selected analytics period.'),
                rows,
                [
                    {'label': _('Returning'), 'value': str(len(partner_ids & returning_ids))},
                    {'label': _('New'), 'value': str(len(partner_ids - returning_ids))},
                ],
            )

        if detail_type == 'customer_mix':
            segment = 'returning' if str(key) == 'returning' else 'new'
            partner_ids = set(selected_orders.mapped('partner_id').ids)
            older_orders = self.env['pos.order'].sudo().search([
                ('company_id', '=', self.env.company.id),
                ('state', 'in', list(PAID_POS_STATES)),
                ('partner_id', 'in', list(partner_ids) or [0]),
                ('date_order', '<', selected_bounds['start']),
            ])
            returning_ids = set(older_orders.mapped('partner_id').ids)
            target_ids = (partner_ids & returning_ids) if segment == 'returning' else (partner_ids - returning_ids)
            partners = self.env['res.partner'].sudo().browse(list(target_ids)).exists()
            rows = []
            for partner in partners:
                orders = self._cw_analytics_partner_orders(selected_orders, partner.id)
                rows.append({
                    'id': f'partner-{partner.id}',
                    'primary': partner.display_name,
                    'secondary': partner.phone or partner.mobile or '',
                    'detail': _('%(count)s wash visit(s)', count=len(orders)),
                    'metric': self._cw_analytics_money_text(sum(self._cw_analytics_order_row(order)['amount'] for order in orders)),
                    'model': 'res.partner',
                    'res_id': partner.id,
                    'icon': 'fa-user',
                })
            rows.sort(key=lambda row: row['primary'])
            return self._cw_analytics_detail_payload(
                detail_type,
                _('Returning Customers') if segment == 'returning' else _('New Customers'),
                _('Customer mix for the selected analytics period.'),
                rows,
                [{'label': _('Customers'), 'value': str(len(rows))}],
            )

        if detail_type == 'revenue_category':
            try:
                category_id = int(key)
            except (TypeError, ValueError):
                category_id = 0
            lines = self._cw_analytics_pos_lines(month_orders).filtered(
                lambda line: (line.product_id.categ_id.id if line.product_id and line.product_id.categ_id else 0) == category_id
            )
            orders = lines.mapped('order_id')
            rows = [self._cw_analytics_order_row(order) for order in orders]
            revenue = sum(self._cw_analytics_line_amount(line) for line in lines)
            category = self.env['product.category'].sudo().browse(category_id).exists() if category_id else False
            return self._cw_analytics_detail_payload(
                detail_type,
                category.display_name if category else _('Other'),
                _('Monthly revenue for this service category.'),
                rows,
                [
                    {'label': _('Orders'), 'value': str(len(rows))},
                    {'label': _('Revenue'), 'value': self._cw_analytics_money_text(revenue)},
                ],
            )

        if detail_type == 'recent_activity':
            model_name = ''
            res_id = 0
            if isinstance(key, str) and ':' in key:
                model_name, raw_id = key.rsplit(':', 1)
                try:
                    res_id = int(raw_id)
                except ValueError:
                    res_id = 0
            if model_name == 'pos.order' and res_id:
                order = self.env['pos.order'].sudo().browse(res_id).exists()
                rows = [self._cw_analytics_order_row(order)] if order else []
                return self._cw_analytics_detail_payload(
                    detail_type, _('Payment received'), order.name if order else '', rows,
                    [{'label': _('Record'), 'value': order.name if order else _('Not found')}],
                )
            if model_name == 'mrp.production' and res_id:
                mo = self.sudo().browse(res_id).exists()
                if mo:
                    service = self._cw_first_value(mo, ['x_cc_service_product_id'])
                    rows = [{
                        'id': f'mo-{mo.id}',
                        'primary': mo.name,
                        'secondary': self._cw_first_value(mo, ['x_cc_customer_name']) or '',
                        'detail': service.display_name if service else '',
                        'timestamp': fields.Datetime.to_string(mo.write_date) if mo.write_date else '',
                        'metric': {'done': _('Finished'), 'cancel': _('Cancelled'), 'progress': _('In Progress'), 'confirmed': _('Waiting')}.get(mo.state, mo.state),
                        'model': 'mrp.production',
                        'res_id': mo.id,
                        'icon': 'fa-car',
                    }]
                    return self._cw_analytics_detail_payload(
                        detail_type, _('Wash Order Activity'), mo.name, rows,
                        [{'label': _('State'), 'value': {'done': _('Finished'), 'cancel': _('Cancelled'), 'progress': _('In Progress'), 'confirmed': _('Waiting')}.get(mo.state, mo.state)}],
                    )
            return self._cw_analytics_detail_payload(detail_type, _('Recent Activity'), _('Record not found.'))

        return self._cw_analytics_detail_payload(
            detail_type,
            _('Analytics Detail'),
            _('No drill-down is available for this item.'),
        )

    # ------------------------------------------------------------------
    # Public RPC
    # ------------------------------------------------------------------
    @api.model
    def get_business_analytics_data(self, period='today'):
        period = 'month' if period == 'month' else 'today'
        selected_bounds = self._cw_analytics_period_bounds(period)
        today_bounds = self._cw_analytics_day_bounds(0)
        yesterday_bounds = self._cw_analytics_day_bounds(-1)
        month_bounds = self._cw_analytics_month_bounds(0)
        previous_month_bounds = self._cw_analytics_month_bounds(-1)

        today_orders = self._cw_analytics_pos_orders(today_bounds)
        yesterday_orders = self._cw_analytics_pos_orders(yesterday_bounds)
        month_orders = self._cw_analytics_pos_orders(month_bounds)
        previous_month_orders = self._cw_analytics_pos_orders(previous_month_bounds)
        selected_orders = today_orders if period == 'today' else month_orders
        selected_lines = self._cw_analytics_pos_lines(selected_orders)

        today_lines = self._cw_analytics_pos_lines(today_orders)
        yesterday_lines = self._cw_analytics_pos_lines(yesterday_orders)
        month_lines = self._cw_analytics_pos_lines(month_orders)
        previous_month_lines = self._cw_analytics_pos_lines(previous_month_orders)
        today_revenue = sum(self._cw_analytics_line_amount(line) for line in today_lines)
        yesterday_revenue = sum(self._cw_analytics_line_amount(line) for line in yesterday_lines)
        month_revenue = sum(self._cw_analytics_line_amount(line) for line in month_lines)
        previous_month_revenue = sum(self._cw_analytics_line_amount(line) for line in previous_month_lines)
        today_customers = today_orders.mapped('partner_id').exists()
        average_ticket = today_revenue / len(today_orders) if today_orders else 0.0

        # Daily wash volume from paid POS visits in three-hour buckets.
        hourly_counts = [0] * 8
        for order in today_orders:
            local_dt = self._cw_analytics_local_datetime(order.date_order)
            if local_dt:
                hourly_counts[min(7, local_dt.hour // 3)] += 1
        daily_washes = [
            {'label': f'{hour:02d}:00', 'value': hourly_counts[index], 'bucket_key': index}
            for index, hour in enumerate(range(0, 24, 3))
        ]

        service_totals = defaultdict(float)
        service_names = {}
        for line in selected_lines:
            qty = float(getattr(line, 'qty', 0.0) or 0.0)
            service_totals[line.product_id.id] += qty
            service_names[line.product_id.id] = line.product_id.display_name

        category_revenue = defaultdict(float)
        category_names = {}
        for line in month_lines:
            category = line.product_id.categ_id if line.product_id else self.env['product.category']
            category_id = category.id or 0
            category_name = category.display_name if category else _('Other')
            category_names[category_id] = category_name
            category_revenue[category_id] += self._cw_analytics_line_amount(line)

        popular_services = [
            {'product_id': product_id, 'name': service_names.get(product_id, _('Service')), 'value': round(value, 2)}
            for product_id, value in sorted(
                service_totals.items(),
                key=lambda item: (-item[1], service_names.get(item[0], '')),
            )[:5]
        ]

        partner_counts = defaultdict(int)
        for order in selected_orders:
            if order.partner_id:
                partner_counts[order.partner_id.id] += 1
        partners = self.env['res.partner'].sudo().browse(list(partner_counts)).exists()
        top_customers = [
            {
                'partner_id': partner.id,
                'name': partner.display_name,
                'washes': partner_counts[partner.id],
                'initial': (partner.display_name or '?')[:1].upper(),
            }
            for partner in partners
        ]
        top_customers.sort(key=lambda item: (-item['washes'], item['name']))
        top_customers = top_customers[:5]

        period_partner_ids = set(partner_counts)
        returning_ids = set()
        if period_partner_ids:
            older_orders = self.env['pos.order'].sudo().search([
                ('company_id', '=', self.env.company.id),
                ('state', 'in', list(PAID_POS_STATES)),
                ('partner_id', 'in', list(period_partner_ids)),
                ('date_order', '<', selected_bounds['start']),
            ])
            returning_ids = set(older_orders.mapped('partner_id').ids)
        returning_count = len(period_partner_ids & returning_ids)
        new_count = len(period_partner_ids - returning_ids)
        mix_total = returning_count + new_count
        returning_percent = round((returning_count / mix_total) * 100.0, 1) if mix_total else 0.0
        customer_mix = {
            'returning': returning_count,
            'new': new_count,
            'returning_percent': returning_percent,
            'new_percent': round(100.0 - returning_percent, 1) if mix_total else 0.0,
        }

        category_total = sum(category_revenue.values())
        revenue_by_category = []
        for category_id, amount in sorted(
            category_revenue.items(),
            key=lambda item: (-item[1], category_names.get(item[0], '')),
        )[:5]:
            revenue_by_category.append({
                'category_id': category_id,
                'name': category_names.get(category_id, _('Other')),
                'amount': round(amount, 2),
                'percent': round((amount / category_total) * 100.0, 1) if category_total else 0.0,
            })

        weekly_revenue = [0.0] * 5
        month_amount_by_order = defaultdict(float)
        for line in month_lines:
            month_amount_by_order[line.order_id.id] += self._cw_analytics_line_amount(line)
        for order in month_orders:
            local_dt = self._cw_analytics_local_datetime(order.date_order)
            if local_dt:
                weekly_revenue[min(4, (local_dt.day - 1) // 7)] += month_amount_by_order.get(order.id, 0.0)
        revenue_trend = [
            {'label': f"{_('Week')} {index + 1}", 'value': round(value, 2), 'week_index': index}
            for index, value in enumerate(weekly_revenue)
            if value or index < 4
        ]

        station_utilization = self._cw_analytics_station_utilization(selected_bounds)
        low_supplies = self._cw_analytics_low_supplies()

        recent_activity = []
        wash_product_ids = self._cw_analytics_wash_product_ids()
        recent_lines = self.env['pos.order.line'].sudo().search([
            ('product_id', 'in', wash_product_ids or [0]),
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.state', 'in', list(PAID_POS_STATES)),
        ], order='order_id desc, id desc', limit=30)
        recent_pos = recent_lines.mapped('order_id').sorted(
            key=lambda order: (order.date_order or fields.Datetime.now(), order.id),
            reverse=True,
        )[:5]
        for order in recent_pos:
            order_lines = recent_lines.filtered(lambda line: line.order_id.id == order.id)
            recent_activity.append({
                'timestamp': fields.Datetime.to_string(order.date_order) if order.date_order else '',
                'type': 'payment',
                'title': _('Payment received'),
                'reference': order.name,
                'detail': order.partner_id.display_name if order.partner_id else _('Walk-in customer'),
                'amount': round(sum(self._cw_analytics_line_amount(line) for line in order_lines), 2),
                'model': 'pos.order',
                'res_id': order.id,
                'detail_key': f'pos.order:{order.id}',
            })

        recent_mos = self.search(
            self._cw_wash_domain(),
            order='write_date desc, id desc',
            limit=5,
        )
        for mo in recent_mos:
            if mo.state == 'done':
                title = _('Car wash completed')
                activity_type = 'done'
                timestamp = mo.date_finished or mo.write_date
            elif mo.state in ('confirmed', 'progress'):
                title = _('Car wash in progress')
                activity_type = 'active'
                timestamp = mo.write_date
            else:
                title = _('Wash order updated')
                activity_type = 'info'
                timestamp = mo.write_date
            recent_activity.append({
                'timestamp': fields.Datetime.to_string(timestamp) if timestamp else '',
                'type': activity_type,
                'title': title,
                'reference': mo.name,
                'detail': self._cw_first_value(mo, ['x_cc_vehicle_plate']) or self._cw_first_value(mo, ['x_cc_customer_name']) or '',
                'amount': False,
                'model': 'mrp.production',
                'res_id': mo.id,
                'detail_key': f'mrp.production:{mo.id}',
            })

        def activity_sort_key(item):
            value = item.get('timestamp') or ''
            return value

        recent_activity.sort(key=activity_sort_key, reverse=True)
        recent_activity = recent_activity[:5]

        currency = self.env.company.currency_id
        return {
            'period': period,
            'period_label': selected_bounds['label'],
            'currency_code': currency.name,
            'currency_symbol': currency.symbol,
            'kpis': {
                'today_revenue': round(today_revenue, 2),
                'today_revenue_growth': self._cw_analytics_growth(today_revenue, yesterday_revenue),
                'monthly_revenue': round(month_revenue, 2),
                'monthly_revenue_growth': self._cw_analytics_growth(month_revenue, previous_month_revenue),
                'total_washes_today': len(today_orders),
                'active_customers': len(today_customers),
                'average_ticket': round(average_ticket, 2),
            },
            'daily_washes': daily_washes,
            'popular_services': popular_services,
            'station_utilization': station_utilization,
            'top_customers': top_customers,
            'low_supplies': low_supplies,
            'revenue_trend': revenue_trend,
            'customer_mix': customer_mix,
            'revenue_by_category': revenue_by_category,
            'recent_activity': recent_activity,
        }
