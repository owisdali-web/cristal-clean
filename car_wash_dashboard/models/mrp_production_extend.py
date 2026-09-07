# -*- coding: utf-8 -*-
from datetime import datetime, time
import pytz

from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    license_plate = fields.Char('License Plate')
    wash_type = fields.Selection([
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('deluxe', 'Deluxe'),
    ], string='Wash Type', default='basic')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _cw_today_start(self):
        """Return the start of *today* in the user's timezone, expressed as a
        naive UTC datetime string.

        ``create_date`` / ``date_finished`` are stored in UTC, so we convert the
        user's local midnight to UTC. Returning it as a string lets us reuse the
        exact same value both for the server-side counts and for the front-end
        drill-down domains, so the two can never disagree.
        """
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        now_local = datetime.now(user_tz)
        start_local = user_tz.localize(datetime.combine(now_local.date(), time.min))
        start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
        return fields.Datetime.to_string(start_utc)

    # ------------------------------------------------------------------
    # Dashboard payload
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        """Aggregated KPIs + ready-to-use domains for the dashboard."""
        today_start = self._cw_today_start()

        # -- KPI domains (kept here so the counts and the click-through always
        #    resolve to the exact same set of records) --------------------
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
        }
        kpis = {key: self.search_count(dom) for key, dom in kpi_domains.items()}

        # -- Active work orders (read once, reused everywhere below) --------
        Workorder = self.env['mrp.workorder']
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

        # -- Distribution by work center (for the doughnut) ----------------
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
            'تلميع': 'fa-gem',
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

        # -- Timeline: orders completed today ------------------------------
        done_orders = self.search(
            kpi_domains['done_today'], order='date_finished desc', limit=10,
        )
        timeline = [{
            'id': o.id,
            'name': o.name or ('Order %s' % o.id),
            'license_plate': o.license_plate or 'N/A',
            'completed_at': o.date_finished.strftime('%H:%M') if o.date_finished else '',
            'wash_type': o.wash_type or 'basic',
        } for o in done_orders]

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
            'phases': phases,
            'workcenter_dist': workcenter_dist,
            'workcenter_load': workcenter_load,
            'timeline': timeline,
            'low_stock': low_stock,
            # reused by the front-end to build drill-down domains
            'kpi_domains': kpi_domains,
            'today_start': today_start,
        }
