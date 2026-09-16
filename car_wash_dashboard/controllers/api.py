# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class CarWashApiController(http.Controller):

    @http.route('/car_wash/management/data', type='json', auth='user', methods=['POST'])
    def management_data(self):
        return request.env['mrp.production'].get_management_data()

    @http.route('/car_wash/materials/data', type='json', auth='user', methods=['POST'])
    def materials_data(self):
        return request.env['mrp.production'].get_materials_data()

    @http.route('/car_wash/customers/data', type='json', auth='user', methods=['POST'])
    def customers_data(self):
        return request.env['mrp.production'].get_customers_data()

    @http.route('/car_wash/team/data', type='json', auth='user', methods=['POST'])
    def team_data(self):
        return request.env['mrp.production'].get_team_data()

    @http.route('/car_wash/customer_display/data', type='json', auth='user', methods=['POST'])
    def customer_display_data(self):
        """Return the V17 sanitized waiting-room display contract."""
        return request.env['mrp.production'].get_customer_display_data()

    @http.route('/car_wash/customer_display/logo', type='http', auth='user', methods=['GET'], csrf=False)
    def customer_display_logo(self, **kwargs):
        """Serve only the current company's logo to an authorized display session."""
        Production = request.env['mrp.production']
        Production._cw_require_customer_display_access()
        company = request.env.company.sudo()
        if not company.logo:
            return request.not_found()

        try:
            payload = base64.b64decode(company.logo)
        except Exception:
            return request.not_found()

        if payload.startswith(b'\x89PNG\r\n\x1a\n'):
            content_type = 'image/png'
        elif payload.startswith(b'\xff\xd8\xff'):
            content_type = 'image/jpeg'
        elif payload.startswith(b'GIF87a') or payload.startswith(b'GIF89a'):
            content_type = 'image/gif'
        elif payload.startswith(b'RIFF') and payload[8:12] == b'WEBP':
            content_type = 'image/webp'
        else:
            content_type = 'application/octet-stream'

        return request.make_response(payload, headers=[
            ('Content-Type', content_type),
            ('Cache-Control', 'private, max-age=300'),
            ('X-Content-Type-Options', 'nosniff'),
        ])
