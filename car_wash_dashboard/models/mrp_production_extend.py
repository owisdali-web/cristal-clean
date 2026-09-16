# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
import hashlib
from collections import defaultdict

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


AR_DAYS = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']

# Legacy values are intentionally kept for backward compatibility with older records.
# Dashboard V2 no longer uses these values for analytics.
WASH_TYPES = [
    ('basic', 'Basic'),
    ('premium', 'Premium'),
    ('deluxe', 'Deluxe'),
]

PIPELINE_STATES = [
    ('draft', 'مسودة'),
    ('confirmed', 'بانتظار البدء'),
    ('progress', 'قيد الغسيل'),
    ('to_close', 'جاهزة للإغلاق'),
]

ACTIVE_WO_STATES = ['pending', 'waiting', 'ready', 'progress']


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Legacy dashboard fields. Kept so upgrading the module never destroys old data.
    license_plate = fields.Char('License Plate')
    wash_type = fields.Selection(WASH_TYPES, string='Wash Type', default='basic')

    # ------------------------------------------------------------------
    # Timezone helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_day_bounds(self, offset=0):
        """Return (start_utc, end_utc, local_date) for the user's timezone."""
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        day = (datetime.now(user_tz) + timedelta(days=offset)).date()
        start_local = user_tz.localize(datetime.combine(day, time.min))
        end_local = start_local + timedelta(days=1)

        def to_utc_string(value):
            value = value.astimezone(pytz.utc).replace(tzinfo=None)
            return fields.Datetime.to_string(value)

        return to_utc_string(start_local), to_utc_string(end_local), day

    @api.model
    def _cw_today_start(self):
        return self._cw_day_bounds(0)[0]

    def _cw_local_hm(self, value):
        if not value:
            return ''
        return fields.Datetime.context_timestamp(self, value).strftime('%H:%M')

    def _cw_local_dm(self, value):
        if not value:
            return ''
        return fields.Datetime.context_timestamp(self, value).strftime('%d/%m')

    # ------------------------------------------------------------------
    # Crystal Clean helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_wash_domain(self):
        domain = [('company_id', '=', self.env.company.id)]
        # POS is the source of truth in this database.  The installed
        # ``pos_mrp_order`` module marks every sellable wash service with
        # ``to_make_mrp`` and creates the MO from that product.  Prefer this
        # standard, populated relation over optional Studio flags which may
        # exist but are not populated on older/current records.
        if 'to_make_mrp' in self.env['product.template']._fields:
            domain.append(('product_id.product_tmpl_id.to_make_mrp', '=', True))
        elif 'x_cc_is_wash_order' in self._fields:
            domain.append(('x_cc_is_wash_order', '=', True))
        else:
            domain.append(('origin', '=like', 'POS-%'))
        return domain

    @api.model
    def _cw_workorder_wash_domain(self):
        if 'to_make_mrp' in self.env['product.template']._fields:
            return [('production_id.product_id.product_tmpl_id.to_make_mrp', '=', True)]
        if 'x_cc_is_wash_order' in self._fields:
            return [('production_id.x_cc_is_wash_order', '=', True)]
        return [('production_id.origin', '=like', 'POS-%')]

    @api.model
    def _cw_service_templates(self):
        ProductTemplate = self.env['product.template']
        templates = ProductTemplate.browse()
        if 'to_make_mrp' in ProductTemplate._fields:
            templates |= ProductTemplate.search([
                ('active', '=', True),
                ('to_make_mrp', '=', True),
            ])
        if 'x_cc_recipe_bom_id' in ProductTemplate._fields:
            templates |= ProductTemplate.search([
                ('active', '=', True),
                ('x_cc_recipe_bom_id', '!=', False),
            ])
        return templates

    @api.model
    def _cw_material_products(self, service_templates):
        Product = self.env['product.product']
        if not service_templates:
            return Product.browse()
        Bom = self.env['mrp.bom']
        boms = Bom.search([
            '|',
            ('product_tmpl_id', 'in', service_templates.ids),
            ('product_id', 'in', service_templates.mapped('product_variant_ids').ids),
        ])
        # The live database also keeps curated wash recipes in a Studio field.
        # Combine both sources: POS/MRP BoMs define operational services while
        # the curated recipe relation preserves the full material catalogue.
        if 'x_cc_recipe_bom_id' in service_templates._fields:
            boms |= service_templates.mapped('x_cc_recipe_bom_id')
        return boms.mapped('bom_line_ids.product_id')

    @api.model
    def _cw_pos_order_for_mo(self, mo):
        """Resolve the real POS ticket without creating a hard data link."""
        if 'pos.order' not in self.env or not (mo.origin or '').startswith('POS-'):
            return self.env['pos.order'] if 'pos.order' in self.env else False
        return self.env['pos.order'].search([
            ('company_id', '=', mo.company_id.id),
            ('name', '=', mo.origin[4:]),
        ], limit=1)

    @api.model
    def _cw_dashboard_channel(self, company_id=None):
        company_id = company_id or self.env.company.id
        return 'crystal_clean_dashboard_%s' % company_id

    @api.model
    def _cw_vehicle_size(self, service_name='', vehicle_type=''):
        """Return large/small from real service wording first, then legacy vehicle type.

        The current POS catalogue explicitly distinguishes سيارة كبيرة / سيارة صغيرة.
        We therefore avoid a new database field and derive the UI label from the commercial
        service that actually generated the wash order.
        """
        text = (service_name or '').lower()
        large_words = ('كبيرة', 'حفار', 'بلدوز', 'بوب كات', 'شاحنة', 'pickup', 'truck', 'suv', 'van')
        small_words = ('صغيرة', 'small', 'sedan')
        if any(word in text for word in large_words):
            return 'large'
        if any(word in text for word in small_words):
            return 'small'
        if vehicle_type in ('truck', 'pickup', 'van'):
            return 'large'
        return 'small'

    @api.model
    def _cw_operation_kind(self, name):
        text = (name or '').lower()
        rules = [
            (('آلي', 'الي', 'auto'), 'auto'),
            (('لمعة', 'تلميع', 'polish', 'باستا'), 'polish'),
            (('داخلي', 'صالون', 'صالة', 'فرشة', 'سقف'), 'interior'),
            (('عميق', 'deep'), 'deep'),
            (('فودرة', 'powder'), 'powder'),
            (('محرك', 'engine'), 'engine'),
            (('سفلي', 'under'), 'underbody'),
            (('فحص', 'qc', 'quality'), 'qc'),
            (('خارجي', 'غسيل', 'wash'), 'external'),
        ]
        for tokens, kind in rules:
            if any(token in text for token in tokens):
                return kind
        return 'service'

    @api.model
    def _cw_pos_extra_payload(self, service_products, today_start, today_end):
        """POS page payload; read only and scoped to the current company."""
        defaults = {
            'orders': [], 'top_services': [], 'hourly': [], 'orders_today': 0,
            'revenue_today': 0.0, 'avg_ticket': 0.0, 'customers_today': 0,
            'month_revenue': 0.0, 'month_orders': 0,
        }
        if 'pos.order' not in self.env or 'pos.order.line' not in self.env:
            return defaults

        company = self.env.company
        PosOrder = self.env['pos.order']
        PosLine = self.env['pos.order.line']
        line_domain = [
            ('order_id.company_id', '=', company.id),
            ('order_id.date_order', '>=', today_start),
            ('order_id.date_order', '<', today_end),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('product_id', 'in', service_products.ids),
        ]
        lines = PosLine.search(line_domain)
        orders = lines.mapped('order_id').sorted(key=lambda o: o.date_order or o.create_date, reverse=True)

        totals = defaultdict(lambda: {'qty': 0.0, 'amount': 0.0, 'orders': set()})
        for line in lines:
            bucket = totals[line.product_id.display_name]
            bucket['qty'] += line.qty
            bucket['amount'] += line.price_subtotal_incl
            bucket['orders'].add(line.order_id.id)
        top_services = [
            {'name': name, 'qty': round(vals['qty'], 2), 'amount': round(vals['amount'], 2), 'orders': len(vals['orders'])}
            for name, vals in totals.items()
        ]
        top_services.sort(key=lambda x: (x['amount'], x['qty']), reverse=True)

        origins = ['POS-%s' % (order.name or '') for order in orders[:30]]
        mo_map = {}
        if origins:
            mos = self.search(self._cw_wash_domain() + [('origin', 'in', origins)])
            mo_map = {mo.origin: mo for mo in mos}

        rows = []
        for order in orders[:20]:
            wash_lines = order.lines.filtered(lambda l: l.product_id.id in service_products.ids)
            mo = mo_map.get('POS-%s' % (order.name or ''))
            car = self._cw_mo_vehicle_payload(mo) if mo else {}
            rows.append({
                'id': order.id,
                'name': order.name or '',
                'time': self._cw_local_hm(order.date_order),
                'customer': order.partner_id.display_name if order.partner_id else 'عميل نقدي',
                'amount': round(sum(wash_lines.mapped('price_subtotal_incl')), 2),
                'services': [l.product_id.display_name for l in wash_lines],
                'plate': car.get('public_reference') or car.get('plate') or '—',
                'wash_order_id': mo.id if mo else False,
                'wash_status': car.get('status_label') or 'بانتظار أمر الغسيل',
            })

        hour_buckets = {hour: 0.0 for hour in range(8, 23, 2)}
        for line in lines:
            if not line.order_id.date_order:
                continue
            local_dt = fields.Datetime.context_timestamp(self, line.order_id.date_order)
            hour = min(22, max(8, (local_dt.hour // 2) * 2))
            if hour in hour_buckets:
                hour_buckets[hour] += line.price_subtotal_incl
        hourly = [{'label': '%02d:00' % h, 'amount': round(v, 2)} for h, v in hour_buckets.items()]

        local_today = self._cw_day_bounds(0)[2]
        month_start_local = local_today.replace(day=1)
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        month_start_dt = user_tz.localize(datetime.combine(month_start_local, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        month_start = fields.Datetime.to_string(month_start_dt)
        month_lines = PosLine.search([
            ('order_id.company_id', '=', company.id),
            ('order_id.date_order', '>=', month_start),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('product_id', 'in', service_products.ids),
        ])
        month_orders = month_lines.mapped('order_id')
        revenue_today = round(sum(lines.mapped('price_subtotal_incl')), 2)
        order_count = len(orders)
        customer_count = len(orders.filtered(lambda o: o.partner_id).mapped('partner_id'))
        return {
            'orders': rows,
            'top_services': top_services[:8],
            'hourly': hourly,
            'orders_today': order_count,
            'revenue_today': revenue_today,
            'avg_ticket': round(revenue_today / order_count, 2) if order_count else 0.0,
            'customers_today': customer_count,
            'month_revenue': round(sum(month_lines.mapped('price_subtotal_incl')), 2),
            'month_orders': len(month_orders),
        }

    @api.model
    def _cw_finance_extra_payload(self, today, today_start, today_end, pos_extra):
        defaults = {
            'customer_invoices_today': 0.0, 'vendor_bills_today': 0.0,
            'receivable_open': 0.0, 'payable_open': 0.0, 'recent_moves': [],
            'expense_breakdown': [], 'week_pos_sales': [],
            'collected_today': 0.0, 'expense_today': 0.0, 'net_today': 0.0,
            'month_expense': 0.0,
        }
        if 'account.move' not in self.env:
            return defaults

        company = self.env.company
        Move = self.env['account.move']
        today_s = fields.Date.to_string(today)
        out_moves = Move.search([
            ('company_id', '=', company.id), ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']), ('invoice_date', '=', today_s),
        ])
        in_moves = Move.search([
            ('company_id', '=', company.id), ('state', '=', 'posted'),
            ('move_type', 'in', ['in_invoice', 'in_refund']), ('invoice_date', '=', today_s),
        ])
        rec_open = Move.search([
            ('company_id', '=', company.id), ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'), ('payment_state', 'not in', ['paid', 'reversed']),
        ])
        pay_open = Move.search([
            ('company_id', '=', company.id), ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'), ('payment_state', 'not in', ['paid', 'reversed']),
        ])

        recent = Move.search([
            ('company_id', '=', company.id), ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'entry']),
        ], order='date desc, id desc', limit=12)
        labels = {
            'out_invoice': 'فاتورة عميل', 'out_refund': 'إشعار دائن',
            'in_invoice': 'فاتورة مورد', 'in_refund': 'مرتجع مورد', 'entry': 'قيد يومية',
        }
        recent_rows = [{
            'id': m.id, 'name': m.name or m.ref or '/', 'date': fields.Date.to_string(m.date),
            'type': labels.get(m.move_type, 'قيد'), 'partner': m.partner_id.display_name if m.partner_id else '',
            'amount': round(m.amount_total_signed if m.move_type != 'entry' else abs(m.amount_total_signed), 2),
            'payment_state': m.payment_state or '',
        } for m in recent]

        expense_breakdown = []
        if 'account.move.line' in self.env:
            Line = self.env['account.move.line']
            month_start = today.replace(day=1)
            exp_lines = Line.search([
                ('company_id', '=', company.id), ('move_id.state', '=', 'posted'),
                ('date', '>=', fields.Date.to_string(month_start)),
                ('account_id.account_type', 'in', ['expense', 'expense_direct_cost']),
            ])
            exp_map = defaultdict(float)
            for line in exp_lines:
                exp_map[line.account_id.display_name] += (line.debit - line.credit)
            expense_breakdown = [
                {'name': name, 'amount': round(amount, 2)}
                for name, amount in exp_map.items() if amount > 0
            ]
            expense_breakdown.sort(key=lambda x: x['amount'], reverse=True)
            expense_breakdown = expense_breakdown[:6]

        # POS seven-day sales trend: operational sales, kept distinct from accounting revenue.
        week_pos_sales = []
        if 'pos.order.line' in self.env:
            PosLine = self.env['pos.order.line']
            service_products = self._cw_service_templates().mapped('product_variant_ids')
            for offset in range(6, -1, -1):
                start, end, day = self._cw_day_bounds(-offset)
                day_lines = PosLine.search([
                    ('order_id.company_id', '=', company.id),
                    ('order_id.date_order', '>=', start), ('order_id.date_order', '<', end),
                    ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                    ('product_id', 'in', service_products.ids),
                ])
                week_pos_sales.append({
                    'label': AR_DAYS[day.weekday()],
                    'amount': round(sum(day_lines.mapped('price_subtotal_incl')), 2),
                })

        collected_today = 0.0
        if 'account.payment' in self.env:
            Payment = self.env['account.payment']
            payment_domain = [
                ('company_id', '=', company.id),
                ('date', '=', today_s),
                ('payment_type', '=', 'inbound'),
                ('partner_type', '=', 'customer'),
            ]
            if 'state' in Payment._fields:
                payment_domain.append(('state', 'not in', ['draft', 'cancel', 'canceled', 'rejected']))
            collected_today = round(sum(Payment.search(payment_domain).mapped('amount')), 2)

        expense_today = 0.0
        month_expense = 0.0
        if 'account.move.line' in self.env:
            Line = self.env['account.move.line']
            month_start_s = fields.Date.to_string(today.replace(day=1))
            expense_base = [
                ('company_id', '=', company.id),
                ('move_id.state', '=', 'posted'),
                ('account_id.account_type', 'in', ['expense', 'expense_direct_cost']),
            ]
            today_exp_lines = Line.search(expense_base + [('date', '=', today_s)])
            month_exp_lines = Line.search(expense_base + [('date', '>=', month_start_s)])
            expense_today = round(sum((line.debit - line.credit) for line in today_exp_lines), 2)
            month_expense = round(sum((line.debit - line.credit) for line in month_exp_lines), 2)

        return {
            'customer_invoices_today': round(sum(m.amount_total if m.move_type == 'out_invoice' else -m.amount_total for m in out_moves), 2),
            'vendor_bills_today': round(sum(m.amount_total if m.move_type == 'in_invoice' else -m.amount_total for m in in_moves), 2),
            'receivable_open': round(sum(rec_open.mapped('amount_residual')), 2),
            'payable_open': round(sum(pay_open.mapped('amount_residual')), 2),
            'recent_moves': recent_rows,
            'expense_breakdown': expense_breakdown,
            'week_pos_sales': week_pos_sales,
            'pos_revenue_today': pos_extra.get('revenue_today', 0.0),
            'pos_month_revenue': pos_extra.get('month_revenue', 0.0),
            'collected_today': collected_today,
            'expense_today': expense_today,
            'net_today': round(pos_extra.get('revenue_today', 0.0) - expense_today, 2),
            'month_expense': month_expense,
        }

    @api.model
    def _cw_customer_page_payload(self, service_products, today_start, today_end):
        """Customer analytics derived from real paid POS wash-service orders."""
        defaults = {
            'rows': [], 'total': 0, 'repeat': 0, 'new_today': 0, 'inactive_30': 0,
        }
        if 'pos.order.line' not in self.env or not service_products:
            return defaults

        company = self.env.company
        PosLine = self.env['pos.order.line']
        year_start = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=365))
        lines = PosLine.search([
            ('order_id.company_id', '=', company.id),
            ('order_id.date_order', '>=', year_start),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('product_id', 'in', service_products.ids),
            ('order_id.partner_id', '!=', False),
        ], order='order_id.date_order desc', limit=12000)

        buckets = {}
        today_partner_ids = set()
        for line in lines:
            order = line.order_id
            partner = order.partner_id
            if not partner:
                continue
            bucket = buckets.setdefault(partner.id, {
                'partner': partner, 'orders': set(), 'spend': 0.0,
                'last_visit': False, 'services': defaultdict(float),
            })
            bucket['orders'].add(order.id)
            bucket['spend'] += line.price_subtotal_incl
            bucket['services'][line.product_id.display_name] += line.qty
            if order.date_order and (not bucket['last_visit'] or order.date_order > bucket['last_visit']):
                bucket['last_visit'] = order.date_order
            if order.date_order and today_start <= fields.Datetime.to_string(order.date_order) < today_end:
                today_partner_ids.add(partner.id)

        cutoff = fields.Datetime.now() - timedelta(days=30)
        rows = []
        repeat = 0
        inactive = 0
        for partner_id, vals in buckets.items():
            partner = vals['partner']
            visits = len(vals['orders'])
            if visits > 1:
                repeat += 1
            last_visit = vals['last_visit']
            if last_visit and last_visit < cutoff:
                inactive += 1
            favorite = ''
            if vals['services']:
                favorite = max(vals['services'].items(), key=lambda item: item[1])[0]
            rows.append({
                'id': partner_id,
                'name': partner.display_name or '',
                'phone': partner.mobile or partner.phone or '',
                'visits': visits,
                'last_visit': fields.Datetime.context_timestamp(self, last_visit).strftime('%Y-%m-%d') if last_visit else '',
                'total_spend': round(vals['spend'], 2),
                'favorite_service': favorite,
            })
        rows.sort(key=lambda r: (r['visits'], r['total_spend']), reverse=True)
        return {
            'rows': rows[:80],
            'total': len(rows),
            'repeat': repeat,
            'new_today': len(today_partner_ids),
            'inactive_30': inactive,
        }

    @api.model
    def _cw_client_hr_payload(self, service_products, today_start, today_end):
        """Combined customer + internal users payload for the people page."""
        customer_page = self._cw_customer_page_payload(service_products, today_start, today_end)
        defaults = {
            'customer_rows': customer_page.get('rows', []),
            'top_customers': customer_page.get('rows', [])[:5],
            'total_customers': customer_page.get('total', 0),
            'repeat_customers': customer_page.get('repeat', 0),
            'new_customers_month': 0,
            'inactive_30': customer_page.get('inactive_30', 0),
            'user_rows': [],
            'total_users': 0,
            'present_today': 0,
            'attendance_rate': 0.0,
            'shift_rows': [],
            'shift_count': 0,
            'station_workers': 0,
        }

        company = self.env.company
        user_domain = [('share', '=', False), ('active', '=', True)]
        if 'company_ids' in self.env['res.users']._fields:
            user_domain.append(('company_ids', 'in', company.ids))

        relevant_group_ids = []
        for xmlid in [
            'mrp.group_mrp_user', 'mrp.group_mrp_manager',
            'mrp_workorder.group_mrp_routing',
            'point_of_sale.group_pos_user', 'point_of_sale.group_pos_manager',
            'stock.group_stock_user', 'stock.group_stock_manager',
        ]:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if rec:
                relevant_group_ids.append(rec.id)
        if relevant_group_ids and 'groups_id' in self.env['res.users']._fields:
            user_domain.append(('groups_id', 'in', relevant_group_ids))

        users = self.env['res.users'].search(user_domain, order='name', limit=40)
        employee_model = self.env['hr.employee'] if 'hr.employee' in self.env.registry.models else False
        attendance_model = self.env['hr.attendance'] if 'hr.attendance' in self.env.registry.models else False
        workcenter_model = self.env['mrp.workcenter'] if 'mrp.workcenter' in self.env.registry.models else False
        users_count = len(users)
        present_today = 0
        shift_map = defaultdict(lambda: {'name': '', 'present': 0, 'total': 0})
        user_rows = []
        station_workers = 0

        def shift_label(hour):
            if hour < 12:
                return 'صباحي'
            if hour < 18:
                return 'مسائي'
            return 'ليلي'

        today_date = fields.Date.context_today(self)
        month_start = today_date.replace(day=1)
        new_customer_ids = set()
        try:
            if 'pos.order.line' in self.env and service_products:
                lines = self.env['pos.order.line'].search([
                    ('order_id.company_id', '=', company.id),
                    ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                    ('product_id', 'in', service_products.ids),
                    ('order_id.partner_id', '!=', False),
                    ('order_id.date_order', '>=', fields.Datetime.to_string(datetime.combine(month_start, time.min))),
                ], limit=4000)
                for line in lines:
                    if line.order_id.partner_id:
                        new_customer_ids.add(line.order_id.partner_id.id)
        except Exception:
            pass

        attendance_cache = {}
        if attendance_model:
            for user in users:
                employee = getattr(user, 'employee_id', False)
                if not employee and employee_model and 'user_id' in employee_model._fields:
                    employee = employee_model.search([('user_id', '=', user.id)], limit=1)
                if employee:
                    attendance_cache[user.id] = attendance_model.search([
                        ('employee_id', '=', employee.id),
                        ('check_in', '>=', today_start),
                        ('check_in', '<', today_end),
                    ], order='check_in desc', limit=5)

        workcenter_names = set()
        if workcenter_model:
            try:
                workcenter_names = {w.name for w in workcenter_model.search([])}
            except Exception:
                workcenter_names = set()

        for user in users:
            employee = getattr(user, 'employee_id', False)
            if not employee and employee_model and 'user_id' in employee_model._fields:
                employee = employee_model.search([('user_id', '=', user.id)], limit=1)

            checkins = attendance_cache.get(user.id, attendance_model.browse() if attendance_model else [])
            open_att = checkins.filtered(lambda a: not a.check_out)[:1] if attendance_model else []
            last_att = checkins[:1] if attendance_model else []

            if open_att:
                status = 'present'
                status_label = 'متصل'
                present_today += 1
                checkin_dt = fields.Datetime.context_timestamp(self, open_att[0].check_in)
                shift = shift_label(checkin_dt.hour)
            elif checkins:
                status = 'done'
                status_label = 'أنهى الوردية'
                checkin_dt = fields.Datetime.context_timestamp(self, last_att[0].check_in)
                shift = shift_label(checkin_dt.hour)
            else:
                status = 'absent'
                status_label = 'غائب'
                shift = 'غير محدد'
                checkin_dt = False

            role = ''
            department = ''
            station = ''
            if employee:
                role = getattr(employee, 'job_title', False) or (employee.job_id.name if 'job_id' in employee._fields and employee.job_id else '')
                department = employee.department_id.name if 'department_id' in employee._fields and employee.department_id else ''
                if 'work_location_name' in employee._fields:
                    station = employee.work_location_name or ''
            if not role:
                role = 'مستخدم تشغيلي'
            if not department:
                department = 'التشغيل'
            if not station:
                station = department
            station_workers += 1

            shift_map[shift]['name'] = shift
            shift_map[shift]['total'] += 1
            if status == 'present':
                shift_map[shift]['present'] += 1

            user_rows.append({
                'id': user.id,
                'name': user.name or '',
                'role': role,
                'department': department,
                'station': station,
                'shift': shift,
                'status': status,
                'status_label': status_label,
                'phone': getattr(employee, 'mobile_phone', False) if employee and 'mobile_phone' in employee._fields else (user.partner_id.mobile or user.partner_id.phone or ''),
                'last_seen': fields.Datetime.context_timestamp(self, user.login_date).strftime('%Y-%m-%d %H:%M') if user.login_date else '',
            })

        shift_rows = []
        for key in ['صباحي', 'مسائي', 'ليلي', 'غير محدد']:
            if key in shift_map:
                row = shift_map[key]
                total = row['total'] or 0
                pct = round((row['present'] / total) * 100, 1) if total else 0.0
                shift_rows.append({'name': row['name'], 'present': row['present'], 'total': total, 'pct': pct})

        defaults.update({
            'new_customers_month': len(new_customer_ids),
            'user_rows': user_rows,
            'total_users': users_count,
            'present_today': present_today,
            'attendance_rate': round((present_today / users_count) * 100, 1) if users_count else 0.0,
            'shift_rows': shift_rows,
            'shift_count': len(shift_rows),
            'station_workers': station_workers,
        })
        return defaults

    @api.model
    def _cw_apply_material_burn_rate(self, materials):
        """Add real 30-day raw-material consumption and days remaining to material cards."""
        if not materials or 'stock.move' not in self.env:
            return materials
        product_ids = [m['product_id'] for m in materials]
        Move = self.env['stock.move']
        if 'raw_material_production_id' not in Move._fields:
            return materials

        start = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=30))
        domain = [
            ('product_id', 'in', product_ids),
            ('state', '=', 'done'),
            ('date', '>=', start),
            ('raw_material_production_id', '!=', False),
            ('raw_material_production_id.company_id', '=', self.env.company.id),
        ]
        if 'to_make_mrp' in self.env['product.template']._fields:
            domain.append(('raw_material_production_id.product_id.product_tmpl_id.to_make_mrp', '=', True))
        elif 'x_cc_is_wash_order' in self._fields:
            domain.append(('raw_material_production_id.x_cc_is_wash_order', '=', True))
        else:
            domain.append(('raw_material_production_id.origin', '=like', 'POS-%'))

        moves = Move.search(domain)
        qty_field = 'quantity' if 'quantity' in Move._fields else 'product_uom_qty'
        consumed = defaultdict(float)
        for move in moves:
            consumed[move.product_id.id] += abs(getattr(move, qty_field, 0.0) or 0.0)

        for item in materials:
            total_30 = consumed.get(item['product_id'], 0.0)
            daily = total_30 / 30.0
            free = max(0.0, item.get('free', 0.0))
            days = round(free / daily, 1) if daily > 0 else False
            item['consumed_30d'] = round(total_30, 2)
            item['daily_consumption'] = round(daily, 2)
            item['days_remaining'] = days
            if item.get('is_low') or (days is not False and days < 3):
                item['burn_status'] = 'danger'
            elif days is not False and days < 7:
                item['burn_status'] = 'warning'
            else:
                item['burn_status'] = 'good'
        return materials

    @api.model
    def _cw_maintenance_page_payload(self, today):
        defaults = {
            'available': False, 'rows': [], 'equipment_count': 0,
            'due_soon': 0, 'open_faults': 0, 'health_avg': 0,
        }
        if 'maintenance.equipment' not in self.env.registry.models:
            return defaults

        Equipment = self.env['maintenance.equipment']
        eq_domain = []
        if 'company_id' in Equipment._fields:
            eq_domain = ['|', ('company_id', '=', False), ('company_id', '=', self.env.company.id)]
        equipments = Equipment.search(eq_domain, order='name,id')

        Request = self.env['maintenance.request'] if 'maintenance.request' in self.env.registry.models else False
        Stage = self.env['maintenance.stage'] if 'maintenance.stage' in self.env.registry.models else False
        rows = []
        health_values = []
        due_soon = 0
        open_faults = 0

        for eq in equipments[:30]:
            requests = Request.browse() if Request else False
            open_requests = Request.browse() if Request else False
            if Request:
                requests = Request.search([('equipment_id', '=', eq.id)], order='request_date desc, id desc', limit=30)
                open_requests = requests
                if Stage and 'stage_id' in Request._fields:
                    if 'done' in Stage._fields:
                        open_requests = requests.filtered(lambda r: not r.stage_id.done)
                    elif 'fold' in Stage._fields:
                        open_requests = requests.filtered(lambda r: not r.stage_id.fold)

            corrective = open_requests.filtered(lambda r: getattr(r, 'maintenance_type', '') == 'corrective') if open_requests else open_requests
            preventive = open_requests.filtered(lambda r: getattr(r, 'maintenance_type', '') == 'preventive') if open_requests else open_requests
            if corrective:
                open_faults += 1

            schedule_dates = []
            if open_requests and 'schedule_date' in Request._fields:
                schedule_dates = [r.schedule_date for r in open_requests if r.schedule_date]
            next_date = min(schedule_dates) if schedule_dates else False
            days_to_next = (next_date - today).days if next_date else False
            if days_to_next is not False and days_to_next <= 14:
                due_soon += 1

            if corrective:
                health = 55
                status = 'fault'
                status_label = 'يحتاج متابعة'
            elif days_to_next is not False and days_to_next <= 7:
                health = 75
                status = 'warning'
                status_label = 'صيانة قريبة'
            elif preventive:
                health = 88
                status = 'warning'
                status_label = 'مجدولة'
            else:
                health = 95
                status = 'good'
                status_label = 'جيد'
            health_values.append(health)

            last_done = False
            if requests:
                closed = requests.filtered(lambda r: bool(getattr(r, 'close_date', False))) if 'close_date' in Request._fields else Request.browse()
                if closed:
                    last_done = max(closed.mapped('close_date'))

            rows.append({
                'id': eq.id,
                'name': eq.display_name or eq.name or 'معدة',
                'category': eq.category_id.display_name if 'category_id' in eq._fields and eq.category_id else '',
                'health': health,
                'status': status,
                'status_label': status_label,
                'last_maintenance': fields.Date.to_string(last_done) if last_done else '',
                'next_maintenance': fields.Date.to_string(next_date) if next_date else '',
                'open_requests': len(open_requests) if open_requests else 0,
            })

        return {
            'available': True,
            'rows': rows,
            'equipment_count': len(equipments),
            'due_soon': due_soon,
            'open_faults': open_faults,
            'health_avg': round(sum(health_values) / len(health_values)) if health_values else 100,
        }

    @api.model
    def _cw_mo_vehicle_payload(self, mo):
        sale = mo.sale_line_id.order_id if mo.sale_line_id else self.env['sale.order']
        pos_order = self._cw_pos_order_for_mo(mo)
        service = False
        if 'x_cc_service_product_id' in mo._fields:
            service = mo.x_cc_service_product_id
        if not service and mo.sale_line_id:
            service = mo.sale_line_id.product_id
        if not service:
            service = mo.product_id

        def mo_value(field_name):
            return getattr(mo, field_name, False) if field_name in mo._fields else False

        def sale_value(field_name):
            return getattr(sale, field_name, False) if sale and field_name in sale._fields else False

        plate = mo_value('x_cc_vehicle_plate') or sale_value('x_cc_vehicle_plate') or mo.license_plate or ''
        model = mo_value('x_cc_vehicle_model') or sale_value('x_cc_vehicle_model') or ''
        color = mo_value('x_cc_vehicle_color') or sale_value('x_cc_vehicle_color') or ''
        notes = mo_value('x_cc_vehicle_notes') or sale_value('x_cc_vehicle_notes') or ''
        vehicle_type = sale_value('vehicle_type') or 'car'
        service_name = service.display_name if service else ''
        vehicle_size = self._cw_vehicle_size(service_name, vehicle_type)

        workorders = mo.workorder_ids.filtered(lambda w: w.state != 'cancel')
        workorders = workorders.sorted(key=lambda w: (getattr(w.operation_id, 'sequence', 0), w.id))
        total_steps = len(workorders)
        done_steps = len(workorders.filtered(lambda w: w.state == 'done'))
        progress = round((done_steps / total_steps) * 100) if total_steps else (100 if mo.state == 'done' else 0)

        current_wo = (
            workorders.filtered(lambda w: w.state == 'progress')[:1]
            or workorders.filtered(lambda w: w.state == 'ready')[:1]
            or workorders.filtered(lambda w: w.state == 'waiting')[:1]
            or workorders.filtered(lambda w: w.state == 'pending')[:1]
        )

        if mo.state == 'done':
            status_code, status_label = 'done', 'مكتملة'
        elif mo.state == 'to_close':
            status_code, status_label = 'ready_delivery', 'جاهزة للإغلاق'
        elif current_wo and current_wo.state == 'progress':
            status_code, status_label = 'washing', 'قيد الغسيل'
        elif current_wo and current_wo.state == 'ready':
            status_code, status_label = 'ready', 'جاهزة للمحطة'
        else:
            status_code, status_label = 'waiting', 'في الانتظار'

        order_reference = (
            mo_value('x_cc_sale_order_ref')
            or mo.origin
            or (sale.name if sale else '')
            or (pos_order.name if pos_order else '')
            or mo.name
            or ''
        )
        customer = (
            sale.partner_id.display_name if sale and sale.partner_id
            else pos_order.partner_id.display_name if pos_order and pos_order.partner_id
            else ''
        )
        public_reference = plate or (
            (pos_order.name or '').rsplit('/', 1)[-1] if pos_order else ''
        ) or mo.name or ''

        operations = []
        for wo in workorders:
            operations.append({
                'id': wo.id,
                'name': wo.name or (wo.operation_id.name if wo.operation_id else 'مرحلة غسيل'),
                'state': wo.state,
                'kind': self._cw_operation_kind(wo.name or (wo.operation_id.name if wo.operation_id else '')),
                'workcenter': wo.workcenter_id.name if wo.workcenter_id else '',
            })
        expected_minutes = round(sum(workorders.mapped('duration_expected'))) if 'duration_expected' in workorders._fields else 0
        remaining_minutes = round(sum(workorders.filtered(lambda w: w.state != 'done').mapped('duration_expected'))) if 'duration_expected' in workorders._fields else 0
        current_operation_kind = self._cw_operation_kind(current_wo.name if current_wo else service_name)

        start_anchor = mo.date_start or mo.create_date
        elapsed_minutes = 0
        if start_anchor:
            elapsed_minutes = max(0, round((fields.Datetime.now() - start_anchor).total_seconds() / 60.0))

        operator_names = []
        if current_wo:
            for fname in ('employee_assigned_ids', 'employee_ids'):
                if fname in current_wo._fields:
                    operator_names = [name for name in current_wo[fname].mapped('name') if name]
                    if operator_names:
                        break
            if not operator_names and 'user_id' in current_wo._fields and current_wo.user_id:
                operator_names = [current_wo.user_id.name]

        return {
            'id': mo.id,
            'name': mo.name or '',
            'sale_order': order_reference,
            'customer': customer,
            'customer_id': (sale.partner_id.id if sale and sale.partner_id else pos_order.partner_id.id if pos_order and pos_order.partner_id else False),
            'customer_phone': (sale.partner_id.mobile or sale.partner_id.phone if sale and sale.partner_id else pos_order.partner_id.mobile or pos_order.partner_id.phone if pos_order and pos_order.partner_id else '') or '',
            'pos_amount': round(pos_order.amount_total, 2) if pos_order else 0.0,
            'payment_state': pos_order.state if pos_order else '',
            'plate': plate or 'بدون لوحة',
            'public_reference': public_reference,
            'vehicle_model': model or '',
            'vehicle_color': color or '',
            'vehicle_notes': notes or '',
            'vehicle_type': vehicle_type,
            'vehicle_size': vehicle_size,
            'service_id': service.id if service else False,
            'service_name': service.display_name if service else 'خدمة غير محددة',
            'state': mo.state,
            'status_code': status_code,
            'status_label': status_label,
            'progress': progress,
            'done_steps': done_steps,
            'total_steps': total_steps,
            'current_workorder_id': current_wo.id if current_wo else False,
            'current_stage': current_wo.name if current_wo else ('مكتملة' if mo.state == 'done' else 'بانتظار المرحلة'),
            'workcenter_id': current_wo.workcenter_id.id if current_wo and current_wo.workcenter_id else False,
            'workcenter_name': current_wo.workcenter_id.name if current_wo and current_wo.workcenter_id else '',
            'started_at': self._cw_local_hm(mo.date_start),
            'scheduled_date': self._cw_local_dm(mo.date_start),
            'elapsed_minutes': elapsed_minutes,
            'expected_minutes': expected_minutes,
            'remaining_minutes': remaining_minutes,
            'operations': operations,
            'current_operation_kind': current_operation_kind,
            'operator_names': operator_names,
            'operator_label': '، '.join(operator_names),
        }

    # ------------------------------------------------------------------
    # Station topology foundation (V14)
    # ------------------------------------------------------------------
    @api.model
    def _cw_station_workcenters(self):
        """Return the explicit car-wash station topology for the current company.

        A code-based fallback is intentionally read-only and exists only as a deployment
        safety net if an upgrade hook has not backfilled the new topology fields yet.
        """
        Workcenter = self.env['mrp.workcenter']
        company = self.env.company
        base_domain = [('active', '=', True)]
        if 'company_id' in Workcenter._fields:
            base_domain += ['|', ('company_id', '=', False), ('company_id', '=', company.id)]

        explicit = Workcenter.search(
            base_domain + [('cc_is_car_wash_station', '=', True)],
            order='cc_station_order,sequence,id',
        )
        if explicit:
            return explicit

        # Transitional safety only. Once the V14 bootstrap ran, explicit records win.
        return Workcenter.search(
            base_domain + [('code', '=like', 'CC-WC-A%')],
            order='sequence,id',
        )

    @api.model
    def _cw_station_kind_payload(self, workcenter):
        if workcenter.cc_is_car_wash_station and workcenter.cc_station_kind:
            kind = workcenter.cc_station_kind
        else:
            inferred = workcenter._cw_topology_values_from_identifiers(workcenter.code, workcenter.name)
            kind = inferred.get('cc_station_kind', 'general')
        labels = {
            'general': 'محطة مرنة',
            'auto': 'غسيل آلي',
            'polish': 'لمعة وتلميع',
        }
        return kind, labels.get(kind, 'محطة مرنة')

    @api.model
    def _cw_station_runtime_state(self, workcenter, occupancy, queue_count, capacity):
        manual_state = workcenter.cc_station_manual_state or 'open'
        if manual_state == 'maintenance':
            return 'maintenance', 'صيانة'
        if manual_state == 'closed':
            return 'closed', 'مغلقة'
        if occupancy > capacity:
            return 'overloaded', 'تجاوز السعة'
        if occupancy:
            return 'busy', 'مشغولة'
        if queue_count:
            return 'queued', 'بانتظار البدء'
        return 'available', 'متاحة'

    @api.model
    def _cw_build_station_payload(self, workorders, finished_workorders, wo_domain, vehicle_cache=None):
        Workorder = self.env['mrp.workorder']
        workcenters = self._cw_station_workcenters()

        wc_map = defaultdict(list)
        for wo in workorders:
            if wo.workcenter_id:
                wc_map[wo.workcenter_id.id].append(wo)

        rows = []
        for wc in workcenters:
            wc_wos = Workorder.browse([w.id for w in wc_map.get(wc.id, [])])
            in_progress_wos = wc_wos.filtered(lambda w: w.state == 'progress')
            queue_wos = wc_wos.filtered(lambda w: w.state in ('pending', 'waiting', 'ready'))

            capacity = int(wc.default_capacity or 1)
            if capacity <= 0:
                capacity = 1
            occupancy = len(in_progress_wos)
            queue_count = len(queue_wos)
            over_capacity = occupancy > capacity

            current_cars = []
            ordered_wos = in_progress_wos + queue_wos
            seen_mos = set()
            for wo in ordered_wos:
                if wo.production_id.id in seen_mos:
                    continue
                seen_mos.add(wo.production_id.id)
                cached_car = (vehicle_cache or {}).get(wo.production_id.id)
                car = dict(cached_car or self._cw_mo_vehicle_payload(wo.production_id))
                car['wo_state'] = wo.state
                car['stage'] = wo.name or ''
                current_cars.append(car)
                if len(current_cars) >= max(3, capacity):
                    break

            kind, kind_label = self._cw_station_kind_payload(wc)
            icon = {
                'auto': 'fa-car',
                'polish': 'fa-diamond',
                'general': 'fa-wrench',
            }.get(kind, 'fa-wrench')

            wc_done = (
                finished_workorders.filtered(lambda w: w.workcenter_id.id == wc.id)
                if finished_workorders else Workorder.browse()
            )
            wc_real = sum(wc_done.mapped('duration')) if wc_done and 'duration' in Workorder._fields else 0.0
            wc_expected = sum(wc_done.mapped('duration_expected')) if wc_done and 'duration_expected' in Workorder._fields else 0.0
            wc_efficiency = round((wc_expected / wc_real) * 100) if wc_real > 0 else 0

            runtime_state, runtime_label = self._cw_station_runtime_state(
                wc, occupancy, queue_count, capacity,
            )
            inferred = wc._cw_topology_values_from_identifiers(wc.code, wc.name)
            station_code = wc.cc_station_code or inferred.get('cc_station_code') or wc.code or wc.name
            display_order = wc.cc_station_order or inferred.get('cc_station_order') or wc.sequence or wc.id
            occupancy_rate = round((occupancy / capacity) * 100, 1)

            rows.append({
                'id': wc.id,
                'name': wc.name or station_code or 'محطة غسيل',
                'native_code': wc.code or '',
                'station_code': station_code,
                'display_order': display_order,
                'kind': kind,
                'kind_label': kind_label,
                'manual_state': wc.cc_station_manual_state or 'open',
                'runtime_state': runtime_state,
                'runtime_label': runtime_label,
                'topology_explicit': bool(wc.cc_is_car_wash_station),
                'load': len(wc_wos),
                'occupancy': occupancy,
                'in_progress': occupancy,  # legacy key retained for the current dashboard asset
                'queue': queue_count,       # legacy key retained for the current dashboard asset
                'queue_count': queue_count,
                'capacity': capacity,
                'available_capacity': max(capacity - occupancy, 0),
                'over_capacity': over_capacity,
                'occupancy_rate': occupancy_rate,
                'utilization': min(100.0, occupancy_rate),
                'queue_pressure': round((len(wc_wos) / capacity) * 100, 1),
                'efficiency': wc_efficiency,
                'done_today': len(wc_done),
                'icon': icon,
                'cars': current_cars,
                'native_working_state': wc.working_state if 'working_state' in wc._fields else '',
                'domain': wo_domain + [('workcenter_id', '=', wc.id)],
            })

        return sorted(rows, key=lambda row: (row['display_order'], row['id']))

    @api.model
    def get_station_topology(self):
        """Lightweight station-only contract for the next dashboard architecture."""
        today_start, today_end, _today = self._cw_day_bounds(0)
        company = self.env.company
        Workorder = self.env['mrp.workorder']

        wo_domain = [
            ('production_id.company_id', '=', company.id),
            ('production_id.state', 'not in', ['done', 'cancel']),
            ('state', 'in', ACTIVE_WO_STATES),
        ] + self._cw_workorder_wash_domain()
        workorders = Workorder.search(wo_domain)

        finished = Workorder.browse()
        if {'duration', 'duration_expected', 'date_finished'} <= set(Workorder._fields):
            finished = Workorder.search([
                ('production_id.company_id', '=', company.id),
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
                ('date_finished', '<', today_end),
            ] + self._cw_workorder_wash_domain())

        stations = self._cw_build_station_payload(workorders, finished, wo_domain)
        return {
            'company_id': company.id,
            'company_name': company.display_name,
            'station_total': len(stations),
            'station_available': sum(1 for row in stations if row['runtime_state'] == 'available'),
            'station_busy': sum(1 for row in stations if row['runtime_state'] in ('busy', 'overloaded')),
            'station_maintenance': sum(1 for row in stations if row['runtime_state'] == 'maintenance'),
            'station_closed': sum(1 for row in stations if row['runtime_state'] == 'closed'),
            'station_overloaded': sum(1 for row in stations if row['runtime_state'] == 'overloaded'),
            'queue_total': sum(row['queue_count'] for row in stations),
            'stations': stations,
        }

    # ------------------------------------------------------------------
    # Operations backend contract (V15)
    # ------------------------------------------------------------------
    @api.model
    def _cw_operations_workorder_domain(self, states=None, station_id=None):
        """Company-scoped wash Work Order domain used by the live operations APIs.

        This helper is deliberately read-only. It mirrors Odoo's real Work Order state
        and never reassigns, starts, stops, plans, or completes a Work Order.
        """
        states = states or ACTIVE_WO_STATES
        domain = [
            ('production_id.company_id', '=', self.env.company.id),
            ('production_id.state', 'not in', ['done', 'cancel']),
            ('state', 'in', states),
        ] + self._cw_workorder_wash_domain()
        if station_id:
            domain.append(('workcenter_id', '=', station_id))
        return domain

    @api.model
    def _cw_queue_anchor(self, workorder):
        """Return a deterministic scheduling anchor without claiming it is actual wait start."""
        return workorder.date_start or workorder.create_date or fields.Datetime.now()

    @api.model
    def _cw_queue_sort_key(self, workorder):
        anchor = self._cw_queue_anchor(workorder)
        return (anchor, workorder.id)

    @api.model
    def _cw_queue_entry_payload(self, workorder, station=None, station_position=0, vehicle_cache=None):
        """Serialize one queued Work Order using only authoritative MRP facts."""
        mo = workorder.production_id
        cached_car = (vehicle_cache or {}).get(mo.id)
        car = dict(cached_car or self._cw_mo_vehicle_payload(mo))
        anchor = self._cw_queue_anchor(workorder)
        age_minutes = 0
        if workorder.create_date:
            age_minutes = max(
                0,
                round((fields.Datetime.now() - workorder.create_date).total_seconds() / 60.0),
            )
        station = station or {}
        return {
            'workorder_id': workorder.id,
            'production_id': mo.id,
            'production_name': mo.name or '',
            'mrp_state': workorder.state,
            'operation_name': workorder.name or '',
            'operation_kind': self._cw_operation_kind(workorder.name or ''),
            'station_id': workorder.workcenter_id.id if workorder.workcenter_id else False,
            'station_name': workorder.workcenter_id.display_name if workorder.workcenter_id else '',
            'station_code': station.get('station_code') or '',
            'station_position': station_position,
            'scheduled_anchor': fields.Datetime.to_string(anchor) if anchor else '',
            'created_at': fields.Datetime.to_string(workorder.create_date) if workorder.create_date else '',
            'queue_age_minutes': age_minutes,
            'expected_minutes': round(workorder.duration_expected or 0.0, 2)
                if 'duration_expected' in workorder._fields else 0.0,
            'vehicle': car,
        }

    @api.model
    def _cw_build_queue_payload(self, workorders, stations, vehicle_cache=None):
        station_map = {row['id']: row for row in stations}
        queue_states = ('pending', 'waiting', 'ready')
        queued = workorders.filtered(lambda wo: wo.state in queue_states)
        grouped = defaultdict(list)
        unassigned = []
        foreign_station = []

        for wo in queued:
            station_id = wo.workcenter_id.id if wo.workcenter_id else False
            if not station_id:
                unassigned.append(wo)
            elif station_id not in station_map:
                foreign_station.append(wo)
            else:
                grouped[station_id].append(wo)

        rows = []
        by_station = []
        for station in stations:
            station_wos = sorted(grouped.get(station['id'], []), key=self._cw_queue_sort_key)
            station_rows = [
                self._cw_queue_entry_payload(wo, station, index, vehicle_cache=vehicle_cache)
                for index, wo in enumerate(station_wos, start=1)
            ]
            rows.extend(station_rows)
            by_station.append({
                'station_id': station['id'],
                'station_code': station['station_code'],
                'station_name': station['name'],
                'count': len(station_rows),
                'rows': station_rows,
            })

        return {
            'total': len(rows),
            'rows': rows,
            'by_station': by_station,
            'unassigned_workorder_ids': [wo.id for wo in unassigned],
            'foreign_station_workorder_ids': [wo.id for wo in foreign_station],
        }

    @api.model
    def _cw_operations_contract(self):
        """Build the lightweight live-operations contract.

        Unlike get_dashboard_data(), this payload intentionally excludes finance,
        stock, customer analytics, HR and maintenance. It is safe for frequent refresh.
        """
        company = self.env.company
        Workorder = self.env['mrp.workorder']
        today_start, today_end, _today = self._cw_day_bounds(0)

        workorder_domain = self._cw_operations_workorder_domain()
        workorders = Workorder.search(workorder_domain)

        finished = Workorder.browse()
        if {'duration', 'duration_expected', 'date_finished'} <= set(Workorder._fields):
            finished = Workorder.search([
                ('production_id.company_id', '=', company.id),
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
                ('date_finished', '<', today_end),
            ] + self._cw_workorder_wash_domain())

        active_mos = self.search(
            self._cw_wash_domain() + [('state', 'not in', ['done', 'cancel'])],
            order='date_start asc, id asc',
        )
        vehicle_cache = {mo.id: self._cw_mo_vehicle_payload(mo) for mo in active_mos}
        cars = [vehicle_cache[mo.id] for mo in active_mos]

        stations = self._cw_build_station_payload(
            workorders, finished, workorder_domain, vehicle_cache=vehicle_cache,
        )
        queue = self._cw_build_queue_payload(workorders, stations, vehicle_cache=vehicle_cache)

        progress_wos = workorders.filtered(lambda wo: wo.state == 'progress')
        running_mo_ids = set(progress_wos.mapped('production_id').ids)
        ready_delivery = [car for car in cars if car.get('status_code') == 'ready_delivery']
        waiting_cars = [car for car in cars if car.get('status_code') in ('waiting', 'ready')]

        topology_ids = {row['id'] for row in stations}
        orphan_active = workorders.filtered(
            lambda wo: wo.workcenter_id and wo.workcenter_id.id not in topology_ids
        )
        unassigned_active = workorders.filtered(lambda wo: not wo.workcenter_id)

        return {
            'contract_version': '15.0-operations',
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
            'timezone': self.env.user.tz or 'UTC',
            'company_id': company.id,
            'company_name': company.display_name,
            'currency_symbol': company.currency_id.symbol or '',
            'kpis': {
                'active_vehicles': len(cars),
                'in_service': len(running_mo_ids),
                'waiting_for_station': queue['total'],
                'ready_for_delivery': len(ready_delivery),
                'station_total': len(stations),
                'station_available': sum(1 for row in stations if row['runtime_state'] == 'available'),
                'station_busy': sum(1 for row in stations if row['runtime_state'] in ('busy', 'overloaded')),
                'station_maintenance': sum(1 for row in stations if row['runtime_state'] == 'maintenance'),
                'station_closed': sum(1 for row in stations if row['runtime_state'] == 'closed'),
                'station_overloaded': sum(1 for row in stations if row['runtime_state'] == 'overloaded'),
            },
            'stations': stations,
            'queue': queue,
            'cars': cars,
            'ready_delivery': ready_delivery,
            'waiting_cars': waiting_cars,
            'diagnostics': {
                'orphan_active_workorder_ids': orphan_active.ids,
                'unassigned_active_workorder_ids': unassigned_active.ids,
                'overloaded_station_ids': [
                    row['id'] for row in stations if row['runtime_state'] == 'overloaded'
                ],
            },
            'domains': {
                'active_workorders': workorder_domain,
                'active_productions': self._cw_wash_domain() + [('state', 'not in', ['done', 'cancel'])],
            },
        }

    @api.model
    def get_operations_data(self):
        """Public read-only contract for the future Operations Control Center."""
        return self._cw_operations_contract()

    @api.model
    def get_queue_data(self):
        """Public read-only queue contract, split from the heavy dashboard payload."""
        data = self._cw_operations_contract()
        return {
            'contract_version': data['contract_version'],
            'generated_at': data['generated_at'],
            'timezone': data['timezone'],
            'company_id': data['company_id'],
            'company_name': data['company_name'],
            'queue': data['queue'],
            'station_total': data['kpis']['station_total'],
            'station_available': data['kpis']['station_available'],
            'station_busy': data['kpis']['station_busy'],
            'diagnostics': data['diagnostics'],
        }

    @api.model
    def get_station_details(self, station_id):
        """Return one station with all of its current jobs and queue entries."""
        try:
            station_id = int(station_id)
        except (TypeError, ValueError):
            return {'found': False, 'reason': 'invalid_station_id'}

        workcenters = self._cw_station_workcenters()
        workcenter = workcenters.filtered(lambda wc: wc.id == station_id)[:1]
        if not workcenter:
            return {'found': False, 'reason': 'station_not_found'}

        company = self.env.company
        Workorder = self.env['mrp.workorder']
        today_start, today_end, _today = self._cw_day_bounds(0)
        domain = self._cw_operations_workorder_domain(station_id=station_id)
        workorders = Workorder.search(domain)

        finished = Workorder.browse()
        if {'duration', 'duration_expected', 'date_finished'} <= set(Workorder._fields):
            finished = Workorder.search([
                ('production_id.company_id', '=', company.id),
                ('workcenter_id', '=', station_id),
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
                ('date_finished', '<', today_end),
            ] + self._cw_workorder_wash_domain())

        station_mos = workorders.mapped('production_id')
        vehicle_cache = {mo.id: self._cw_mo_vehicle_payload(mo) for mo in station_mos}
        station_rows = self._cw_build_station_payload(
            workorders, finished, domain, vehicle_cache=vehicle_cache,
        )
        station = next((row for row in station_rows if row['id'] == station_id), False)
        if not station:
            return {'found': False, 'reason': 'station_not_found'}
        queue = self._cw_build_queue_payload(workorders, [station], vehicle_cache=vehicle_cache)

        running = []
        for wo in workorders.filtered(lambda item: item.state == 'progress'):
            running.append({
                'workorder_id': wo.id,
                'production_id': wo.production_id.id,
                'mrp_state': wo.state,
                'operation_name': wo.name or '',
                'expected_minutes': round(wo.duration_expected or 0.0, 2)
                    if 'duration_expected' in wo._fields else 0.0,
                'vehicle': dict(vehicle_cache.get(wo.production_id.id) or self._cw_mo_vehicle_payload(wo.production_id)),
            })

        return {
            'found': True,
            'contract_version': '15.0-operations',
            'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
            'company_id': company.id,
            'station': station,
            'running_jobs': running,
            'queue': queue,
            'active_workorder_ids': workorders.ids,
            'done_today': station.get('done_today', 0),
        }

    # ------------------------------------------------------------------
    # Operational intelligence (V16)
    # ------------------------------------------------------------------
    @api.model
    def _cw_minutes_between(self, start, end=None):
        """Return a non-negative minute delta for two naive UTC datetimes."""
        if not start:
            return 0.0
        end = end or fields.Datetime.now()
        try:
            return max(0.0, (end - start).total_seconds() / 60.0)
        except (TypeError, ValueError):
            return 0.0

    @api.model
    def _cw_workorder_runtime_metrics(self, workorder, now=None):
        """Read-only runtime metrics for one Work Order.

        ``elapsed_minutes`` is deliberately operational, not accounting time.  While a
        Work Order is in progress we use the greater of Odoo's recorded ``duration`` and
        elapsed wall time since ``date_start``.  This avoids reporting zero while a job is
        currently running.  No Work Order field is written by this helper.
        """
        now = now or fields.Datetime.now()
        expected = float(workorder.duration_expected or 0.0) if 'duration_expected' in workorder._fields else 0.0
        recorded = float(workorder.duration or 0.0) if 'duration' in workorder._fields else 0.0
        wall = 0.0
        source = 'recorded_duration'

        if workorder.state == 'progress' and 'date_start' in workorder._fields and workorder.date_start:
            wall = self._cw_minutes_between(workorder.date_start, now)
            source = 'max_recorded_or_running_wall_time'

        elapsed = max(recorded, wall)
        remaining = max(expected - elapsed, 0.0) if expected > 0 else 0.0
        over_expected = bool(expected > 0 and elapsed > expected)
        delay = max(elapsed - expected, 0.0) if expected > 0 else 0.0
        progress_ratio = min((elapsed / expected) * 100.0, 100.0) if expected > 0 else 0.0

        return {
            'expected_minutes': round(expected, 2),
            'recorded_duration_minutes': round(recorded, 2),
            'running_wall_minutes': round(wall, 2),
            'elapsed_minutes': round(elapsed, 2),
            'remaining_minutes': round(remaining, 2),
            'over_expected': over_expected,
            'delay_minutes': round(delay, 2),
            'progress_ratio': round(progress_ratio, 1),
            'elapsed_source': source,
            'eta_known': bool(expected > 0),
        }

    @api.model
    def _cw_station_intelligence_payload(self, station, workorders, finished_today, finished_last_hour, vehicle_cache=None, now=None):
        """Build throughput, delay and queue projection metrics for one station.

        The queue projection never changes Odoo planning.  It is a deterministic read-only
        simulation over the existing MRP Work Order assignment and expected durations.
        """
        now = now or fields.Datetime.now()
        station_id = station['id']
        capacity = max(int(station.get('capacity') or 1), 1)
        station_wos = workorders.filtered(lambda wo: wo.workcenter_id and wo.workcenter_id.id == station_id)
        running = station_wos.filtered(lambda wo: wo.state == 'progress')
        queued = station_wos.filtered(lambda wo: wo.state in ('pending', 'waiting', 'ready'))
        queued = self.env['mrp.workorder'].browse(
            [wo.id for wo in sorted(queued, key=self._cw_queue_sort_key)]
        )

        running_rows = []
        for wo in running:
            metrics = self._cw_workorder_runtime_metrics(wo, now=now)
            car = dict((vehicle_cache or {}).get(wo.production_id.id) or self._cw_mo_vehicle_payload(wo.production_id))
            running_rows.append({
                'workorder_id': wo.id,
                'production_id': wo.production_id.id,
                'operation_name': wo.name or '',
                'vehicle': car,
                **metrics,
            })

        occupancy = len(running_rows)
        overloaded = occupancy > capacity
        projection_reliable = not overloaded

        queue_rows = []
        projected_clear_minutes = 0.0
        if projection_reliable:
            lanes = [0.0] * capacity
            for index, row in enumerate(sorted(running_rows, key=lambda r: r['remaining_minutes'], reverse=True)):
                lane = index % capacity
                lanes[lane] = max(lanes[lane], float(row['remaining_minutes'] or 0.0))

            for position, wo in enumerate(queued, start=1):
                expected = float(wo.duration_expected or 0.0) if 'duration_expected' in wo._fields else 0.0
                lane = min(range(capacity), key=lambda idx: lanes[idx])
                start_in = lanes[lane]
                finish_in = start_in + max(expected, 0.0)
                lanes[lane] = finish_in
                anchor = self._cw_queue_anchor(wo)
                age = self._cw_minutes_between(wo.create_date, now) if wo.create_date else 0.0
                car = dict((vehicle_cache or {}).get(wo.production_id.id) or self._cw_mo_vehicle_payload(wo.production_id))
                queue_rows.append({
                    'workorder_id': wo.id,
                    'production_id': wo.production_id.id,
                    'position': position,
                    'mrp_state': wo.state,
                    'operation_name': wo.name or '',
                    'vehicle': car,
                    'queue_age_minutes': round(age, 2),
                    'scheduled_anchor': fields.Datetime.to_string(anchor) if anchor else '',
                    'expected_minutes': round(expected, 2),
                    'estimated_start_in_minutes': round(start_in, 2),
                    'estimated_finish_in_minutes': round(finish_in, 2),
                    'estimate_reliable': True,
                })
            projected_clear_minutes = max(lanes) if lanes else 0.0
        else:
            for position, wo in enumerate(queued, start=1):
                expected = float(wo.duration_expected or 0.0) if 'duration_expected' in wo._fields else 0.0
                anchor = self._cw_queue_anchor(wo)
                age = self._cw_minutes_between(wo.create_date, now) if wo.create_date else 0.0
                car = dict((vehicle_cache or {}).get(wo.production_id.id) or self._cw_mo_vehicle_payload(wo.production_id))
                queue_rows.append({
                    'workorder_id': wo.id,
                    'production_id': wo.production_id.id,
                    'position': position,
                    'mrp_state': wo.state,
                    'operation_name': wo.name or '',
                    'vehicle': car,
                    'queue_age_minutes': round(age, 2),
                    'scheduled_anchor': fields.Datetime.to_string(anchor) if anchor else '',
                    'expected_minutes': round(expected, 2),
                    'estimated_start_in_minutes': False,
                    'estimated_finish_in_minutes': False,
                    'estimate_reliable': False,
                })

        station_done_today = finished_today.filtered(lambda wo: wo.workcenter_id and wo.workcenter_id.id == station_id)
        station_done_last_hour = finished_last_hour.filtered(lambda wo: wo.workcenter_id and wo.workcenter_id.id == station_id)
        durations = [float(wo.duration or 0.0) for wo in station_done_today if 'duration' in wo._fields and (wo.duration or 0.0) > 0]
        expected_durations = [float(wo.duration_expected or 0.0) for wo in station_done_today if 'duration_expected' in wo._fields and (wo.duration_expected or 0.0) > 0]
        avg_duration = (sum(durations) / len(durations)) if durations else 0.0
        avg_expected = (sum(expected_durations) / len(expected_durations)) if expected_durations else 0.0
        delayed_running = [row for row in running_rows if row['over_expected']]
        queue_ages = [row['queue_age_minutes'] for row in queue_rows]

        return {
            'station_id': station_id,
            'station_code': station.get('station_code') or '',
            'station_name': station.get('name') or '',
            'runtime_state': station.get('runtime_state') or '',
            'capacity': capacity,
            'occupancy': occupancy,
            'queue_count': len(queue_rows),
            'over_capacity': overloaded,
            'projection_reliable': projection_reliable,
            'projection_reason': '' if projection_reliable else 'station_over_capacity',
            'running_jobs': running_rows,
            'queue': queue_rows,
            'delayed_running_jobs': len(delayed_running),
            'max_running_delay_minutes': round(max([row['delay_minutes'] for row in delayed_running], default=0.0), 2),
            'queue_age_avg_minutes': round((sum(queue_ages) / len(queue_ages)) if queue_ages else 0.0, 2),
            'queue_age_max_minutes': round(max(queue_ages, default=0.0), 2),
            'projected_clear_minutes': round(projected_clear_minutes, 2) if projection_reliable else False,
            'done_today': len(station_done_today),
            'done_last_60_minutes': len(station_done_last_hour),
            'avg_duration_today_minutes': round(avg_duration, 2),
            'avg_expected_today_minutes': round(avg_expected, 2),
        }

    @api.model
    def _cw_operational_intelligence_contract(self):
        """Read-only operational intelligence contract for the future control center."""
        company = self.env.company
        Workorder = self.env['mrp.workorder']
        now = fields.Datetime.now()
        today_start, today_end, _today = self._cw_day_bounds(0)
        hour_start = fields.Datetime.to_string(now - timedelta(minutes=60))

        active_domain = self._cw_operations_workorder_domain()
        active_wos = Workorder.search(active_domain)

        finished_base = [
            ('production_id.company_id', '=', company.id),
            ('state', '=', 'done'),
        ] + self._cw_workorder_wash_domain()
        finished_today = Workorder.browse()
        finished_last_hour = Workorder.browse()
        if 'date_finished' in Workorder._fields:
            finished_today = Workorder.search(finished_base + [
                ('date_finished', '>=', today_start),
                ('date_finished', '<', today_end),
            ])
            finished_last_hour = Workorder.search(finished_base + [
                ('date_finished', '>=', hour_start),
                ('date_finished', '<=', fields.Datetime.to_string(now)),
            ])

        active_mos = active_wos.mapped('production_id')
        vehicle_cache = {mo.id: self._cw_mo_vehicle_payload(mo) for mo in active_mos}

        topology = self.get_station_topology()
        station_rows = []
        for station in topology.get('stations', []):
            station_rows.append(self._cw_station_intelligence_payload(
                station,
                active_wos,
                finished_today,
                finished_last_hour,
                vehicle_cache=vehicle_cache,
                now=now,
            ))

        delayed_jobs = [
            row
            for station in station_rows
            for row in station['running_jobs']
            if row['over_expected']
        ]
        queue_ages = [
            row['queue_age_minutes']
            for station in station_rows
            for row in station['queue']
        ]
        reliable_clearances = [
            float(station['projected_clear_minutes'])
            for station in station_rows
            if station['projection_reliable'] and station['projected_clear_minutes'] is not False
        ]
        unreliable_ids = [station['station_id'] for station in station_rows if not station['projection_reliable']]

        done_durations = [
            float(wo.duration or 0.0)
            for wo in finished_today
            if 'duration' in wo._fields and (wo.duration or 0.0) > 0
        ]

        return {
            'contract_version': '16.0-operational-intelligence',
            'generated_at': fields.Datetime.to_string(now),
            'timezone': self.env.user.tz or 'UTC',
            'company_id': company.id,
            'company_name': company.display_name,
            'kpis': {
                'active_workorders': len(active_wos),
                'running_jobs': len(active_wos.filtered(lambda wo: wo.state == 'progress')),
                'queued_jobs': len(active_wos.filtered(lambda wo: wo.state in ('pending', 'waiting', 'ready'))),
                'delayed_running_jobs': len(delayed_jobs),
                'completed_today': len(finished_today),
                'completed_last_60_minutes': len(finished_last_hour),
                'avg_completed_duration_today_minutes': round((sum(done_durations) / len(done_durations)) if done_durations else 0.0, 2),
                'max_queue_age_minutes': round(max(queue_ages, default=0.0), 2),
                'projected_system_clear_minutes': round(max(reliable_clearances), 2) if reliable_clearances else 0.0,
                'projection_reliable_for_all_stations': not unreliable_ids,
            },
            'stations': station_rows,
            'diagnostics': {
                'unreliable_projection_station_ids': unreliable_ids,
                'overloaded_station_ids': [station['station_id'] for station in station_rows if station['over_capacity']],
                'delayed_workorder_ids': [row['workorder_id'] for row in delayed_jobs],
                'projection_policy': 'read_only_existing_mrp_assignment',
            },
            'semantics': {
                'delay': 'A running Work Order is delayed only when elapsed operational minutes exceed duration_expected.',
                'queue_age': 'Minutes since Work Order create_date; this is queue aging, not a promised wait SLA.',
                'eta': 'Queue ETA is simulated from current station assignment, capacity and duration_expected; no MRP record is changed.',
                'throughput': 'Completed Work Orders using date_finished, measured today and over the rolling last 60 minutes.',
            },
        }

    @api.model
    def get_operational_intelligence_data(self):
        """Public V16 read-only intelligence API.  V15 APIs remain unchanged."""
        return self._cw_operational_intelligence_contract()

    # ------------------------------------------------------------------
    # Customer display backend contract (V17)
    # ------------------------------------------------------------------
    @api.model
    def _cw_customer_display_access_allowed(self):
        """Return True only for the dedicated display group or system administrators.

        The display contract deliberately does not piggyback on ordinary MRP/POS ACLs.
        A dedicated TV/user can therefore receive a sanitized projection without being
        granted direct read access to production, POS, accounting or customer records.
        """
        user = self.env.user
        return bool(
            user.has_group('car_wash_dashboard.group_car_wash_customer_display')
            or user.has_group('base.group_system')
        )

    @api.model
    def _cw_require_customer_display_access(self):
        if not self._cw_customer_display_access_allowed():
            raise AccessError(_('You are not allowed to access the car wash customer display.'))
        return True

    @api.model
    def _cw_customer_display_key(self, mo):
        """Return a stable opaque key without exposing the internal MO database ID."""
        created = fields.Datetime.to_string(mo.create_date) if mo.create_date else ''
        seed = f"{mo.company_id.id}:{mo.id}:{created}"
        return hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]

    @api.model
    def _cw_customer_display_progress(self, mo, now=None):
        """Compute a presentation-safe progress estimate without writing MRP data.

        Completed Work Orders contribute 100%.  A currently running Work Order
        contributes its elapsed/expected ratio.  Waiting future stages contribute 0%.
        The value is an operational estimate, not a contractual SLA.
        """
        now = now or fields.Datetime.now()
        workorders = mo.workorder_ids.filtered(lambda wo: wo.state != 'cancel')
        workorders = workorders.sorted(key=lambda wo: (getattr(wo.operation_id, 'sequence', 0), wo.id))
        if not workorders:
            return 100.0 if mo.state in ('to_close', 'done') else 0.0
        if mo.state in ('to_close', 'done'):
            return 100.0

        units = 0.0
        for wo in workorders:
            if wo.state == 'done':
                units += 1.0
            elif wo.state == 'progress':
                metrics = self._cw_workorder_runtime_metrics(wo, now=now)
                units += min(max(float(metrics.get('progress_ratio') or 0.0), 0.0), 100.0) / 100.0
        return round(min(max((units / len(workorders)) * 100.0, 0.0), 100.0), 1)

    @api.model
    def _cw_customer_display_eta_map(self, active_workorders, now=None):
        """Return a workorder->ETA map using the same read-only V16 queue semantics.

        Projection becomes unreliable for a station that is manually closed, under
        maintenance, or already above capacity.  No Work Order assignment/state changes.
        """
        now = now or fields.Datetime.now()
        result = {}
        stations = self._cw_station_workcenters()

        for wc in stations:
            station_wos = active_workorders.filtered(
                lambda wo: wo.workcenter_id and wo.workcenter_id.id == wc.id
            )
            running = station_wos.filtered(lambda wo: wo.state == 'progress')
            queued = station_wos.filtered(lambda wo: wo.state in ('pending', 'waiting', 'ready'))
            queued = self.env['mrp.workorder'].browse(
                [wo.id for wo in sorted(queued, key=self._cw_queue_sort_key)]
            )

            capacity = max(int(wc.default_capacity or 1), 1)
            occupancy = len(running)
            manual_state = wc.cc_station_manual_state or 'open'
            reliable = occupancy <= capacity and manual_state == 'open'
            reason = ''
            if manual_state == 'maintenance':
                reason = 'station_maintenance'
            elif manual_state == 'closed':
                reason = 'station_closed'
            elif occupancy > capacity:
                reason = 'station_over_capacity'

            lanes = [0.0] * capacity
            for index, wo in enumerate(running):
                metrics = self._cw_workorder_runtime_metrics(wo, now=now)
                remaining = float(metrics.get('remaining_minutes') or 0.0)
                if reliable:
                    lane = index % capacity
                    lanes[lane] = max(lanes[lane], remaining)
                eta_known = bool(metrics.get('eta_known'))
                result[wo.id] = {
                    'eta_minutes': round(remaining, 2) if reliable and eta_known else False,
                    'eta_reliable': bool(reliable and eta_known),
                    'eta_scope': 'current_stage',
                    'eta_reason': reason or ('' if eta_known else 'missing_expected_duration'),
                    'queue_position': 0,
                }

            for position, wo in enumerate(queued, start=1):
                expected = float(wo.duration_expected or 0.0) if 'duration_expected' in wo._fields else 0.0
                if reliable and expected > 0:
                    lane = min(range(capacity), key=lambda idx: lanes[idx])
                    start_in = lanes[lane]
                    finish_in = start_in + expected
                    lanes[lane] = finish_in
                    eta = round(finish_in, 2)
                    eta_reliable = True
                    eta_reason = ''
                else:
                    eta = False
                    eta_reliable = False
                    eta_reason = reason or 'missing_expected_duration'
                result[wo.id] = {
                    'eta_minutes': eta,
                    'eta_reliable': eta_reliable,
                    'eta_scope': 'current_stage',
                    'eta_reason': eta_reason,
                    'queue_position': position,
                }

        return result

    @api.model
    def _cw_customer_display_car_payload(self, mo, eta_map=None, now=None):
        """Serialize only fields approved for a public-facing waiting-room screen."""
        now = now or fields.Datetime.now()
        eta_map = eta_map or {}
        internal = self._cw_mo_vehicle_payload(mo)
        workorders = mo.workorder_ids.filtered(lambda wo: wo.state != 'cancel')
        workorders = workorders.sorted(key=lambda wo: (getattr(wo.operation_id, 'sequence', 0), wo.id))
        current_wo = (
            workorders.filtered(lambda wo: wo.state == 'progress')[:1]
            or workorders.filtered(lambda wo: wo.state == 'ready')[:1]
            or workorders.filtered(lambda wo: wo.state == 'waiting')[:1]
            or workorders.filtered(lambda wo: wo.state == 'pending')[:1]
        )
        eta = eta_map.get(current_wo.id, {}) if current_wo else {}

        if mo.state == 'to_close':
            display_state = 'ready_for_pickup'
            display_label = 'جاهزة للاستلام'
            eta = {
                'eta_minutes': 0.0,
                'eta_reliable': True,
                'eta_scope': 'service',
                'eta_reason': '',
                'queue_position': 0,
            }
        elif current_wo and current_wo.state == 'progress':
            display_state = 'in_service'
            display_label = 'قيد الخدمة'
        else:
            display_state = 'waiting'
            display_label = 'في الانتظار'

        plate = internal.get('plate') or ''
        if plate == 'بدون لوحة':
            plate = ''
        origin = (mo.origin or '').strip()
        if origin.startswith('POS-'):
            order_reference = origin[4:].rsplit('/', 1)[-1] or origin[4:]
        else:
            order_reference = origin
        display_key = self._cw_customer_display_key(mo)
        reference = plate or order_reference or ('#' + display_key[:8].upper())

        return {
            'display_key': display_key,
            'public_reference': reference,
            'vehicle_model': internal.get('vehicle_model') or '',
            'vehicle_color': internal.get('vehicle_color') or '',
            'service_name': internal.get('service_name') or '',
            'display_state': display_state,
            'display_label': display_label,
            'progress_percent': self._cw_customer_display_progress(mo, now=now),
            'progress_basis': 'completed_steps_plus_running_expected_duration',
            'current_stage': (current_wo.name or '') if current_wo else ('جاهزة للاستلام' if mo.state == 'to_close' else ''),
            'station_code': (
                current_wo.workcenter_id.cc_station_code
                if current_wo and current_wo.workcenter_id and current_wo.workcenter_id.cc_station_code
                else (current_wo.workcenter_id.code if current_wo and current_wo.workcenter_id else '')
            ),
            'eta_minutes': eta.get('eta_minutes', False),
            'eta_reliable': bool(eta.get('eta_reliable', False)),
            'eta_scope': eta.get('eta_scope', 'current_stage'),
            'eta_reason': eta.get('eta_reason', ''),
            'queue_position': int(eta.get('queue_position') or 0),
        }

    @api.model
    def _cw_customer_display_contract(self):
        """Sanitized read-only data contract for the future standalone TV client."""
        company = self.env.company
        now = fields.Datetime.now()
        Workorder = self.env['mrp.workorder']

        visible_mos = self.search(
            self._cw_wash_domain() + [('state', 'in', ['confirmed', 'progress', 'to_close'])],
            order='date_start asc, id asc',
        )
        active_wos = Workorder.search(self._cw_operations_workorder_domain())
        eta_map = self._cw_customer_display_eta_map(active_wos, now=now)

        cars = [self._cw_customer_display_car_payload(mo, eta_map=eta_map, now=now) for mo in visible_mos]
        ready = [row for row in cars if row['display_state'] == 'ready_for_pickup']
        in_service = [row for row in cars if row['display_state'] == 'in_service']
        waiting = [row for row in cars if row['display_state'] == 'waiting']

        # Rotation intentionally excludes ready-for-pickup vehicles because the future
        # screen has a dedicated ready strip/list.  This avoids showing the same vehicle twice.
        rotation = sorted(
            in_service + waiting,
            key=lambda row: (
                0 if row['display_state'] == 'in_service' else 1,
                row.get('queue_position', 0),
                row['display_key'],
            ),
        )
        ready = sorted(ready, key=lambda row: row['display_key'])

        return {
            'contract_version': '17.0-customer-display',
            'generated_at': fields.Datetime.to_string(now),
            'timezone': self.env.context.get('tz') or self.env.user.tz or 'UTC',
            'company': {
                'id': company.id,
                'name': company.display_name,
                'logo_available': bool(company.logo),
                'logo_url': '/car_wash/customer_display/logo' if company.logo else '',
            },
            'display_policy': {
                'intro_enabled': True,
                'intro_seconds': 2.0,
                'rotation_seconds': 10.0,
                'fullscreen_requires_user_gesture': True,
                'show_vehicle_model': True,
                'show_current_stage': True,
                'show_eta': True,
                'show_ready_for_pickup': True,
            },
            'counts': {
                'visible': len(cars),
                'in_service': len(in_service),
                'waiting': len(waiting),
                'ready_for_pickup': len(ready),
            },
            'idle': not bool(cars),
            'rotation': rotation,
            'ready_for_pickup': ready,
            'semantics': {
                'privacy': 'No customer name, phone, price, payment, accounting or operator identity is exposed.',
                'progress': 'Operational estimate from completed Work Orders plus elapsed/expected ratio of the running stage.',
                'eta': 'ETA is for the current Work Order stage only unless the vehicle is already ready for pickup.',
                'projection': 'Queue projection is read-only and follows existing MRP station assignment and capacity.',
            },
        }

    @api.model
    def get_customer_display_data(self):
        """Permission-gated V17 API used by the future standalone customer display."""
        self._cw_require_customer_display_access()
        company = self.env.company
        request_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        context = dict(
            self.env.context,
            allowed_company_ids=[company.id],
            tz=request_tz,
            cw_customer_display_request_user_id=self.env.user.id,
        )
        return self.sudo().with_company(company).with_context(context)._cw_customer_display_contract()

    # ------------------------------------------------------------------
    # Dashboard V2 payload
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        today_start, today_end, today = self._cw_day_bounds(0)
        now_str = fields.Datetime.to_string(fields.Datetime.now())
        company = self.env.company
        base = self._cw_wash_domain()

        has_deadline = 'date_deadline' in self._fields
        has_reservation = 'reservation_state' in self._fields
        has_start = 'date_start' in self._fields

        # ------------------------------------------------------------------
        # 1) Wash-order KPIs: EVERY domain is scoped to the current company
        #    and to real Crystal Clean wash MOs.
        # ------------------------------------------------------------------
        kpi_domains = {
            'total_today': base + [('create_date', '>=', today_start), ('create_date', '<', today_end)],
            'in_progress': base + [('state', '=', 'progress')],
            'done_today': base + [('state', '=', 'done'), ('date_finished', '>=', today_start), ('date_finished', '<', today_end)],
            'waiting': base + [('state', '=', 'confirmed')],
            'ready_delivery': base + [('state', '=', 'to_close')],
            'active_total': base + [('state', 'not in', ['done', 'cancel'])],
        }
        kpis = {key: self.search_count(domain) for key, domain in kpi_domains.items()}

        mfg_domains = {}
        overdue = 0
        if has_deadline:
            mfg_domains['overdue'] = base + [
                ('date_deadline', '!=', False),
                ('date_deadline', '<', now_str),
                ('state', 'not in', ['done', 'cancel']),
            ]
            overdue = self.search_count(mfg_domains['overdue'])

        ready = 0
        if has_reservation:
            mfg_domains['ready'] = base + [
                ('reservation_state', '=', 'assigned'),
                ('state', '=', 'confirmed'),
            ]
            ready = self.search_count(mfg_domains['ready'])

        pipeline = []
        for code, label in PIPELINE_STATES:
            domain = base + [('state', '=', code)]
            mfg_domains['state_%s' % code] = domain
            pipeline.append({'code': code, 'label': label, 'count': self.search_count(domain)})

        # ------------------------------------------------------------------
        # 2) Work orders / Shop Floor
        # ------------------------------------------------------------------
        Workorder = self.env['mrp.workorder']
        wo_base = [
            ('production_id.company_id', '=', company.id),
            ('production_id.state', 'not in', ['done', 'cancel']),
            ('state', 'in', ACTIVE_WO_STATES),
        ]
        wo_base += self._cw_workorder_wash_domain()

        workorders = Workorder.search(wo_base)

        wo_efficiency = 0
        finished_wo = Workorder.browse()
        if {'duration', 'duration_expected', 'date_finished'} <= set(Workorder._fields):
            finished_domain = [
                ('production_id.company_id', '=', company.id),
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
                ('date_finished', '<', today_end),
            ]
            finished_domain += self._cw_workorder_wash_domain()
            finished_wo = Workorder.search(finished_domain)
            real = sum(finished_wo.mapped('duration'))
            expected = sum(finished_wo.mapped('duration_expected'))
            if real > 0:
                wo_efficiency = round((expected / real) * 100)

        phase_map = {}
        for wo in workorders:
            op = wo.operation_id
            key = op.id or 0
            phase_map.setdefault(key, {
                'operation_id': op.id or False,
                'name': op.name or 'بدون مرحلة',
                'count': 0,
                'domain': wo_base + [('operation_id', '=', op.id or False)],
            })
            phase_map[key]['count'] += 1
        phases = sorted(phase_map.values(), key=lambda p: p['count'], reverse=True)

        workcenter_load = self._cw_build_station_payload(workorders, finished_wo, wo_base)

        workcenter_dist = [
            {'id': wc['id'], 'name': wc['name'], 'count': wc['load']}
            for wc in workcenter_load if wc['load']
        ]

        # ------------------------------------------------------------------
        # 3) Services / vehicles
        # ------------------------------------------------------------------
        service_templates = self._cw_service_templates()
        service_products = service_templates.mapped('product_variant_ids')

        active_mos = self.search(kpi_domains['active_total'], order='date_start asc, id asc')
        active_cars = [self._cw_mo_vehicle_payload(mo) for mo in active_mos]

        service_dist = []
        for service in service_products.sorted(key=lambda p: p.display_name):
            domain = kpi_domains['active_total'] + [('x_cc_service_product_id', '=', service.id)] if 'x_cc_service_product_id' in self._fields else []
            count = self.search_count(domain) if domain else 0
            service_dist.append({
                'id': service.id,
                'name': service.display_name,
                'count': count,
                'domain': domain,
            })

        done_orders = self.search(kpi_domains['done_today'], order='date_finished desc')
        durations = []
        for mo in done_orders:
            start_dt = mo.date_start or mo.create_date
            if mo.date_finished and start_dt:
                durations.append((mo.date_finished - start_dt).total_seconds() / 60.0)
        avg_turnaround = round(sum(durations) / len(durations)) if durations else 0

        upcoming = []
        if has_start:
            ups = self.search(
                base + [
                    ('state', 'in', ['draft', 'confirmed']),
                    ('date_start', '!=', False),
                    ('date_start', '>=', today_start),
                ],
                order='date_start asc', limit=30,
            )
            upcoming = [self._cw_mo_vehicle_payload(mo) for mo in ups]

        timeline = []
        for mo in done_orders[:10]:
            item = self._cw_mo_vehicle_payload(mo)
            item['completed_at'] = self._cw_local_hm(mo.date_finished)
            timeline.append(item)

        trend = []
        for i in range(6, -1, -1):
            start, end, day = self._cw_day_bounds(-i)
            count = self.search_count(base + [
                ('state', '=', 'done'),
                ('date_finished', '>=', start),
                ('date_finished', '<', end),
            ])
            trend.append({'label': AR_DAYS[day.weekday()], 'date': day.strftime('%d/%m'), 'count': count})

        # ------------------------------------------------------------------
        # 4) Sales: only Crystal Clean wash-service lines count as wash sales
        # ------------------------------------------------------------------
        SaleOrder = self.env['sale.order']
        SaleLine = self.env['sale.order.line']

        sale_domains = {
            'revenue_today': [
                ('company_id', '=', company.id),
                ('date_order', '>=', today_start),
                ('date_order', '<', today_end),
                ('state', 'in', ['sale', 'done']),
                ('order_line.product_id', 'in', service_products.ids),
            ],
            'pending_quotations': [
                ('company_id', '=', company.id),
                ('state', 'in', ['draft', 'sent']),
                ('order_line.product_id', 'in', service_products.ids),
            ],
        }

        wash_line_domain = [
            ('order_id.company_id', '=', company.id),
            ('order_id.date_order', '>=', today_start),
            ('order_id.date_order', '<', today_end),
            ('order_id.state', 'in', ['sale', 'done']),
            ('product_id', 'in', service_products.ids),
            ('display_type', '=', False),
        ]
        sale_lines_today = SaleLine.search(wash_line_domain)
        revenue_today = round(sum(sale_lines_today.mapped('price_total')), 2)
        pending_quotations = SaleOrder.search_count(sale_domains['pending_quotations'])
        wash_sales_orders_today = len(sale_lines_today.mapped('order_id'))
        avg_ticket = round(revenue_today / wash_sales_orders_today, 2) if wash_sales_orders_today else 0.0

        # ------------------------------------------------------------------
        # 4b) Point of Sale: the real commercial source for this wash center.
        # ------------------------------------------------------------------
        pos_domains = {}
        pos_orders_today = 0
        pos_revenue_today = 0.0
        pos_avg_ticket = 0.0
        if 'pos.order' in self.env and 'pos.order.line' in self.env:
            PosLine = self.env['pos.order.line']
            pos_line_domain = [
                ('order_id.company_id', '=', company.id),
                ('order_id.date_order', '>=', today_start),
                ('order_id.date_order', '<', today_end),
                ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                ('product_id', 'in', service_products.ids),
            ]
            pos_lines_today = PosLine.search(pos_line_domain)
            pos_order_records = pos_lines_today.mapped('order_id')
            pos_orders_today = len(pos_order_records)
            pos_revenue_today = round(sum(pos_lines_today.mapped('price_subtotal_incl')), 2)
            pos_avg_ticket = round(pos_revenue_today / pos_orders_today, 2) if pos_orders_today else 0.0
            pos_domains['orders_today'] = [
                ('id', 'in', pos_order_records.ids),
            ]

        # ------------------------------------------------------------------
        # 5) Accounting KPIs (posted customer invoices only)
        # ------------------------------------------------------------------
        accounting_domains = {}
        invoiced_today = 0.0
        receivable_open = 0.0
        posted_invoices_today = 0
        if 'account.move' in self.env:
            Move = self.env['account.move']
            today_date = fields.Date.to_string(today)
            accounting_domains['invoiced_today'] = [
                ('company_id', '=', company.id),
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('invoice_date', '=', today_date),
            ]
            moves_today = Move.search(accounting_domains['invoiced_today'])
            posted_invoices_today = len(moves_today)
            invoiced_today = round(
                sum(m.amount_total if m.move_type == 'out_invoice' else -m.amount_total for m in moves_today),
                2,
            )

            accounting_domains['receivable_open'] = [
                ('company_id', '=', company.id),
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('payment_state', 'not in', ['paid', 'reversed']),
            ]
            open_moves = Move.search(accounting_domains['receivable_open'])
            receivable_open = round(
                sum(m.amount_residual if m.move_type == 'out_invoice' else -m.amount_residual for m in open_moves),
                2,
            )

        # ------------------------------------------------------------------
        # 6) Materials: read the 12 real recipe materials directly.
        # ------------------------------------------------------------------
        materials = []
        low_stock = []
        material_products = self._cw_material_products(service_templates)
        Quant = self.env['stock.quant']
        Orderpoint = self.env['stock.warehouse.orderpoint']

        for product in material_products.sorted(key=lambda p: p.display_name):
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
            is_low = bool(has_minimum and free_qty < min_qty)

            item = {
                'product_id': product.id,
                'product_name': product.display_name,
                'on_hand': round(on_hand, 2),
                'reserved': round(reserved, 2),
                'free': round(free_qty, 2),
                'min_qty': round(min_qty, 2),
                'has_minimum': has_minimum,
                'is_low': is_low,
                'uom': product.uom_id.name or '',
            }
            materials.append(item)
            if is_low:
                low_stock.append(item)

        materials.sort(key=lambda item: (item['free'], item['product_name']))
        materials = self._cw_apply_material_burn_rate(materials)

        # ------------------------------------------------------------------
        # 7) Scrap: only scrap linked to real wash MOs.
        # ------------------------------------------------------------------
        scrap_qty = 0.0
        scrap_count = 0
        scrap_domain = []
        if 'stock.scrap' in self.env:
            Scrap = self.env['stock.scrap']
            scrap_domain = [
                ('company_id', '=', company.id),
                ('create_date', '>=', today_start),
                ('create_date', '<', today_end),
            ]
            if 'production_id' in Scrap._fields:
                if 'to_make_mrp' in self.env['product.template']._fields:
                    scrap_domain += [('production_id.product_id.product_tmpl_id.to_make_mrp', '=', True)]
                elif 'x_cc_is_wash_order' in self._fields:
                    scrap_domain += [('production_id.x_cc_is_wash_order', '=', True)]
                else:
                    scrap_domain += [('production_id.origin', '=like', 'POS-%')]
            scraps = Scrap.search(scrap_domain)
            scrap_count = len(scraps)
            scrap_qty = round(sum(scraps.mapped('scrap_qty')), 2)

        station_busy = sum(1 for item in workcenter_load if item.get('runtime_state') in ('busy', 'overloaded'))
        station_free = sum(1 for item in workcenter_load if item.get('runtime_state') == 'available')
        station_queue = sum(item.get('queue_count', item.get('queue', 0)) for item in workcenter_load)
        station_total = len(workcenter_load)
        station_overloaded = sum(1 for item in workcenter_load if item.get('runtime_state') == 'overloaded')
        station_maintenance = sum(1 for item in workcenter_load if item.get('runtime_state') == 'maintenance')
        station_closed = sum(1 for item in workcenter_load if item.get('runtime_state') == 'closed')
        material_reserved_count = sum(1 for item in materials if item.get('reserved', 0) > 0)
        known_plate_count = sum(1 for car in active_cars if car.get('plate') and car.get('plate') != 'بدون لوحة')
        data_quality = round((known_plate_count / len(active_cars)) * 100, 1) if active_cars else 100.0

        try:
            pos_extra = self._cw_pos_extra_payload(service_products, today_start, today_end)
        except Exception:
            pos_extra = {
                'orders': [], 'top_services': [], 'hourly': [], 'orders_today': 0,
                'revenue_today': 0.0, 'avg_ticket': 0.0, 'customers_today': 0,
                'month_revenue': 0.0, 'month_orders': 0,
            }
        try:
            finance_extra = self._cw_finance_extra_payload(today, today_start, today_end, pos_extra)
        except Exception:
            finance_extra = {
                'recent_moves': [], 'expense_breakdown': [], 'week_pos_sales': [],
                'customer_invoices_today': 0, 'vendor_bills_today': 0,
                'receivable_open': 0.0, 'payable_open': 0.0,
                'pos_revenue_today': pos_extra.get('revenue_today', 0.0),
                'pos_month_revenue': pos_extra.get('month_revenue', 0.0),
                'collected_today': 0.0, 'expense_today': 0.0,
                'net_today': pos_extra.get('revenue_today', 0.0), 'month_expense': 0.0,
            }
        stock_value = round(sum(
            item.get('free', 0.0) * (self.env['product.product'].browse(item['product_id']).standard_price or 0.0)
            for item in materials
        ), 2)
        current_user = self.env.user
        try:
            client_hr_page = self._cw_client_hr_payload(service_products, today_start, today_end)
        except Exception:
            client_hr_page = {
                'customer_rows': [], 'top_customers': [], 'total_customers': 0,
                'repeat_customers': 0, 'new_customers_month': 0, 'inactive_30': 0,
                'user_rows': [], 'total_users': 0, 'present_today': 0,
                'attendance_rate': 0.0, 'shift_rows': [], 'shift_count': 0,
                'station_workers': 0,
            }
        customer_screen = {
            'cars': sorted(active_cars, key=lambda c: (0 if c.get('status_code') == 'ready_delivery' else 1, -c.get('progress', 0), c.get('elapsed_minutes', 0))),
            'ready_count': sum(1 for c in active_cars if c.get('status_code') == 'ready_delivery'),
            'washing_count': sum(1 for c in active_cars if c.get('status_code') == 'washing'),
            'waiting_count': sum(1 for c in active_cars if c.get('status_code') in ('waiting', 'ready')),
            'avg_turnaround': avg_turnaround,
        }
        try:
            customer_page = self._cw_customer_page_payload(service_products, today_start, today_end)
        except Exception:
            customer_page = {'rows': [], 'total': 0, 'repeat': 0, 'new_today': 0, 'inactive_30': 0}
        try:
            maintenance_page = self._cw_maintenance_page_payload(today)
        except Exception:
            maintenance_page = {'available': False, 'rows': [], 'equipment_count': 0, 'due_soon': 0, 'open_faults': 0, 'health_avg': 0}
        station_utilization = round(sum(w.get('utilization', 0.0) for w in workcenter_load) / len(workcenter_load), 1) if workcenter_load else 0.0
        reports_page = {
            'avg_service_minutes': avg_turnaround,
            'workorder_efficiency': wo_efficiency,
            'station_utilization': station_utilization,
            'data_quality': data_quality,
            'trend': trend,
            'hourly': pos_extra.get('hourly', []),
            'top_services': pos_extra.get('top_services', []),
        }

        return {
            'dashboard_version': '15.0-operations-contract',
            'company_id': company.id,
            'company_name': company.display_name,
            'currency_symbol': company.currency_id.symbol or '',
            'station_busy': station_busy,
            'station_free': station_free,
            'station_queue': station_queue,
            'station_total': station_total,
            'station_overloaded': station_overloaded,
            'station_maintenance': station_maintenance,
            'station_closed': station_closed,
            'material_reserved_count': material_reserved_count,
            'data_quality': data_quality,
            **kpis,
            'overdue': overdue,
            'ready': ready,
            'wo_efficiency': wo_efficiency,
            'scrap_qty': scrap_qty,
            'scrap_count': scrap_count,
            'pipeline': pipeline,
            'revenue_today': revenue_today,
            'wash_sales_orders_today': wash_sales_orders_today,
            'avg_ticket': avg_ticket,
            'pending_quotations': pending_quotations,
            'pos_orders_today': pos_orders_today,
            'pos_revenue_today': pos_revenue_today,
            'pos_avg_ticket': pos_avg_ticket,
            'invoiced_today': invoiced_today,
            'posted_invoices_today': posted_invoices_today,
            'receivable_open': receivable_open,
            'avg_turnaround': avg_turnaround,
            'phases': phases,
            'workcenter_dist': workcenter_dist,
            'workcenter_load': workcenter_load,
            'service_dist': service_dist,
            # Legacy key kept so an older browser asset does not crash during deployment.
            'wash_dist': service_dist,
            'active_cars': active_cars,
            'trend': trend,
            'upcoming': upcoming,
            'timeline': timeline,
            'materials': materials,
            'low_stock': low_stock,
            'kpi_domains': kpi_domains,
            'mfg_domains': mfg_domains,
            'sale_domains': sale_domains,
            'accounting_domains': accounting_domains,
            'pos_domains': pos_domains,
            'scrap_domain': scrap_domain,
            'today_start': today_start,
            'journey_car': active_cars[0] if active_cars else False,
            'shop_floor_action': 'mrp_workorder.action_mrp_display',
            'pos_page': pos_extra,
            'finance_page': finance_extra,
            'customer_screen': customer_screen,
            'customer_page': customer_page,
            'client_hr_page': client_hr_page,
            'current_user_name': current_user.name or '',
            'current_user_initial': (current_user.name or 'U')[:1],
            'current_user_role': '',
            'maintenance_page': maintenance_page,
            'reports_page': reports_page,
            'stock_value': stock_value,
            'bus_channel': self._cw_dashboard_channel(company.id),
            'realtime_enabled': 'bus.bus' in self.env.registry.models,
        }
