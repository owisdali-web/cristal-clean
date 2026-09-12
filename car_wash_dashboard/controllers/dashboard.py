# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class DashboardController(http.Controller):

    @http.route('/car_wash/dashboard_data', type='json', auth='user')
    def dashboard_data(self):
        """Return aggregated data for the dashboard."""
        production_obj = request.env['mrp.production']
        return production_obj.get_dashboard_data()