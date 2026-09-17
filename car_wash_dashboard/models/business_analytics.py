# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models


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
            'label': start_local.strftime('%B %Y'),
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
            {'label': f'{hour:02d}:00', 'value': hourly_counts[index]}
            for index, hour in enumerate(range(0, 24, 3))
        ]

        service_totals = defaultdict(float)
        for line in selected_lines:
            qty = float(getattr(line, 'qty', 0.0) or 0.0)
            service_totals[line.product_id.display_name] += qty

        category_revenue = defaultdict(float)
        for line in month_lines:
            category_name = (
                line.product_id.categ_id.display_name
                if line.product_id and line.product_id.categ_id
                else 'Other'
            )
            category_revenue[category_name] += self._cw_analytics_line_amount(line)

        popular_services = [
            {'name': name, 'value': round(value, 2)}
            for name, value in sorted(service_totals.items(), key=lambda item: (-item[1], item[0]))[:5]
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
        for name, amount in sorted(category_revenue.items(), key=lambda item: (-item[1], item[0]))[:5]:
            revenue_by_category.append({
                'name': name,
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
            {'label': f'Week {index + 1}', 'value': round(value, 2)}
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
                'title': 'Payment received',
                'reference': order.name,
                'detail': order.partner_id.display_name if order.partner_id else 'Walk-in customer',
                'amount': round(sum(self._cw_analytics_line_amount(line) for line in order_lines), 2),
            })

        recent_mos = self.search(
            self._cw_wash_domain(),
            order='write_date desc, id desc',
            limit=5,
        )
        for mo in recent_mos:
            if mo.state == 'done':
                title = 'Car wash completed'
                activity_type = 'done'
                timestamp = mo.date_finished or mo.write_date
            elif mo.state in ('confirmed', 'progress'):
                title = 'Car wash in progress'
                activity_type = 'active'
                timestamp = mo.write_date
            else:
                title = 'Wash order updated'
                activity_type = 'info'
                timestamp = mo.write_date
            recent_activity.append({
                'timestamp': fields.Datetime.to_string(timestamp) if timestamp else '',
                'type': activity_type,
                'title': title,
                'reference': mo.name,
                'detail': self._cw_first_value(mo, ['x_cc_vehicle_plate']) or self._cw_first_value(mo, ['x_cc_customer_name']) or '',
                'amount': False,
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
