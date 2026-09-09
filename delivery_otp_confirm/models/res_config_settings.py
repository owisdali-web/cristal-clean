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
    # ---------------------------------------------------------
    # OTP REQUIRED WAREHOUSES
    # ---------------------------------------------------------

    otp_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='OTP Required Warehouses',
        help=(
            'OTP verification will be required only for '
            'operations from these warehouses.'
        ),
    )

    # ---------------------------------------------------------
    # OTP REQUIRED OPERATION TYPES
    # ---------------------------------------------------------

    otp_operation_type_ids = fields.Many2many(
        'stock.picking.type',
        string='OTP Required Operation Types',
        help=(
            'OTP verification will be required only for '
            'these operation types. '
            'If no operation types are selected, '
            'all operation types in the selected warehouses '
            'will require OTP.'
        ),
    )

    def set_values(self):
        super(ResConfigSettings, self).set_values()

        Config = self.env['ir.config_parameter'].sudo()

        # Warehouses
        Config.set_param(
            'delivery_otp.warehouse_ids',
            json.dumps(self.otp_warehouse_ids.ids)
        )

        # Operation types
        Config.set_param(
            'delivery_otp.operation_type_ids',
            json.dumps(self.otp_operation_type_ids.ids)
        )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        Config = self.env['ir.config_parameter'].sudo()

        # -----------------------------------------------------
        # Warehouses
        # -----------------------------------------------------

        warehouse_param = Config.get_param(
            'delivery_otp.warehouse_ids',
            default='[]'
        )

        try:
            warehouse_ids = json.loads(warehouse_param)
        except Exception:
            warehouse_ids = []

        res['otp_warehouse_ids'] = [
            (6, 0, warehouse_ids)
        ]

        # -----------------------------------------------------
        # Operation Types
        # -----------------------------------------------------

        operation_param = Config.get_param(
            'delivery_otp.operation_type_ids',
            default='[]'
        )

        try:
            operation_type_ids = json.loads(
                operation_param
            )
        except Exception:
            operation_type_ids = []

        res['otp_operation_type_ids'] = [
            (6, 0, operation_type_ids)
        ]

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
