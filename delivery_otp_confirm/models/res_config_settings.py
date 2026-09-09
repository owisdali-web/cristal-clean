# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

API_LOGIN_URL = "https://rasael.almasafa.ly/api/MasafaRasaelLogin"


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    delivery_otp_enabled = fields.Boolean(
        string="Enable Delivery OTP",
        config_parameter='delivery_otp.enabled',
        default=False,
    )
    delivery_otp_expiry_minutes = fields.Integer(
        string="OTP Expiry (minutes)",
        config_parameter='delivery_otp.expiry_minutes',
        default=5,
        help="Number of minutes after which the OTP expires.",
    )

    # --- API credentials ---
    sms_otp_username = fields.Char(
        string="SMS API Username",
        config_parameter='vehicle_rental_sms_otp.username',
    )
    sms_otp_password = fields.Char(
        string="SMS API Password",
        config_parameter='vehicle_rental_sms_otp.password',
    )
    sms_otp_token = fields.Char(
        string="Current Token",
        config_parameter='vehicle_rental_sms_otp.token',
        readonly=True,
    )

    # --- OTP required operation types (no warehouses) ---
    otp_operation_type_ids = fields.Many2many(
        'stock.picking.type',
        string='OTP Required Operation Types',
        help='OTP verification will be required for these operation types. '
             'If none are selected, OTP is not required anywhere.',
    )

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'delivery_otp.operation_type_ids',
            json.dumps(self.otp_operation_type_ids.ids),
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'delivery_otp.operation_type_ids', default='[]'
        )
        try:
            operation_type_ids = json.loads(param)
        except (ValueError, TypeError):
            operation_type_ids = []
        res['otp_operation_type_ids'] = [(6, 0, operation_type_ids)]
        return res

    def action_fetch_token(self):
        self.ensure_one()
        if not self.sms_otp_username or not self.sms_otp_password:
            raise UserError(_("Username and password are required."))
        try:
            resp = requests.post(
                API_LOGIN_URL,
                json={"username": self.sms_otp_username,
                      "password": self.sms_otp_password},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            token = data.get('token')
            if not token:
                raise UserError(_("No token in response: %s", data))
            self.sms_otp_token = token
            self.env['ir.config_parameter'].sudo().set_param(
                'vehicle_rental_sms_otp.token', token
            )
        except Exception as e:
            raise UserError(_("Failed to fetch token: %s", e))

    @api.model
    def get_api_token(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'vehicle_rental_sms_otp.token'
        )