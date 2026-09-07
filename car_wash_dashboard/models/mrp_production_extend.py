# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
import pytz

from odoo import models, fields, api

AR_DAYS = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']

WASH_TYPES = [
    ('basic', 'Basic'),
    ('premium', 'Premium'),
    ('deluxe', 'Deluxe'),
]

# MO states shown in the pipeline strip (valid mrp.production states).
PIPELINE_STATES = [
    ('draft', 'مسودة'),
    ('confirmed', 'مؤكدة'),
    ('progress', 'قيد التنفيذ'),
    ('to_close', 'بانتظار الإغلاق'),
]


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    license_plate = fields.Char('License Plate')
    wash_type = fields.Selection(WASH_TYPES, string='Wash Type', default='basic')

    # ------------------------------------------------------------------
    # Timezone helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_day_bounds(self, offset=0):
        """``(start_str, end_str, date)`` for a day relative to today, computed
        in the user's timezone, as naive-UTC strings for safe comparison."""
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        day = (datetime.now(user_tz) + timedelta(days=offset)).date()
        start_local = user_tz.localize(datetime.combine(day, time.min))
        end_local = start_local + timedelta(days=1)

        def to_utc_str(dt_local):
            return fields.Datetime.to_string(dt_local.astimezone(pytz.utc).replace(tzinfo=None))

        return to_utc_str(start_local), to_utc_str(end_local), day

    @api.model
    def _cw_today_start(self):
        start, _end, _day = self._cw_day_bounds(0)
        return start

    def _cw_local_hm(self, dt):
        """Format a stored (UTC) datetime as HH:MM in the user's timezone."""
        if not dt:
            return ''
        return fields.Datetime.context_timestamp(self, dt).strftime('%H:%M')

    def _cw_local_dm(self, dt):
        if not dt:
            return ''
        return fields.Datetime.context_timestamp(self, dt).strftime('%d/%m')

    # ------------------------------------------------------------------
    # Dashboard payload
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        today_start = self._cw_today_start()
        now_str = fields.Datetime.to_string(fields.Datetime.now())
        company = self.env.company

        has_deadline = 'date_deadline' in self._fields
        has_res = 'reservation_state' in self._fields
        has_start = 'date_start' in self._fields

        # -- Manufacturing KPI domains (single source of truth) ------------
        kpi_domains = {
            'total_today': [('create_date', '>=', today_start)],
            'in_progress': [('state', '=', 'progress')],
            'done_today': [
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
            ],
            'waiting': [
                ('state', 'in', ['confirmed', 'planned']),
                ('workorder_ids', '=', False),
            ],
            'active_total': [('state', 'not in', ['done', 'cancel'])],
        }
        kpis = {key: self.search_count(dom) for key, dom in kpi_domains.items()}

        # -- Extra manufacturing KPIs (drill-down domains) -----------------
        mfg_domains = {}

        overdue = 0
        if has_deadline:
            mfg_domains['overdue'] = [
                ('date_deadline', '!=', False),
                ('date_deadline', '<', now_str),
                ('state', 'not in', ['done', 'cancel']),
            ]
            overdue = self.search_count(mfg_domains['overdue'])

        ready = 0
        if has_res:
            mfg_domains['ready'] = [
                ('reservation_state', '=', 'assigned'),
                ('state', '=', 'confirmed'),
            ]
            ready = self.search_count(mfg_domains['ready'])

        # MO status pipeline
        pipeline = []
        for code, label in PIPELINE_STATES:
            mfg_domains['state_%s' % code] = [('state', '=', code)]
            pipeline.append({
                'code': code,
                'label': label,
                'count': self.search_count([('state', '=', code)]),
            })

        # -- Work-order efficiency today (expected vs real duration) -------
        Workorder = self.env['mrp.workorder']
        wo_efficiency = 0
        wo_fields = Workorder._fields
        if {'duration', 'duration_expected', 'date_finished'} <= set(wo_fields):
            finished_wo = Workorder.search([
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
            ])
            real = sum(finished_wo.mapped('duration'))
            expected = sum(finished_wo.mapped('duration_expected'))
            if real > 0:
                wo_efficiency = round((expected / real) * 100)

        # -- Scrap today ---------------------------------------------------
        scrap_qty = 0.0
        scrap_count = 0
        scrap_domain = None
        if 'stock.scrap' in self.env:
            Scrap = self.env['stock.scrap']
            scrap_domain = [('create_date', '>=', today_start)]
            if 'production_id' in Scrap._fields:
                scrap_domain = scrap_domain + [('production_id', '!=', False)]
            scraps = Scrap.search(scrap_domain)
            scrap_count = len(scraps)
            scrap_qty = round(sum(scraps.mapped('scrap_qty')), 2)

        # -- Sales side (flow starts from a sale order) --------------------
        SaleOrder = self.env['sale.order']
        sale_domains = {
            'revenue_today': [('date_order', '>=', today_start), ('state', '=', 'sale')],
            'pending_quotations': [('state', 'in', ['draft', 'sent'])],
        }
        confirmed_today = SaleOrder.search(sale_domains['revenue_today'])
        revenue_today = sum(confirmed_today.mapped('amount_total'))
        pending_quotations = SaleOrder.search_count(sale_domains['pending_quotations'])

        # -- Average turnaround (create -> finished) for orders done today --
        done_orders = self.search(kpi_domains['done_today'], order='date_finished desc')
        durations = [
            (o.date_finished - o.create_date).total_seconds() / 60.0
            for o in done_orders if o.date_finished and o.create_date
        ]
        avg_turnaround = round(sum(durations) / len(durations)) if durations else 0

        # -- Active work orders (read once, reused below) ------------------
        workorders = Workorder.search([
            ('production_id.state', 'not in', ['done', 'cancel']),
            ('state', 'in', ['pending', 'progress']),
        ])

        # -- Distribution by phase (operation) -----------------------------
        phase_map = {}
        for wo in workorders:
            op = wo.operation_id
            key = op.id or 0
            phase_map.setdefault(key, {
                'operation_id': op.id or False,
                'name': op.name or 'بدون عملية',
                'count': 0,
            })
            phase_map[key]['count'] += 1
        phases = sorted(phase_map.values(), key=lambda p: p['count'], reverse=True)

        # -- Distribution by work center (doughnut) ------------------------
        wc_map = {}
        for wo in workorders:
            wc = wo.workcenter_id
            if not wc:
                continue
            wc_map.setdefault(wc.id, {'id': wc.id, 'name': wc.name or '', 'count': 0})
            wc_map[wc.id]['count'] += 1
        workcenter_dist = sorted(wc_map.values(), key=lambda w: w['count'], reverse=True)

        # -- Work-center load / utilisation --------------------------------
        icon_map = {
            'غسيل خارجي': 'fa-car',
            'غسيل داخلي': 'fa-tint',
            'تجفيف': 'fa-wind',
            'تلميع': 'fa-diamond',
            'غسيل': 'fa-car',
        }
        workcenter_load = []
        for wc in self.env['mrp.workcenter'].search([]):
            load = wc_map.get(wc.id, {}).get('count', 0)
            capacity = wc.default_capacity or 0
            if not capacity and wc.capacity_ids:
                capacity = wc.capacity_ids[0].capacity or 0
            if not capacity or capacity <= 0:
                capacity = 1
            workcenter_load.append({
                'id': wc.id,
                'name': wc.name or 'Unknown Workcenter',
                'load': load,
                'capacity': capacity,
                'utilization': round((load / capacity) * 100, 1),
                'icon': icon_map.get(wc.name, 'fa-wrench'),
            })

        # -- Wash-type breakdown (completed today) -------------------------
        wash_dist = []
        for code, label in WASH_TYPES:
            wash_dist.append({
                'code': code,
                'label': label,
                'count': self.search_count(kpi_domains['done_today'] + [('wash_type', '=', code)]),
            })

        # -- 7-day throughput trend (completed per day) --------------------
        trend = []
        for i in range(6, -1, -1):
            start, end, day = self._cw_day_bounds(-i)
            count = self.search_count([
                ('state', '=', 'done'),
                ('date_finished', '>=', start),
                ('date_finished', '<', end),
            ])
            trend.append({
                'label': AR_DAYS[day.weekday()],
                'date': day.strftime('%d/%m'),
                'count': count,
            })

        # -- Upcoming / scheduled (not started yet) ------------------------
        upcoming = []
        if has_start:
            ups = self.search([
                ('state', 'in', ['draft', 'confirmed']),
                ('date_start', '!=', False),
                ('date_start', '>=', today_start),
            ], order='date_start asc', limit=6)
            for o in ups:
                upcoming.append({
                    'id': o.id,
                    'name': o.name or ('Order %s' % o.id),
                    'license_plate': o.license_plate or 'N/A',
                    'wash_type': o.wash_type or 'basic',
                    'scheduled_at': self._cw_local_hm(o.date_start),
                    'scheduled_date': self._cw_local_dm(o.date_start),
                    'ready': (o.reservation_state == 'assigned') if has_res else False,
                })

        # -- Timeline: completed today (max 10) ----------------------------
        timeline = [{
            'id': o.id,
            'name': o.name or ('Order %s' % o.id),
            'license_plate': o.license_plate or 'N/A',
            'completed_at': self._cw_local_hm(o.date_finished),
            'wash_type': o.wash_type or 'basic',
        } for o in done_orders[:10]]

        # -- Low-stock alerts (all warehouses) -----------------------------
        low_stock = []
        for op in self.env['stock.warehouse.orderpoint'].search([]):
            product = op.product_id
            available = product.qty_available
            if available < (op.product_min_qty or 0):
                low_stock.append({
                    'product_id': product.id,
                    'product_name': product.display_name,
                    'available': available,
                    'min_qty': op.product_min_qty or 0,
                })

        return {
            **kpis,
            'overdue': overdue,
            'ready': ready,
            'wo_efficiency': wo_efficiency,
            'scrap_qty': scrap_qty,
            'scrap_count': scrap_count,
            'pipeline': pipeline,
            'upcoming': upcoming,
            'revenue_today': revenue_today,
            'pending_quotations': pending_quotations,
            'avg_turnaround': avg_turnaround,
            'currency_symbol': company.currency_id.symbol or '',
            'phases': phases,
            'workcenter_dist': workcenter_dist,
            'workcenter_load': workcenter_load,
            'wash_dist': wash_dist,
            'trend': trend,
            'timeline': timeline,
            'low_stock': low_stock,
            # reused by the front-end for drill-down
            'kpi_domains': kpi_domains,
            'mfg_domains': mfg_domains,
            'sale_domains': sale_domains,
            'scrap_domain': scrap_domain or [],
            'today_start': today_start,
        }
