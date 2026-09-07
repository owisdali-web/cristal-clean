# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    license_plate = fields.Char('License Plate')
    wash_type = fields.Selection([
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('deluxe', 'Deluxe'),
    ], string='Wash Type', default='basic')

    @api.model
    def get_dashboard_data(self):
        """Return aggregated data for the dashboard with safety checks."""
        today = datetime.now().strftime('%Y-%m-%d')

        # --- KPI Calculations ---
        total_today = self.search_count([('create_date', '>=', today)])
        in_progress = self.search_count([('state', '=', 'progress')])
        done_today = self.search_count([
            ('state', '=', 'done'),
            ('date_finished', '>=', today)
        ])
        waiting = self.search_count([
            ('state', 'in', ['confirmed', 'planned']),
            ('workorder_ids', '=', False)
        ])

        # --- Phase & Workcenter Counts ---
        workorder_obj = self.env['mrp.workorder']
        workorders = workorder_obj.search([
            ('production_id.state', 'not in', ['done', 'cancel']),
            ('state', 'in', ['pending', 'progress'])
        ])

        phase_counts = {}
        for wo in workorders:
            op_name = wo.operation_id.name or 'Unknown Operation'
            phase_counts[op_name] = phase_counts.get(op_name, 0) + 1

        workcenter_counts = {}
        for wo in workorders:
            if wo.workcenter_id:
                wc_name = wo.workcenter_id.name or 'Unknown Workcenter'
                workcenter_counts[wc_name] = workcenter_counts.get(wc_name, 0) + 1

        # --- Work Center Load Calculation ---
        wc_obj = self.env['mrp.workcenter']
        all_workcenters = wc_obj.search([])
        
        # Icon mapping dictionary
        icon_map = {
            'غسيل خارجي': 'fa-car-wash',
            'غسيل داخلي': 'fa-tint',
            'تجفيف': 'fa-wind',
            'تلميع': 'fa-gem',
            'غسيل': 'fa-car',
            'default': 'fa-wrench'
        }

        workcenter_load = []  # Ensure this is always a list
        for wc in all_workcenters:
            load = workorder_obj.search_count([
                ('workcenter_id', '=', wc.id),
                ('state', 'in', ['pending', 'progress']),
                ('production_id.state', 'not in', ['done', 'cancel'])
            ])

            # Capacity Logic
            capacity = wc.default_capacity or 1
            if not capacity and wc.capacity_ids:
                capacity = wc.capacity_ids[0].capacity or 1
            if not capacity or capacity <= 0:
                capacity = 1

            utilization = round((load / capacity * 100), 1) if capacity else 0.0
            
            # Get icon, fallback to default
            icon = icon_map.get(wc.name or 'default', 'fa-wrench')

            workcenter_load.append({
                'name': wc.name or 'Unknown Workcenter',
                'load': load,
                'capacity': capacity,
                'utilization': utilization,
                'icon': icon,
            })

        # --- Timeline (Completed Orders) ---
        done_orders = self.search([
            ('state', '=', 'done'),
            ('date_finished', '>=', today)
        ], order='date_finished desc', limit=10)
        
        timeline = []
        for order in done_orders:
            timeline.append({
                'name': order.name or 'Order ' + str(order.id),
                'license_plate': order.license_plate or 'N/A',
                'completed_at': order.date_finished.strftime('%H:%M') if order.date_finished else '',
                'wash_type': order.wash_type or 'basic',
            })

        # --- Low Stock Alerts ---
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        low_stock = []  # Ensure this is always a list
        if warehouse:
            reorder_lines = self.env['stock.warehouse.orderpoint'].search([
                ('warehouse_id', '=', warehouse.id)
            ])
            for line in reorder_lines:
                product = line.product_id
                qty_available = product.qty_available
                min_qty = line.product_min_qty or 0
                if qty_available < min_qty:
                    low_stock.append({
                        'product_name': product.display_name,
                        'available': qty_available,
                        'min_qty': min_qty,
                    })

        return {
            'total_today': total_today,
            'in_progress': in_progress,
            'done_today': done_today,
            'waiting': waiting,
            'phase_counts': phase_counts or {},
            'workcenter_counts': workcenter_counts or {},
            'workcenter_load': workcenter_load or [],
            'timeline': timeline or [],
            'low_stock': low_stock or [],
        }