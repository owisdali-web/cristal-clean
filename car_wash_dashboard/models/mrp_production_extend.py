# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from collections import defaultdict

import pytz

from odoo import api, fields, models


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
        if 'x_cc_is_wash_order' in self._fields:
            domain.append(('x_cc_is_wash_order', '=', True))
        return domain

    @api.model
    def _cw_service_templates(self):
        ProductTemplate = self.env['product.template']
        domain = [('active', '=', True), ('type', '=', 'service')]
        if 'x_cc_recipe_bom_id' in ProductTemplate._fields:
            domain.append(('x_cc_recipe_bom_id', '!=', False))
        return ProductTemplate.search(domain)

    @api.model
    def _cw_material_products(self, service_templates):
        Product = self.env['product.product']
        if not service_templates or 'x_cc_recipe_bom_id' not in service_templates._fields:
            return Product.browse()
        products = Product.browse()
        for bom in service_templates.mapped('x_cc_recipe_bom_id'):
            products |= bom.bom_line_ids.mapped('product_id')
        return products

    @api.model
    def _cw_mo_vehicle_payload(self, mo):
        sale = mo.sale_line_id.order_id if mo.sale_line_id else self.env['sale.order']
        service = False
        if 'x_cc_service_product_id' in mo._fields:
            service = mo.x_cc_service_product_id
        if not service and mo.sale_line_id:
            service = mo.sale_line_id.product_id

        def mo_value(field_name):
            return getattr(mo, field_name, False) if field_name in mo._fields else False

        def sale_value(field_name):
            return getattr(sale, field_name, False) if sale and field_name in sale._fields else False

        plate = mo_value('x_cc_vehicle_plate') or sale_value('x_cc_vehicle_plate') or mo.license_plate or ''
        model = mo_value('x_cc_vehicle_model') or sale_value('x_cc_vehicle_model') or ''
        color = mo_value('x_cc_vehicle_color') or sale_value('x_cc_vehicle_color') or ''
        notes = mo_value('x_cc_vehicle_notes') or sale_value('x_cc_vehicle_notes') or ''
        vehicle_type = sale_value('vehicle_type') or 'car'

        workorders = mo.workorder_ids.filtered(lambda w: w.state != 'cancel')
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

        return {
            'id': mo.id,
            'name': mo.name or '',
            'sale_order': mo_value('x_cc_sale_order_ref') or mo.origin or (sale.name if sale else '') or '',
            'customer': sale.partner_id.display_name if sale and sale.partner_id else '',
            'plate': plate or 'بدون لوحة',
            'vehicle_model': model or '',
            'vehicle_color': color or '',
            'vehicle_notes': notes or '',
            'vehicle_type': vehicle_type,
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
        }

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
        if 'x_cc_is_wash_order' in self._fields:
            wo_base.append(('production_id.x_cc_is_wash_order', '=', True))

        workorders = Workorder.search(wo_base)

        wo_efficiency = 0
        if {'duration', 'duration_expected', 'date_finished'} <= set(Workorder._fields):
            finished_domain = [
                ('production_id.company_id', '=', company.id),
                ('state', '=', 'done'),
                ('date_finished', '>=', today_start),
                ('date_finished', '<', today_end),
            ]
            if 'x_cc_is_wash_order' in self._fields:
                finished_domain.append(('production_id.x_cc_is_wash_order', '=', True))
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

        wc_map = defaultdict(list)
        for wo in workorders:
            if wo.workcenter_id:
                wc_map[wo.workcenter_id.id].append(wo)

        workcenter_load = []
        Workcenter = self.env['mrp.workcenter']
        wc_domain = [('active', '=', True)]
        if 'company_id' in Workcenter._fields:
            wc_domain += ['|', ('company_id', '=', False), ('company_id', '=', company.id)]

        icon_map = {
            'الآلي': 'fa-car',
            'خارجي': 'fa-tint',
            'داخلي': 'fa-shower',
            'عميق': 'fa-tint',
            'صالة': 'fa-home',
            'فودرة': 'fa-cloud',
            'لمعة': 'fa-diamond',
            'فحص': 'fa-check-circle',
        }

        for wc in Workcenter.search(wc_domain, order='sequence,id'):
            wc_wos = Workorder.browse([w.id for w in wc_map.get(wc.id, [])])
            in_progress_wos = wc_wos.filtered(lambda w: w.state == 'progress')
            queue_wos = wc_wos.filtered(lambda w: w.state in ('pending', 'waiting', 'ready'))
            capacity = wc.default_capacity or 1
            if capacity <= 0:
                capacity = 1

            current_cars = []
            ordered_wos = in_progress_wos + queue_wos
            seen_mos = set()
            for wo in ordered_wos:
                if wo.production_id.id in seen_mos:
                    continue
                seen_mos.add(wo.production_id.id)
                car = self._cw_mo_vehicle_payload(wo.production_id)
                car['wo_state'] = wo.state
                car['stage'] = wo.name or ''
                current_cars.append(car)
                if len(current_cars) >= 3:
                    break

            icon = 'fa-wrench'
            for fragment, mapped_icon in icon_map.items():
                if fragment in (wc.name or ''):
                    icon = mapped_icon
                    break

            workcenter_load.append({
                'id': wc.id,
                'name': wc.name or 'محطة غسيل',
                'load': len(wc_wos),
                'in_progress': len(in_progress_wos),
                'queue': len(queue_wos),
                'capacity': capacity,
                # Occupancy, not queue pressure. This intentionally avoids the old misleading 400% figure.
                'utilization': round((len(in_progress_wos) / capacity) * 100, 1),
                'queue_pressure': round((len(wc_wos) / capacity) * 100, 1),
                'icon': icon,
                'cars': current_cars,
                'domain': wo_base + [('workcenter_id', '=', wc.id)],
            })

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
                order='date_start asc', limit=8,
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
                scrap_domain += [('production_id.x_cc_is_wash_order', '=', True)] if 'x_cc_is_wash_order' in self._fields else [('production_id', '!=', False)]
            scraps = Scrap.search(scrap_domain)
            scrap_count = len(scraps)
            scrap_qty = round(sum(scraps.mapped('scrap_qty')), 2)

        station_busy = sum(1 for item in workcenter_load if item.get('in_progress'))
        station_free = sum(1 for item in workcenter_load if not item.get('load'))
        station_queue = sum(item.get('queue', 0) for item in workcenter_load)
        station_total = len(workcenter_load)
        material_reserved_count = sum(1 for item in materials if item.get('reserved', 0) > 0)
        known_plate_count = sum(1 for car in active_cars if car.get('plate') and car.get('plate') != 'بدون لوحة')
        data_quality = round((known_plate_count / len(active_cars)) * 100, 1) if active_cars else 100.0

        return {
            'dashboard_version': '5.0-concept-replica',
            'company_id': company.id,
            'company_name': company.display_name,
            'currency_symbol': company.currency_id.symbol or '',
            'station_busy': station_busy,
            'station_free': station_free,
            'station_queue': station_queue,
            'station_total': station_total,
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
            'scrap_domain': scrap_domain,
            'today_start': today_start,
            'shop_floor_action': 'mrp_workorder.action_mrp_display',
        }
