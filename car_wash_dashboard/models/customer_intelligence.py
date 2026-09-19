# -*- coding: utf-8 -*-
"""Read-only customer intelligence for the Crystal Clean dashboard."""

from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models

from ..customer_logic import FREQUENT_VISITS_MIN, INACTIVE_DAYS, customer_segment, high_value_cutoff


PAID_POS_STATES = ('paid', 'done', 'invoiced')


class MrpProductionCustomerIntelligence(models.Model):
    _inherit = 'mrp.production'

    @api.model
    def _cw_customer_filters(self, values=None):
        values = values or {}
        try:
            service_id = int(values.get('service_id') or 0)
        except (TypeError, ValueError):
            service_id = 0
        return {
            'search': str(values.get('search') or '').strip().lower(),
            'segment': str(values.get('segment') or '').strip().lower(),
            'service_id': service_id,
            'activity_period': str(values.get('activity_period') or 'all').strip().lower(),
        }

    @api.model
    def _cw_customer_paid_lines(self):
        product_ids = self._cw_analytics_wash_product_ids()
        if not product_ids:
            return self.env['pos.order.line'].sudo()
        return self.env['pos.order.line'].sudo().search([
            ('product_id', 'in', product_ids),
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.state', 'in', list(PAID_POS_STATES)),
            ('order_id.partner_id', '!=', False),
        ], order='id asc')

    @api.model
    def _cw_customer_vehicle_map(self, partner_ids):
        vehicle_map = defaultdict(dict)
        if not partner_ids:
            return vehicle_map

        productions = self.search(self._cw_wash_domain(), order='create_date desc, id desc')
        for production in productions:
            sale = self._cw_sale_order(production)
            partner = sale.partner_id if sale and sale.partner_id else False
            if not partner or partner.id not in partner_ids:
                continue

            payload = self._cw_vehicle_payload(production)
            plate = str(payload.get('plate') or '').strip()
            if plate.lower() == 'no plate':
                plate = ''
            model = str(payload.get('vehicle_model') or '').strip()
            if not plate and not model:
                continue

            key = (plate.lower() if plate else f"model:{model.lower()}:{payload.get('vehicle_size') or ''}")
            if key in vehicle_map[partner.id]:
                continue
            vehicle_map[partner.id][key] = {
                'plate': plate,
                'model': model,
                'color': payload.get('vehicle_color') or '',
                'size': payload.get('vehicle_size') or '',
                'visual': payload.get('vehicle_visual') or 'small',
                'production_id': production.id,
            }
        return vehicle_map

    @api.model
    def _cw_customer_aggregate(self, lines):
        customer_revenue = defaultdict(float)
        customer_visits = defaultdict(set)
        customer_first = {}
        customer_last = {}
        customer_services = defaultdict(lambda: defaultdict(float))
        customer_service_ids = defaultdict(set)

        for line in lines:
            order = line.order_id
            partner = order.partner_id
            if not partner:
                continue
            customer_revenue[partner.id] += self._cw_analytics_line_amount(line)
            customer_visits[partner.id].add(order.id)
            customer_services[partner.id][line.product_id.display_name] += float(line.qty or 0.0)
            customer_service_ids[partner.id].add(line.product_id.id)
            local_dt = self._cw_analytics_local_datetime(order.date_order)
            if local_dt:
                if partner.id not in customer_first or local_dt < customer_first[partner.id]:
                    customer_first[partner.id] = local_dt
                if partner.id not in customer_last or local_dt > customer_last[partner.id]:
                    customer_last[partner.id] = local_dt

        return {
            'revenue': customer_revenue,
            'visits': customer_visits,
            'first': customer_first,
            'last': customer_last,
            'services': customer_services,
            'service_ids': customer_service_ids,
        }

    @api.model
    def _cw_customer_scope_partner_ids(self, all_lines, filters):
        scoped = all_lines
        if filters['service_id']:
            scoped = scoped.filtered(lambda line: line.product_id.id == filters['service_id'])

        if filters['activity_period'] in {'30', '90', '365'}:
            threshold = fields.Datetime.now() - timedelta(days=int(filters['activity_period']))
            scoped = scoped.filtered(lambda line: bool(line.order_id.date_order and line.order_id.date_order >= threshold))

        return set(scoped.mapped('order_id.partner_id').ids), scoped

    @api.model
    def get_customer_intelligence_data(self, filters=None):
        filters = self._cw_customer_filters(filters)
        all_lines = self._cw_customer_paid_lines()
        aggregation = self._cw_customer_aggregate(all_lines)
        partner_ids = set(aggregation['revenue'])
        scoped_partner_ids, scoped_lines = self._cw_customer_scope_partner_ids(all_lines, filters)
        if filters['service_id'] or filters['activity_period'] != 'all':
            partner_ids &= scoped_partner_ids

        partners = self.env['res.partner'].sudo().browse(sorted(partner_ids)).exists()
        vehicle_map = self._cw_customer_vehicle_map(set(partners.ids))
        spend_values = [aggregation['revenue'][partner.id] for partner in partners]
        high_value_threshold = high_value_cutoff(spend_values)
        user_today = self._cw_analytics_local_datetime(fields.Datetime.now()).date()
        month_start = user_today.replace(day=1)

        rows = []
        for partner in partners:
            visits = len(aggregation['visits'][partner.id])
            total_spend = aggregation['revenue'][partner.id]
            first_visit = aggregation['first'].get(partner.id)
            last_visit = aggregation['last'].get(partner.id)
            days_since_last = (user_today - last_visit.date()).days if last_visit else 999999
            segment = customer_segment(visits, total_spend, days_since_last, high_value_threshold)
            service_counts = aggregation['services'][partner.id]
            preferred_service = max(service_counts, key=service_counts.get) if service_counts else ''
            vehicles = list(vehicle_map.get(partner.id, {}).values())
            phone = partner.phone or partner.mobile or ''

            row = {
                'id': partner.id,
                'partner_id': partner.id,
                'name': partner.display_name,
                'phone': phone,
                'mobile': partner.mobile or '',
                'email': partner.email or '',
                'visits': visits,
                'total_spend': round(total_spend, 2),
                'average_spend': round(total_spend / visits, 2) if visits else 0.0,
                'first_visit': first_visit.strftime('%Y-%m-%d') if first_visit else '',
                'last_visit': last_visit.strftime('%Y-%m-%d %H:%M') if last_visit else '',
                'days_since_last': days_since_last,
                'preferred_service': preferred_service,
                'vehicle_count': len(vehicles),
                'vehicle_plates': [vehicle['plate'] for vehicle in vehicles if vehicle.get('plate')],
                'segment': segment,
                'is_new_this_month': bool(first_visit and first_visit.date() >= month_start),
                'model': 'res.partner',
                'res_id': partner.id,
            }

            search = filters['search']
            if search:
                haystack = ' '.join([
                    row['name'], row['phone'], row['mobile'], row['email'],
                    row['preferred_service'], ' '.join(row['vehicle_plates']),
                ]).lower()
                if search not in haystack:
                    continue
            if filters['segment'] and row['segment'] != filters['segment']:
                continue
            rows.append(row)

        rows.sort(key=lambda row: (-row['total_spend'], -row['visits'], row['name']))
        filtered_ids = {row['partner_id'] for row in rows}
        filtered_lines = all_lines.filtered(lambda line: line.order_id.partner_id.id in filtered_ids)
        if filters['service_id']:
            filtered_lines = filtered_lines.filtered(lambda line: line.product_id.id == filters['service_id'])

        service_totals = defaultdict(float)
        service_ids = {}
        for line in filtered_lines:
            service_totals[line.product_id.display_name] += float(line.qty or 0.0)
            service_ids[line.product_id.display_name] = line.product_id.id

        total_spend = sum(row['total_spend'] for row in rows)
        returning_count = sum(1 for row in rows if row['visits'] > 1)
        new_count = sum(1 for row in rows if row['visits'] <= 1)

        services = self.env['product.product'].sudo().with_context(active_test=False).browse(
            self._cw_analytics_wash_product_ids()
        ).exists().sorted('display_name')

        return {
            'kpis': {
                'total_customers': len(rows),
                'new_this_month': sum(1 for row in rows if row['is_new_this_month']),
                'returning_customers': returning_count,
                'frequent_customers': sum(1 for row in rows if row['visits'] >= FREQUENT_VISITS_MIN),
                'inactive_customers': sum(1 for row in rows if row['days_since_last'] > INACTIVE_DAYS),
                'average_spend': round(total_spend / len(rows), 2) if rows else 0.0,
            },
            'customers': rows,
            'top_by_revenue': [
                {'partner_id': row['partner_id'], 'name': row['name'], 'value': row['total_spend']}
                for row in rows[:6]
            ],
            'most_frequent': [
                {'partner_id': row['partner_id'], 'name': row['name'], 'value': row['visits']}
                for row in sorted(rows, key=lambda row: (-row['visits'], -row['total_spend'], row['name']))[:6]
            ],
            'new_vs_returning': [
                {'key': 'new', 'label': _('New'), 'value': new_count},
                {'key': 'returning', 'label': _('Returning'), 'value': returning_count},
            ],
            'service_preferences': [
                {
                    'product_id': service_ids[name],
                    'name': name,
                    'value': round(value, 2),
                }
                for name, value in sorted(service_totals.items(), key=lambda item: (-item[1], item[0]))[:6]
            ],
            'filter_options': {
                'services': [{'id': product.id, 'name': product.display_name} for product in services],
                'segments': ['new', 'regular', 'frequent', 'high_value', 'inactive'],
            },
            'currency_code': self.env.company.currency_id.name,
            'currency_symbol': self.env.company.currency_id.symbol,
            'high_value_threshold': round(high_value_threshold, 2),
        }

    @api.model
    def get_customer_intelligence_detail(self, partner_id):
        try:
            partner_id = int(partner_id or 0)
        except (TypeError, ValueError):
            partner_id = 0
        partner = self.env['res.partner'].sudo().browse(partner_id).exists()
        if not partner:
            return {}

        all_lines = self._cw_customer_paid_lines().filtered(lambda line: line.order_id.partner_id.id == partner.id)
        if not all_lines:
            return {}

        orders = all_lines.mapped('order_id').sorted(
            key=lambda order: (order.date_order or fields.Datetime.now(), order.id), reverse=True
        )
        revenue = sum(self._cw_analytics_line_amount(line) for line in all_lines)
        service_totals = defaultdict(lambda: {'qty': 0.0, 'revenue': 0.0})
        for line in all_lines:
            service_totals[line.product_id.display_name]['qty'] += float(line.qty or 0.0)
            service_totals[line.product_id.display_name]['revenue'] += self._cw_analytics_line_amount(line)

        vehicles = list(self._cw_customer_vehicle_map({partner.id}).get(partner.id, {}).values())

        timeline = []
        for order in orders[:30]:
            order_lines = all_lines.filtered(lambda line: line.order_id.id == order.id)
            local_dt = self._cw_analytics_local_datetime(order.date_order)
            timeline.append({
                'kind': 'pos',
                'model': 'pos.order',
                'res_id': order.id,
                'reference': order.name,
                'date': local_dt.strftime('%Y-%m-%d %H:%M') if local_dt else '',
                'sort_value': fields.Datetime.to_string(order.date_order) if order.date_order else '',
                'title': ', '.join(order_lines.mapped('product_id').mapped('display_name')),
                'amount': round(sum(self._cw_analytics_line_amount(line) for line in order_lines), 2),
                'status': _('Paid POS Visit'),
            })

        production_state_labels = {
            'draft': _('Draft'),
            'confirmed': _('Confirmed'),
            'progress': _('In Progress'),
            'to_close': _('To Close'),
            'done': _('Done'),
            'cancel': _('Cancelled'),
        }
        productions = self.search(self._cw_wash_domain(), order='create_date desc, id desc')
        for production in productions:
            sale = self._cw_sale_order(production)
            if not sale or sale.partner_id.id != partner.id:
                continue
            payload = self._cw_vehicle_payload(production)
            workcenter_names = production.workorder_ids.mapped('workcenter_id').mapped('display_name')
            event_dt = production.date_finished or production.create_date
            local_dt = self._cw_analytics_local_datetime(event_dt)
            timeline.append({
                'kind': 'wash',
                'model': 'mrp.production',
                'res_id': production.id,
                'reference': production.name,
                'date': local_dt.strftime('%Y-%m-%d %H:%M') if local_dt else '',
                'sort_value': fields.Datetime.to_string(event_dt) if event_dt else '',
                'title': payload.get('service_name') or _('Car Wash Service'),
                'plate': payload.get('plate') or '',
                'vehicle': payload.get('vehicle_model') or '',
                'station': ', '.join(workcenter_names),
                'status': production_state_labels.get(production.state, production.state),
            })

        timeline.sort(key=lambda item: item.get('sort_value') or '', reverse=True)
        last_order = orders[:1]
        first_order = orders[-1:] if orders else self.env['pos.order']
        last_dt = self._cw_analytics_local_datetime(last_order.date_order) if last_order else False
        first_dt = self._cw_analytics_local_datetime(first_order.date_order) if first_order else False

        services = [
            {
                'name': name,
                'qty': round(values['qty'], 2),
                'revenue': round(values['revenue'], 2),
            }
            for name, values in sorted(service_totals.items(), key=lambda item: (-item[1]['revenue'], item[0]))
        ]

        return {
            'partner_id': partner.id,
            'model': 'res.partner',
            'res_id': partner.id,
            'name': partner.display_name,
            'phone': partner.phone or '',
            'mobile': partner.mobile or '',
            'email': partner.email or '',
            'visits': len(orders),
            'total_spend': round(revenue, 2),
            'average_spend': round(revenue / len(orders), 2) if orders else 0.0,
            'first_visit': first_dt.strftime('%Y-%m-%d') if first_dt else '',
            'last_visit': last_dt.strftime('%Y-%m-%d %H:%M') if last_dt else '',
            'vehicles': vehicles,
            'timeline': timeline[:40],
            'services': services,
            'currency_code': self.env.company.currency_id.name,
            'currency_symbol': self.env.company.currency_id.symbol,
        }
