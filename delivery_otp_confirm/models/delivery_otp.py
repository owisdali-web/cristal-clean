# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import random
import logging
import requests
from datetime import timedelta

_logger = logging.getLogger(__name__)

API_SEND_URL = "https://rasael.almasafa.ly/api/sms/Send"

class DeliveryOtp(models.Model):
    _name = 'delivery.otp'
    _description = 'Delivery OTP'
    _order = 'create_date desc'

    picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True, ondelete='cascade')
    phone = fields.Char(string='Phone Number', required=True)
    code = fields.Char(string='OTP Code', required=True, size=10)
    expiry = fields.Datetime(string='Expiry Time', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
        ('failed', 'Failed')
    ], string='Status', default='pending', tracking=True)
    attempts = fields.Integer(string='Verification Attempts', default=0)
    last_error = fields.Text(string='Last Error')

    @api.model
    def _generate_otp(self, length=4):
        """Generate a numeric OTP of given length."""
        return ''.join(random.choices('0123456789', k=length))

    @api.model
    def _get_token(self):
        """Retrieve the SMS API token from settings."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'vehicle_rental_sms_otp.token'
        )

    @api.model
    def _normalize_phone(self, phone):
        """Normalize phone number (Libya format)."""
        import re
        if not phone:
            raise ValidationError(_("Phone number is required."))
        digits = re.sub(r'\D', '', phone.strip())
        if len(digits) < 6:
            raise ValidationError(_("Phone number too short."))
        if not digits.startswith('218'):
            digits = '218' + digits.lstrip('0')
        return digits

    def send_otp(self):
        """Send the OTP via SMS API."""
        self.ensure_one()
        if self.status == 'verified':
            raise UserError(_("This OTP has already been verified."))

        token = self._get_token()
        if not token:
            raise UserError(_("SMS token not configured. Please set it in Settings."))

        phone = self._normalize_phone(self.phone)
        expiry_minutes = int(self.env['ir.config_parameter'].sudo().get_param(
            'delivery_otp.expiry_minutes', default=5
        ))
        message = _("Your delivery confirmation code is: %s. It will expire in %d minutes.") % (
            self.code, expiry_minutes
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "phoneNumber": phone,
            "message": message,
            "senderID": ""
        }

        try:
            resp = requests.post(API_SEND_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                resp_data = resp.json()
                if resp_data.get('success') or resp_data.get('status') == 'success':
                    self.status = 'sent'
                    self.last_error = False
                    _logger.info("OTP sent to %s", phone)
                else:
                    self.status = 'failed'
                    self.last_error = str(resp_data)
                    _logger.error("OTP send failed: %s", resp_data)
            else:
                self.status = 'failed'
                self.last_error = f"{resp.status_code}: {resp.text}"
        except Exception as e:
            self.status = 'failed'
            self.last_error = str(e)
            _logger.exception("OTP send exception")

    def verify_code(self, input_code):
        """Verify the provided code against this OTP record."""
        self.ensure_one()
        self.attempts += 1

        if self.status == 'verified':
            raise UserError(_("OTP already verified."))
        if self.status == 'expired' or (self.expiry and fields.Datetime.now() > self.expiry):
            self.status = 'expired'
            raise UserError(_("OTP has expired. Please request a new one."))
        if self.code != input_code:
            if self.attempts >= 5:
                self.status = 'expired'
                raise UserError(_("Too many failed attempts. OTP invalidated."))
            raise UserError(_("Incorrect OTP. Please try again."))

        self.status = 'verified'
        self.picking_id.otp_verified = True
        return True