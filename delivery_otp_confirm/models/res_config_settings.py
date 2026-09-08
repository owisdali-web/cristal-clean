# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests

API_LOGIN_URL = "https://rasael.almasafa.ly/api/MasafaRasaelLogin"

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # OTP feature toggle
    delivery_otp_enabled = fields.Boolean(
        string="Enable Delivery OTP",
        config_parameter='delivery_otp.enabled',
        default=False
    )
    delivery_otp_expiry_minutes = fields.Integer(
        string="OTP Expiry (minutes)",
        config_parameter='delivery_otp.expiry_minutes',
        default=5,
        help="Number of minutes after which the OTP expires."
    )

    # --- API credentials ---
    sms_otp_username = fields.Char(
        string="SMS API Username",
        config_parameter='vehicle_rental_sms_otp.username'
    )
    sms_otp_password = fields.Char(
        string="SMS API Password",
        config_parameter='vehicle_rental_sms_otp.password'
    )
    # Stored token (readonly)
    sms_otp_token = fields.Char(
        string="Current Token",
        config_parameter='vehicle_rental_sms_otp.token',
        readonly=True
    )

    def action_fetch_token(self):
        """Call login endpoint and save token."""
        self.ensure_one()
        if not self.sms_otp_username or not self.sms_otp_password:
            raise UserError(_("Username and password are required."))
        try:
            resp = requests.post(
                API_LOGIN_URL,
                json={
                    "username": self.sms_otp_username,
                    "password": self.sms_otp_password
                },
                timeout=30
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
        """Helper to retrieve stored token."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'vehicle_rental_sms_otp.token'
        )