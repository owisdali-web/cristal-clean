# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models

from .business_analytics import PAID_POS_STATES
from ..dashboard_logic import normalize_vehicle_size


class MrpProductionReportCenter(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _cw_report_filters(self, filters=None):
        values = dict(filters or {})
        return {
            'period': values.get('period') or 'today',
            'date_from': values.get('date_from') or '',
            'date_to': values.get('date_to') or '',
            'station_id': int(values.get('station_id') or 0),
            'service_id': int(values.get('service_id') or 0),
            'vehicle_size': values.get('vehicle_size') or '',
            'customer_id': int(values.get('customer_id') or 0),
            'status': values.get('status') or '',
        }

    @api.model
    def _cw_report_bounds(self, filters):
        user_tz = self._cw_analytics_timezone()
        local_now = datetime.now(user_tz)
        period = filters['period']

        if period == 'custom' and filters['date_from'] and filters['date_to']:
            start_date = fields.Date.from_string(filters['date_from'])
            end_inclusive = fields.Date.from_string(filters['date_to'])
            if end_inclusive < start_date:
                start_date, end_inclusive = end_inclusive, start_date
            end_date = end_inclusive + timedelta(days=1)
        elif period == 'yesterday':
            start_date = local_now.date() - timedelta(days=1)
            end_date = local_now.date()
        elif period == 'week':
            start_date = local_now.date() - timedelta(days=local_now.weekday())
            end_date = start_date + timedelta(days=7)
        elif period == 'month':
            start_date = local_now.date().replace(day=1)
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)
        else:
            start_date = local_now.date()
            end_date = start_date + timedelta(days=1)

        start_local = user_tz.localize(datetime.combine(start_date, time.min))
        end_local = user_tz.localize(datetime.combine(end_date, time.min))
        return {
            'start': self._cw_analytics_to_utc_string(start_local),
            'end': self._cw_analytics_to_utc_string(end_local),
            'start_local': start_local,
            'end_local': end_local,
            'date_from': start_date.isoformat(),
            'date_to': (end_date - timedelta(days=1)).isoformat(),
            'label': start_date.isoformat() if end_date - start_date == timedelta(days=1) else f'{start_date.isoformat()} - {(end_date - timedelta(days=1)).isoformat()}',
        }

    @api.model
    def _cw_report_pos_lines(self, bounds, filters):
        wash_product_ids = self._cw_analytics_wash_product_ids()
        if not wash_product_ids:
            return self.env['pos.order.line'].sudo()
        domain = [
            ('product_id', 'in', wash_product_ids),
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.state', 'in', list(PAID_POS_STATES)),
            ('order_id.date_order', '>=', bounds['start']),
            ('order_id.date_order', '<', bounds['end']),
        ]
        if filters['service_id']:
            domain.append(('product_id', '=', filters['service_id']))
        if filters['customer_id']:
            domain.append(('order_id.partner_id', '=', filters['customer_id']))
        lines = self.env['pos.order.line'].sudo().search(domain, order='id asc')
        lines = lines.sorted(
            key=lambda line: (
                line.order_id.date_order or fields.Datetime.from_string('1970-01-01 00:00:00'),
                line.id,
            )
        )
        if filters['vehicle_size']:
            expected_size = filters['vehicle_size']
            lines = lines.filtered(
                lambda line: normalize_vehicle_size('', line.product_id.display_name) == expected_size
            )
        return lines

    @api.model
    def _cw_report_mos(self, bounds, filters):
        domain = self._cw_wash_domain() + [
            ('create_date', '<', bounds['end']),
            '|', ('date_finished', '=', False), ('date_finished', '>=', bounds['start']),
        ]
        if filters['service_id'] and 'x_cc_service_product_id' in self._fields:
            domain.append(('x_cc_service_product_id', '=', filters['service_id']))
        if filters['vehicle_size'] and 'car_wash_vehicle_size' in self._fields:
            domain.append(('car_wash_vehicle_size', '=', filters['vehicle_size']))
        if filters['status']:
            status_map = {
                'waiting': ['confirmed', 'progress'],
                'in_progress': ['confirmed', 'progress'],
                'finished': ['done'],
                'cancelled': ['cancel'],
            }
            domain.append(('state', 'in', status_map.get(filters['status'], [filters['status']])))
        mos = self.search(domain, order='create_date desc, id desc')

        if filters['station_id']:
            station_id = filters['station_id']
            mos = mos.filtered(lambda mo: station_id in mo.workorder_ids.mapped('workcenter_id').ids)
        if filters['customer_id']:
            partner_id = filters['customer_id']
            mos = mos.filtered(lambda mo: self._cw_sale_order(mo).partner_id.id == partner_id if self._cw_sale_order(mo) else False)
        if filters['status'] in ('waiting', 'in_progress'):
            wants_progress = filters['status'] == 'in_progress'
            mos = mos.filtered(
                lambda mo: bool(mo.workorder_ids.filtered(lambda wo: wo.state == 'progress')) == wants_progress
            )
        return mos

    @api.model
    def _cw_report_duration_minutes(self, workorder):
        if not workorder:
            return 0.0
        if workorder.date_start and workorder.date_finished:
            return max(0.0, (workorder.date_finished - workorder.date_start).total_seconds() / 60.0)
        duration = getattr(workorder, 'duration', 0.0) or 0.0
        return float(duration)

    @api.model
    def _cw_report_operation_row(self, mo):
        workorders = mo.workorder_ids.sorted(key=lambda wo: (wo.date_start or wo.create_date, wo.id))
        wo = workorders[-1] if workorders else self.env['mrp.workorder']
        payload = self._cw_vehicle_payload(mo, wo if wo else False)
        sale = self._cw_sale_order(mo)
        local_dt = self._cw_analytics_local_datetime(mo.date_finished or mo.create_date)
        state_label = {
            'done': _('Finished'),
            'cancel': _('Cancelled'),
            'progress': _('In Progress'),
            'confirmed': _('Waiting'),
        }.get(mo.state, mo.state or '')
        return {
            'id': mo.id,
            'time': local_dt.strftime('%H:%M') if local_dt else '',
            'date': local_dt.strftime('%Y-%m-%d') if local_dt else '',
            'ticket': mo.name,
            'plate': payload.get('plate') or '',
            'vehicle': payload.get('vehicle_model') or '',
            'customer': payload.get('customer_name') or (sale.partner_id.display_name if sale and sale.partner_id else _('Walk-in')),
            'service': payload.get('service_name') or '',
            'station': wo.workcenter_id.name if wo and wo.workcenter_id else '',
            'duration': round(self._cw_report_duration_minutes(wo), 1),
            'amount': False,
            'status': mo.state,
            'status_label': state_label,
            'vehicle_size': payload.get('vehicle_size') or '',
            'model': 'mrp.production',
            'res_id': mo.id,
        }

    @api.model
    def _cw_report_revenue_trend(self, lines, bounds):
        amount_by_order = defaultdict(float)
        for line in lines:
            amount_by_order[line.order_id.id] += self._cw_analytics_line_amount(line)
        orders = lines.mapped('order_id')
        day_count = max(1, (bounds['end_local'].date() - bounds['start_local'].date()).days)
        if day_count == 1:
            values = [0.0] * 8
            labels = [f'{hour:02d}:00' for hour in range(0, 24, 3)]
            for order in orders:
                local_dt = self._cw_analytics_local_datetime(order.date_order)
                if local_dt:
                    values[min(7, local_dt.hour // 3)] += amount_by_order[order.id]
        else:
            values = [0.0] * day_count
            labels = [(bounds['start_local'].date() + timedelta(days=i)).strftime('%d/%m') for i in range(day_count)]
            for order in orders:
                local_dt = self._cw_analytics_local_datetime(order.date_order)
                if local_dt:
                    index = (local_dt.date() - bounds['start_local'].date()).days
                    if 0 <= index < day_count:
                        values[index] += amount_by_order[order.id]
        return [{'label': label, 'value': round(values[i], 2)} for i, label in enumerate(labels)]

    @api.model
    def _cw_report_payment_methods(self, lines):
        order_revenue = defaultdict(float)
        for line in lines:
            order_revenue[line.order_id.id] += self._cw_analytics_line_amount(line)
        totals = defaultdict(float)
        orders = lines.mapped('order_id')
        for order in orders:
            wash_amount = order_revenue[order.id]
            total_order = abs(float(getattr(order, 'amount_total', 0.0) or 0.0))
            ratio = min(1.0, wash_amount / total_order) if total_order else 1.0
            payments = getattr(order, 'payment_ids', self.env['pos.payment'])
            if payments:
                for payment in payments:
                    method = payment.payment_method_id.name if payment.payment_method_id else _('Other')
                    totals[method] += float(payment.amount or 0.0) * ratio
            else:
                totals[_('Unspecified')] += wash_amount
        return [
            {'name': name, 'amount': round(amount, 2)}
            for name, amount in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        ]

    @api.model
    def _cw_report_filter_options(self, lines):
        Workcenter = self.env['mrp.workcenter'].sudo()
        stations = Workcenter.search([
            ('active', '=', True), ('car_wash_enabled', '=', True),
            '|', ('company_id', '=', False), ('company_id', '=', self.env.company.id),
        ], order='car_wash_sequence, sequence, id')
        products = self.env['product.product'].sudo().with_context(active_test=False).browse(self._cw_analytics_wash_product_ids()).exists().sorted('display_name')
        all_customer_lines = self.env['pos.order.line'].sudo().search([
            ('product_id', 'in', self._cw_analytics_wash_product_ids() or [0]),
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.state', 'in', list(PAID_POS_STATES)),
            ('order_id.partner_id', '!=', False),
        ])
        customers = all_customer_lines.mapped('order_id.partner_id').exists().sorted('display_name')
        return {
            'stations': [{'id': row.id, 'name': row.display_name} for row in stations],
            'services': [{'id': row.id, 'name': row.display_name} for row in products],
            'customers': [{'id': row.id, 'name': row.display_name} for row in customers],
        }

    @api.model
    def get_report_center_data(self, filters=None):
        filters = self._cw_report_filters(filters)
        bounds = self._cw_report_bounds(filters)
        lines = self._cw_report_pos_lines(bounds, filters)
        orders = lines.mapped('order_id')
        mos = self._cw_report_mos(bounds, filters)

        revenue = sum(self._cw_analytics_line_amount(line) for line in lines)
        average_ticket = revenue / len(orders) if orders else 0.0
        customers = orders.mapped('partner_id').exists()
        finished = mos.filtered(lambda mo: mo.state == 'done')
        active = mos.filtered(lambda mo: mo.state in ('confirmed', 'progress'))
        progress_ids = set(active.mapped('workorder_ids').filtered(lambda wo: wo.state == 'progress').mapped('production_id').ids)
        waiting = active.filtered(lambda mo: mo.id not in progress_ids)

        service_qty = defaultdict(float)
        service_revenue = defaultdict(float)
        service_names = {}
        for line in lines:
            product = line.product_id
            service_names[product.id] = product.display_name
            service_qty[product.id] += float(getattr(line, 'qty', 0.0) or 0.0)
            service_revenue[product.id] += self._cw_analytics_line_amount(line)
        cars_by_service = [
            {'product_id': pid, 'name': service_names[pid], 'value': round(qty, 2), 'revenue': round(service_revenue[pid], 2)}
            for pid, qty in sorted(service_qty.items(), key=lambda item: (-item[1], service_names[item[0]]))
        ]

        service_durations = defaultdict(list)
        for mo in mos:
            service = self._cw_service(mo)
            if service:
                durations = [self._cw_report_duration_minutes(wo) for wo in mo.workorder_ids if self._cw_report_duration_minutes(wo)]
                if durations:
                    service_durations[service.id].extend(durations)
        services = []
        for row in cars_by_service:
            durations = service_durations.get(row['product_id'], [])
            services.append({
                **row,
                'average_duration': round(sum(durations) / len(durations), 1) if durations else 0.0,
                'sales_percent': round((row['revenue'] / revenue) * 100.0, 1) if revenue else 0.0,
            })

        station_utilization = self._cw_analytics_station_utilization(bounds)
        stations = []
        Workorder = self.env['mrp.workorder'].sudo()
        for row in station_utilization['stations']:
            workorders = Workorder.search([
                ('workcenter_id', '=', row['id']),
                ('production_id.company_id', '=', self.env.company.id),
                ('production_id.x_cc_is_wash_order', '=', True),
                ('date_start', '<', bounds['end']),
                '|', ('date_finished', '=', False), ('date_finished', '>=', bounds['start']),
            ])
            durations = [self._cw_report_duration_minutes(wo) for wo in workorders if self._cw_report_duration_minutes(wo)]
            stations.append({
                **row,
                'cars_served': len(workorders.mapped('production_id')),
                'average_duration': round(sum(durations) / len(durations), 1) if durations else 0.0,
            })

        customer_revenue = defaultdict(float)
        customer_visits = defaultdict(set)
        customer_last = {}
        customer_services = defaultdict(lambda: defaultdict(float))
        for line in lines:
            partner = line.order_id.partner_id
            if not partner:
                continue
            customer_revenue[partner.id] += self._cw_analytics_line_amount(line)
            customer_visits[partner.id].add(line.order_id.id)
            customer_services[partner.id][line.product_id.display_name] += float(getattr(line, 'qty', 0.0) or 0.0)
            local_dt = self._cw_analytics_local_datetime(line.order_id.date_order)
            if local_dt and (partner.id not in customer_last or local_dt > customer_last[partner.id]):
                customer_last[partner.id] = local_dt
        customer_records = self.env['res.partner'].sudo().browse(list(customer_revenue)).exists()
        customer_rows = []
        for partner in customer_records:
            visits = len(customer_visits[partner.id])
            top_service = max(customer_services[partner.id], key=customer_services[partner.id].get) if customer_services[partner.id] else ''
            customer_rows.append({
                'partner_id': partner.id,
                'name': partner.display_name,
                'visits': visits,
                'total_spend': round(customer_revenue[partner.id], 2),
                'average_spend': round(customer_revenue[partner.id] / visits, 2) if visits else 0.0,
                'last_visit': customer_last[partner.id].strftime('%Y-%m-%d %H:%M') if partner.id in customer_last else '',
                'top_service': top_service,
            })
        customer_rows.sort(key=lambda item: (-item['total_spend'], item['name']))

        operations = [self._cw_report_operation_row(mo) for mo in mos[:100]]
        supplies = self._cw_analytics_low_supplies()

        exceptions = []
        now = fields.Datetime.now()
        for mo in mos:
            payload = self._cw_vehicle_payload(mo, queue_item=True)
            progress_wo = mo.workorder_ids.filtered(lambda wo: wo.state == 'progress')[:1]
            if mo.state == 'cancel':
                exceptions.append({'type': 'cancelled', 'severity': 'danger', 'reference': mo.name, 'detail': payload['plate'], 'message': _('Cancelled wash order'), 'res_id': mo.id})
            elif progress_wo and progress_wo.duration_expected and progress_wo.date_start:
                elapsed = max(0.0, (now - progress_wo.date_start).total_seconds() / 60.0)
                if elapsed > float(progress_wo.duration_expected) * 1.25:
                    exceptions.append({'type': 'overdue', 'severity': 'warning', 'reference': mo.name, 'detail': payload['plate'], 'message': _('Wash exceeds expected duration'), 'res_id': mo.id})
            elif mo.state in ('confirmed', 'progress') and payload.get('waiting_minutes', 0) and payload['waiting_minutes'] > 30:
                exceptions.append({'type': 'waiting', 'severity': 'warning', 'reference': mo.name, 'detail': payload['plate'], 'message': _('Waiting longer than 30 minutes'), 'res_id': mo.id})

        return {
            'period_label': bounds['label'],
            'date_from': bounds['date_from'],
            'date_to': bounds['date_to'],
            'currency_code': self.env.company.currency_id.name,
            'currency_symbol': self.env.company.currency_id.symbol,
            'filters': filters,
            'kpis': {
                'total_cars': len(mos),
                'finished_cars': len(finished),
                'waiting_cars': len(waiting),
                'total_revenue': round(revenue, 2),
                'average_ticket': round(average_ticket, 2),
                'unique_customers': len(customers),
            },
            'revenue_trend': self._cw_report_revenue_trend(lines, bounds),
            'cars_by_service': cars_by_service,
            'payment_methods': self._cw_report_payment_methods(lines),
            'operations': operations,
            'services': services,
            'stations': stations,
            'customers': customer_rows,
            'supplies': supplies,
            'exceptions': exceptions,
            'filter_options': self._cw_report_filter_options(lines),
        }
