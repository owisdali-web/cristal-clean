# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    otp_verified = fields.Boolean(string='OTP Verified', default=False, copy=False)
    otp_ids = fields.One2many('delivery.otp', 'picking_id', string='OTPs')

    delivery_otp_enabled = fields.Boolean(
        compute='_compute_delivery_otp_enabled',
        string='OTP Enabled for Deliveries'
    )

    def _compute_delivery_otp_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'delivery_otp.enabled', default='False'
        )
        enabled = enabled.lower() in ('true', '1', 'yes')
        for rec in self:
            rec.delivery_otp_enabled = enabled

    @api.model
    def _get_otp_settings(self):
        Config = self.env['ir.config_parameter'].sudo()
        return {
            'enabled': Config.get_param('delivery_otp.enabled', default='False').lower() in ('true', '1', 'yes'),
            'expiry_minutes': int(Config.get_param('delivery_otp.expiry_minutes', default=5)),
        }

    def action_send_delivery_otp(self):
        self.ensure_one()
        if not self.partner_id.phone:
            raise UserError(_("Customer has no phone number."))

        settings = self._get_otp_settings()
        if not settings['enabled']:
            raise UserError(_("OTP feature is disabled in settings."))

        # Invalidate previous pending OTPs
        self.otp_ids.filtered(lambda o: o.status in ['pending', 'sent']).write({'status': 'expired'})

        code = self.env['delivery.otp']._generate_otp(length=4)
        expiry = fields.Datetime.now() + timedelta(minutes=settings['expiry_minutes'])
        otp = self.env['delivery.otp'].create({
            'picking_id': self.id,
            'phone': self.partner_id.phone,
            'code': code,
            'expiry': expiry,
            'status': 'pending',
        })
        otp.send_otp()
        return {
            'type': 'ir.actions.act_window',
            'name': _('OTP Sent'),
            'res_model': 'delivery.otp',
            'res_id': otp.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_verify_delivery_otp(self):
        self.ensure_one()
        otp = self.otp_ids.filtered(lambda o: o.status == 'sent' and o.expiry > fields.Datetime.now())
        if not otp:
            raise UserError(_("No valid OTP found. Please send a new one."))
        otp = otp[0]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Verify OTP'),
            'res_model': 'delivery.otp.verify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_otp_id': otp.id},
        }

    def button_validate(self):
        for picking in self:
            if self._get_otp_settings()['enabled'] and not picking.otp_verified:
                valid_otp = picking.otp_ids.filtered(
                    lambda o: o.status == 'sent' and o.expiry > fields.Datetime.now()
                )
                if valid_otp:
                    raise UserError(_(
                        "OTP has been sent but not yet verified. Please enter the OTP to confirm delivery."
                    ))
                else:
                    raise UserError(_(
                        "OTP verification is required for this delivery. Please send an OTP first."
                    ))
        return super(StockPicking, self).button_validate()