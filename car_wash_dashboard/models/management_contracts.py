# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class MrpProductionManagementContracts(models.Model):
    _inherit = 'mrp.production'

    # ------------------------------------------------------------------
    # V18 access boundary
    # ------------------------------------------------------------------
    @api.model
    def _cw_management_access_allowed(self):
        user = self.env.user
        return bool(
            user.has_group('car_wash_dashboard.group_car_wash_manager')
            or user.has_group('base.group_system')
        )

    @api.model
    def _cw_require_management_access(self):
        if not self._cw_management_access_allowed():
            raise AccessError(_('You are not allowed to access Crystal Clean management analytics.'))
        return True

    # ------------------------------------------------------------------
    # Shared commercial helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_v18_pos_lines(self, start_dt, end_dt, service_products=None):
        if 'pos.order.line' not in self.env.registry.models:
            return self.env['pos.order.line'].browse() if 'pos.order.line' in self.env.registry.models else []
        service_products = service_products or self._cw_service_templates().mapped('product_variant_ids')
        if not service_products:
            return self.env['pos.order.line'].browse()
        return self.env['pos.order.line'].search([
            ('order_id.company_id', '=', self.env.company.id),
            ('order_id.date_order', '>=', start_dt),
            ('order_id.date_order', '<', end_dt),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('product_id', 'in', service_products.ids),
        ])

    @api.model
    def _cw_v18_commercial_summary(self):
        today_start, today_end, local_today = self._cw_day_bounds(0)
        service_products = self._cw_service_templates().mapped('product_variant_ids')
        today_lines = self._cw_v18_pos_lines(today_start, today_end, service_products)
        today_orders = today_lines.mapped('order_id') if today_lines else self.env['pos.order'].browse()

        user_tz = self.env.user.tz or 'UTC'
        import pytz
        tz = pytz.timezone(user_tz)
        month_start_local = tz.localize(datetime.combine(local_today.replace(day=1), time.min))
        month_start = fields.Datetime.to_string(month_start_local.astimezone(pytz.utc).replace(tzinfo=None))
        month_lines = self._cw_v18_pos_lines(month_start, today_end, service_products)
        month_orders = month_lines.mapped('order_id') if month_lines else self.env['pos.order'].browse()

        top = defaultdict(lambda: {'qty': 0.0, 'amount': 0.0, 'orders': set()})
        for line in today_lines:
            bucket = top[line.product_id.display_name]
            bucket['qty'] += line.qty
            bucket['amount'] += line.price_subtotal_incl
            bucket['orders'].add(line.order_id.id)
        top_services = [
            {
                'name': name,
                'qty': round(vals['qty'], 2),
                'amount': round(vals['amount'], 2),
                'orders': len(vals['orders']),
            }
            for name, vals in top.items()
        ]
        top_services.sort(key=lambda row: (row['amount'], row['qty']), reverse=True)

        revenue_today = round(sum(today_lines.mapped('price_subtotal_incl')), 2) if today_lines else 0.0
        revenue_month = round(sum(month_lines.mapped('price_subtotal_incl')), 2) if month_lines else 0.0
        return {
            'service_product_ids': service_products.ids,
            'pos_sales_today': revenue_today,
            'pos_orders_today': len(today_orders),
            'average_ticket_today': round(revenue_today / len(today_orders), 2) if today_orders else 0.0,
            'pos_sales_month': revenue_month,
            'pos_orders_month': len(month_orders),
            'top_services_today': top_services[:8],
        }

    @api.model
    def _cw_v18_financial_summary(self, pos_sales_today):
        today = fields.Date.context_today(self)
        company = self.env.company
        result = {
            'collected_today': 0.0,
            'posted_expenses_today': 0.0,
            'posted_expenses_month': 0.0,
            'receivable_open': 0.0,
            'payable_open': 0.0,
            'operational_balance_today': round(pos_sales_today, 2),
        }

        if 'account.move.line' in self.env.registry.models:
            Line = self.env['account.move.line']
            expense_base = [
                ('company_id', '=', company.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ['expense', 'expense_direct_cost']),
            ]
            today_lines = Line.search(expense_base + [('date', '=', fields.Date.to_string(today))])
            month_lines = Line.search(expense_base + [('date', '>=', fields.Date.to_string(today.replace(day=1)))])
            result['posted_expenses_today'] = round(sum((l.debit - l.credit) for l in today_lines), 2)
            result['posted_expenses_month'] = round(sum((l.debit - l.credit) for l in month_lines), 2)

        if 'account.move' in self.env.registry.models:
            Move = self.env['account.move']
            receivables = Move.search([
                ('company_id', '=', company.id), ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice'), ('payment_state', 'not in', ['paid', 'reversed']),
            ])
            payables = Move.search([
                ('company_id', '=', company.id), ('state', '=', 'posted'),
                ('move_type', '=', 'in_invoice'), ('payment_state', 'not in', ['paid', 'reversed']),
            ])
            result['receivable_open'] = round(sum(receivables.mapped('amount_residual')), 2)
            result['payable_open'] = round(sum(payables.mapped('amount_residual')), 2)

        if 'account.payment' in self.env.registry.models:
            Payment = self.env['account.payment']
            domain = [
                ('company_id', '=', company.id),
                ('date', '=', fields.Date.to_string(today)),
                ('payment_type', '=', 'inbound'),
                ('partner_type', '=', 'customer'),
            ]
            if 'state' in Payment._fields:
                domain.append(('state', 'not in', ['draft', 'cancel', 'canceled', 'rejected']))
            result['collected_today'] = round(sum(Payment.search(domain).mapped('amount')), 2)

        result['operational_balance_today'] = round(
            pos_sales_today - result['posted_expenses_today'], 2
        )
        return result

    # ------------------------------------------------------------------
    # V18 Manager contract
    # ------------------------------------------------------------------
    @api.model
    def _cw_management_contract(self):
        commercial = self._cw_v18_commercial_summary()
        finance = self._cw_v18_financial_summary(commercial['pos_sales_today'])
        operations = self.get_operations_data()
        intelligence = self.get_operational_intelligence_data()

        stations = intelligence.get('stations', [])
        live_capacity = sum(max(int(row.get('capacity') or 1), 1) for row in stations)
        live_occupancy = sum(int(row.get('occupancy') or 0) for row in stations)
        live_occupancy_pct = round((live_occupancy / live_capacity) * 100.0, 1) if live_capacity else 0.0

        return {
            'contract_version': '18.0-management',
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
            'company_id': self.env.company.id,
            'company_name': self.env.company.display_name,
            'currency_symbol': self.env.company.currency_id.symbol or '',
            'commercial': commercial,
            'financial': finance,
            'operations': {
                'active_vehicles': operations.get('kpis', {}).get('active_vehicles', 0),
                'running_jobs': intelligence.get('kpis', {}).get('running_jobs', 0),
                'queued_jobs': intelligence.get('kpis', {}).get('queued_jobs', 0),
                'ready_for_pickup': operations.get('kpis', {}).get('ready_for_delivery', 0),
                'completed_today': intelligence.get('kpis', {}).get('completed_today', 0),
                'avg_completed_duration_today_minutes': intelligence.get('kpis', {}).get('avg_completed_duration_today_minutes', 0.0),
                'delayed_running_jobs': intelligence.get('kpis', {}).get('delayed_running_jobs', 0),
                'station_live_occupancy_pct': live_occupancy_pct,
                'overloaded_stations': len(intelligence.get('diagnostics', {}).get('overloaded_station_ids', [])),
                'projection_reliable_for_all_stations': intelligence.get('kpis', {}).get('projection_reliable_for_all_stations', True),
            },
            'stations': [
                {
                    'station_id': row.get('station_id'),
                    'station_code': row.get('station_code'),
                    'station_name': row.get('station_name'),
                    'runtime_state': row.get('runtime_state'),
                    'capacity': row.get('capacity', 1),
                    'occupancy': row.get('occupancy', 0),
                    'queue_count': row.get('queue_count', 0),
                    'done_today': row.get('done_today', 0),
                    'done_last_60_minutes': row.get('done_last_60_minutes', 0),
                    'avg_duration_today_minutes': row.get('avg_duration_today_minutes', 0.0),
                    'delayed_running_jobs': row.get('delayed_running_jobs', 0),
                }
                for row in stations
            ],
            'semantics': {
                'pos_sales': 'Operational wash-service sales from paid/done/invoiced POS lines only.',
                'operational_balance_today': 'POS wash-service sales today minus posted expense move lines today; this is not accounting profit or cash profit.',
                'collected_today': 'Inbound customer payments posted/processed today; this may differ from POS sales.',
                'station_live_occupancy_pct': 'Current running Work Orders divided by configured live station capacity; not historical utilization.',
                'station_revenue': 'Intentionally not allocated. A vehicle may pass through multiple Work Centers, so V18 does not duplicate revenue by station.',
            },
        }

    @api.model
    def get_management_data(self):
        self._cw_require_management_access()
        return self._cw_management_contract()

    # ------------------------------------------------------------------
    # V18 Materials contract
    # ------------------------------------------------------------------
    @api.model
    def _cw_materials_contract(self):
        company = self.env.company
        service_templates = self._cw_service_templates()
        products = self._cw_material_products(service_templates)
        Quant = self.env['stock.quant']
        Orderpoint = self.env['stock.warehouse.orderpoint']
        rows = []

        for product in products.sorted(key=lambda p: p.display_name):
            quants = Quant.search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
                '|', ('company_id', '=', False), ('company_id', '=', company.id),
            ])
            on_hand = sum(quants.mapped('quantity'))
            reserved = sum(quants.mapped('reserved_quantity'))
            free_qty = on_hand - reserved

            op_domain = [('product_id', '=', product.id)]
            if 'company_id' in Orderpoint._fields:
                op_domain += ['|', ('company_id', '=', False), ('company_id', '=', company.id)]
            orderpoints = Orderpoint.search(op_domain)
            min_qty = max(orderpoints.mapped('product_min_qty') or [0.0])
            has_minimum = bool(orderpoints and min_qty > 0)

            locations = []
            for quant in quants.filtered(lambda q: (q.quantity or 0.0) or (q.reserved_quantity or 0.0)):
                locations.append({
                    'location_id': quant.location_id.id,
                    'location_name': quant.location_id.display_name,
                    'quantity': round(quant.quantity or 0.0, 2),
                    'reserved': round(quant.reserved_quantity or 0.0, 2),
                    'free': round((quant.quantity or 0.0) - (quant.reserved_quantity or 0.0), 2),
                })

            rows.append({
                'product_id': product.id,
                'product_name': product.display_name,
                'uom': product.uom_id.name or '',
                'on_hand': round(on_hand, 2),
                'reserved': round(reserved, 2),
                'free': round(free_qty, 2),
                'minimum': round(min_qty, 2),
                'has_minimum': has_minimum,
                'is_low': bool(has_minimum and free_qty < min_qty),
                'standard_cost': round(product.standard_price or 0.0, 4),
                'free_stock_value': round(free_qty * (product.standard_price or 0.0), 2),
                'locations': locations,
            })

        rows = self._cw_apply_material_burn_rate(rows)
        rows.sort(key=lambda r: (0 if r.get('is_low') else 1, r.get('days_remaining') if r.get('days_remaining') is not False else 999999, r['product_name']))

        return {
            'contract_version': '18.0-materials',
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
            'company_id': company.id,
            'company_name': company.display_name,
            'currency_symbol': company.currency_id.symbol or '',
            'scope': {
                'inventory_scope': 'all_internal_locations_in_company',
                'dedicated_car_wash_location_configured': False,
            },
            'kpis': {
                'material_count': len(rows),
                'low_stock_count': sum(1 for row in rows if row.get('is_low')),
                'reserved_material_count': sum(1 for row in rows if (row.get('reserved') or 0.0) > 0),
                'under_3_days_count': sum(1 for row in rows if row.get('days_remaining') is not False and row.get('days_remaining') < 3),
                'free_stock_value': round(sum(row.get('free_stock_value', 0.0) for row in rows), 2),
            },
            'materials': rows,
            'semantics': {
                'inventory_scope': 'Quantities are currently aggregated across all internal locations of the company because no dedicated car-wash stock location is configured in this module.',
                'consumption': '30-day burn rate uses done raw-material stock moves linked to wash Manufacturing Orders.',
                'days_remaining': 'Free quantity divided by average daily consumption over the last 30 days; False means no measurable 30-day consumption.',
                'minimum': 'Maximum configured reordering minimum for the product in the current/shared company scope.',
            },
        }

    @api.model
    def get_materials_data(self):
        self._cw_require_management_access()
        return self._cw_materials_contract()

    # ------------------------------------------------------------------
    # V18 Customers contract
    # ------------------------------------------------------------------
    @api.model
    def _cw_customers_contract(self):
        company = self.env.company
        service_products = self._cw_service_templates().mapped('product_variant_ids')
        now = fields.Datetime.now()
        year_start = fields.Datetime.to_string(now - timedelta(days=365))
        today_start, today_end, local_today = self._cw_day_bounds(0)
        import pytz
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        month_local = tz.localize(datetime.combine(local_today.replace(day=1), time.min))
        month_start = fields.Datetime.to_string(month_local.astimezone(pytz.utc).replace(tzinfo=None))

        if 'pos.order.line' not in self.env.registry.models or not service_products:
            return {
                'contract_version': '18.0-customers',
                'generated_at': fields.Datetime.to_string(now),
                'company_id': company.id,
                'kpis': {},
                'customers': [],
                'semantics': {},
            }

        lines = self.env['pos.order.line'].search([
            ('order_id.company_id', '=', company.id),
            ('order_id.date_order', '>=', year_start),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('product_id', 'in', service_products.ids),
            ('order_id.partner_id', '!=', False),
        ], order='order_id.date_order desc', limit=20000)

        buckets = {}
        served_today = set()
        active_month = set()
        for line in lines:
            order = line.order_id
            partner = order.partner_id
            if not partner:
                continue
            bucket = buckets.setdefault(partner.id, {
                'partner': partner,
                'orders': set(),
                'spend': 0.0,
                'last_visit': False,
                'services': defaultdict(float),
            })
            bucket['orders'].add(order.id)
            bucket['spend'] += line.price_subtotal_incl
            bucket['services'][line.product_id.display_name] += line.qty
            if order.date_order and (not bucket['last_visit'] or order.date_order > bucket['last_visit']):
                bucket['last_visit'] = order.date_order
            order_s = fields.Datetime.to_string(order.date_order) if order.date_order else ''
            if order_s and today_start <= order_s < today_end:
                served_today.add(partner.id)
            if order_s and order_s >= month_start:
                active_month.add(partner.id)

        cutoff_30 = now - timedelta(days=30)
        rows = []
        repeat = 0
        inactive_30 = 0
        for partner_id, vals in buckets.items():
            partner = vals['partner']
            visits = len(vals['orders'])
            if visits > 1:
                repeat += 1
            if vals['last_visit'] and vals['last_visit'] < cutoff_30:
                inactive_30 += 1
            favorite = max(vals['services'].items(), key=lambda item: item[1])[0] if vals['services'] else ''
            rows.append({
                'partner_id': partner_id,
                'name': partner.display_name or '',
                'phone': partner.mobile or partner.phone or '',
                'visits_365d': visits,
                'spend_365d': round(vals['spend'], 2),
                'last_visit': fields.Datetime.context_timestamp(self, vals['last_visit']).strftime('%Y-%m-%d') if vals['last_visit'] else '',
                'favorite_service': favorite,
                'repeat_customer': visits > 1,
                'active_last_30_days': bool(vals['last_visit'] and vals['last_visit'] >= cutoff_30),
            })
        rows.sort(key=lambda r: (r['visits_365d'], r['spend_365d']), reverse=True)

        return {
            'contract_version': '18.0-customers',
            'generated_at': fields.Datetime.to_string(now),
            'company_id': company.id,
            'company_name': company.display_name,
            'currency_symbol': company.currency_id.symbol or '',
            'kpis': {
                'known_customers_365d': len(rows),
                'repeat_customers_365d': repeat,
                'customers_served_today': len(served_today),
                'active_customers_month': len(active_month),
                'inactive_over_30_days': inactive_30,
            },
            'customers': rows[:100],
            'semantics': {
                'population': 'Named customers on paid/done/invoiced wash-service POS orders observed during the rolling last 365 days.',
                'repeat_customer': 'More than one distinct wash POS order within the rolling 365-day window.',
                'customers_served_today': 'Customers with at least one qualifying wash POS order today; this does not mean first-time/new customers.',
                'active_customers_month': 'Customers with a qualifying wash POS order since the first day of the current month; this does not mean newly acquired customers.',
                'spend': 'Wash-service POS line value only; other products/services are excluded.',
            },
        }

    @api.model
    def get_customers_data(self):
        self._cw_require_management_access()
        return self._cw_customers_contract()

    # ------------------------------------------------------------------
    # V18 Team contract
    # ------------------------------------------------------------------
    @api.model
    def _cw_team_contract(self):
        company = self.env.company
        now = fields.Datetime.now()
        today_start, today_end, _today = self._cw_day_bounds(0)

        group_ids = []
        for xmlid in [
            'mrp.group_mrp_user', 'mrp.group_mrp_manager',
            'mrp_workorder.group_mrp_routing',
            'point_of_sale.group_pos_user', 'point_of_sale.group_pos_manager',
            'stock.group_stock_user', 'stock.group_stock_manager',
        ]:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                group_ids.append(group.id)

        user_domain = [('share', '=', False), ('active', '=', True)]
        if 'company_ids' in self.env['res.users']._fields:
            user_domain.append(('company_ids', 'in', [company.id]))
        if group_ids and 'groups_id' in self.env['res.users']._fields:
            user_domain.append(('groups_id', 'in', group_ids))
        users = self.env['res.users'].search(user_domain, order='name')

        employee_model = self.env['hr.employee'] if 'hr.employee' in self.env.registry.models else False
        attendance_model = self.env['hr.attendance'] if 'hr.attendance' in self.env.registry.models else False

        employee_by_user = {}
        if employee_model and users:
            employees = employee_model.search([('user_id', 'in', users.ids)]) if 'user_id' in employee_model._fields else employee_model.browse()
            employee_by_user = {emp.user_id.id: emp for emp in employees if emp.user_id}

        attendance_by_employee = defaultdict(list)
        if attendance_model and employee_by_user:
            attendances = attendance_model.search([
                ('employee_id', 'in', [emp.id for emp in employee_by_user.values()]),
                ('check_in', '>=', today_start),
                ('check_in', '<', today_end),
            ], order='check_in desc')
            for att in attendances:
                attendance_by_employee[att.employee_id.id].append(att)

        rows = []
        currently_checked_in = 0
        worked_today = 0
        shift_map = defaultdict(lambda: {'total': 0, 'currently_checked_in': 0, 'worked_today': 0})

        def shift_label(check_in):
            if not check_in:
                return 'غير محدد'
            local = fields.Datetime.context_timestamp(self, check_in)
            if local.hour < 12:
                return 'صباحي'
            if local.hour < 18:
                return 'مسائي'
            return 'ليلي'

        for user in users:
            employee = employee_by_user.get(user.id)
            attendances = attendance_by_employee.get(employee.id, []) if employee else []
            open_att = next((att for att in attendances if not att.check_out), False)
            last_att = attendances[0] if attendances else False
            did_work = bool(attendances)
            is_present = bool(open_att)
            worked_today += 1 if did_work else 0
            currently_checked_in += 1 if is_present else 0
            shift = shift_label((open_att or last_att).check_in if (open_att or last_att) else False)
            shift_map[shift]['total'] += 1
            shift_map[shift]['currently_checked_in'] += 1 if is_present else 0
            shift_map[shift]['worked_today'] += 1 if did_work else 0

            role = ''
            department = ''
            work_location = ''
            phone = user.partner_id.mobile or user.partner_id.phone or ''
            if employee:
                role = getattr(employee, 'job_title', False) or (employee.job_id.name if 'job_id' in employee._fields and employee.job_id else '')
                department = employee.department_id.name if 'department_id' in employee._fields and employee.department_id else ''
                work_location = employee.work_location_name if 'work_location_name' in employee._fields else ''
                if 'mobile_phone' in employee._fields and employee.mobile_phone:
                    phone = employee.mobile_phone

            rows.append({
                'user_id': user.id,
                'employee_id': employee.id if employee else False,
                'name': user.name or '',
                'role': role or 'مستخدم تشغيلي',
                'department': department or '',
                'work_location_label': work_location or '',
                'phone': phone,
                'worked_today': did_work,
                'currently_checked_in': is_present,
                'shift_bucket': shift,
                'last_check_in': fields.Datetime.to_string(last_att.check_in) if last_att else '',
                'last_check_out': fields.Datetime.to_string(last_att.check_out) if last_att and last_att.check_out else '',
            })

        shift_rows = [
            {
                'name': key,
                'total_operational_users': vals['total'],
                'worked_today': vals['worked_today'],
                'currently_checked_in': vals['currently_checked_in'],
            }
            for key, vals in sorted(shift_map.items())
        ]

        total = len(users)
        return {
            'contract_version': '18.0-team',
            'generated_at': fields.Datetime.to_string(now),
            'company_id': company.id,
            'company_name': company.display_name,
            'hr_attendance_available': bool(attendance_model),
            'kpis': {
                'operational_users': total,
                'worked_today': worked_today,
                'currently_checked_in': currently_checked_in,
                'current_presence_pct': round((currently_checked_in / total) * 100.0, 1) if total else 0.0,
                'worked_today_pct': round((worked_today / total) * 100.0, 1) if total else 0.0,
            },
            'team': rows,
            'shifts': shift_rows,
            'semantics': {
                'operational_users': 'Active internal users belonging to MRP/POS/Stock operational groups for the current company.',
                'currently_checked_in': 'Users whose linked employee has an HR Attendance record today without check_out. This is current presence, not an attendance-performance score.',
                'worked_today': 'Users whose linked employee has at least one HR Attendance check-in today.',
                'shift_bucket': 'Heuristic grouping based on check-in clock time: before 12:00 morning, before 18:00 evening, otherwise night. It is not an HR schedule/roster assignment.',
                'work_location_label': 'Employee work-location text only. V18 does not claim this is an MRP Work Center assignment.',
            },
        }

    @api.model
    def get_team_data(self):
        self._cw_require_management_access()
        return self._cw_team_contract()
