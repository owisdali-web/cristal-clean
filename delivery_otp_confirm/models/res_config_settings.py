# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json

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
    sms_otp_token = fields.Char(
        string="Current Token",
        config_parameter='vehicle_rental_sms_otp.token',
        readonly=True
    )

    # --- Warehouse selection ---
    otp_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='OTP Required Warehouses',
        help="OTP verification will be required only for deliveries from these warehouses."
    )

    def set_values(self):
        """Save m2m warehouse IDs as a JSON string in ir.config_parameter."""
        super(ResConfigSettings, self).set_values()
        # Save the m2m
        warehouse_ids = self.otp_warehouse_ids.ids
        self.env['ir.config_parameter'].sudo().set_param(
            'delivery_otp.warehouse_ids',
            json.dumps(warehouse_ids)
        )

    @api.model
    def get_values(self):
        """Load m2m warehouse IDs from ir.config_parameter."""
        res = super(ResConfigSettings, self).get_values()
        # Load warehouse IDs
        param = self.env['ir.config_parameter'].sudo().get_param(
            'delivery_otp.warehouse_ids', default='[]'
        )
        try:
            ids = json.loads(param)
        except:
            ids = []
        # Set the field value (m2m requires a list of ids)
        res['otp_warehouse_ids'] = [(6, 0, ids)]  # replace with these ids
        return res

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
        return self.env['ir.config_parameter'].sudo().get_param(
            'vehicle_rental_sms_otp.token'
        )