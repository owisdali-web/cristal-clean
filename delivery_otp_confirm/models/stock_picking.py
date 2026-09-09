# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import json


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    otp_verified = fields.Boolean(string='OTP Verified', default=False, copy=False)
    otp_skipped = fields.Boolean(
        string='OTP Skipped', default=False, copy=False,
        help='OTP requirement was bypassed by an authorized user.',
    )
    otp_ids = fields.One2many('delivery.otp', 'picking_id', string='OTPs')

    delivery_otp_required = fields.Boolean(
        compute='_compute_delivery_otp_required',
        string='OTP Required for this Operation',
    )

    @api.depends('picking_type_id')
    def _compute_delivery_otp_required(self):
        Config = self.env['ir.config_parameter'].sudo()
        enabled = str(Config.get_param('delivery_otp.enabled', 'False')).lower() \
            in ('true', '1', 'yes')

        try:
            operation_type_ids = [
                int(x) for x in json.loads(
                    Config.get_param('delivery_otp.operation_type_ids', '[]')
                )
            ]
        except (ValueError, TypeError):
            operation_type_ids = []

        for rec in self:
            rec.delivery_otp_required = bool(
                enabled
                and operation_type_ids
                and rec.picking_type_id.id in operation_type_ids
            )

    @api.model
    def _get_otp_settings(self):
        Config = self.env['ir.config_parameter'].sudo()
        return {
            'enabled': str(Config.get_param('delivery_otp.enabled', 'False')).lower()
                       in ('true', '1', 'yes'),
            'expiry_minutes': int(Config.get_param('delivery_otp.expiry_minutes', 5)),
        }

    def action_send_delivery_otp(self):
        self.ensure_one()
        if not self.partner_id.phone:
            raise UserError(_("Customer has no phone number."))

        settings = self._get_otp_settings()
        if not settings['enabled']:
            raise UserError(_("OTP feature is disabled in settings."))
        if not self.delivery_otp_required:
            raise UserError(_("OTP is not required for this operation."))

        self.write({'otp_verified': False, 'otp_skipped': False})
        self.otp_ids.filtered(lambda o: o.status in ('pending', 'sent')).write(
            {'status': 'expired'}
        )

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
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OTP Sent'),
                'message': _("A 4-digit OTP has been sent to the customer's phone."),
                'sticky': False,
                'type': 'success',
            },
        }

    def action_verify_delivery_otp(self):
        self.ensure_one()
        otp = self.otp_ids.filtered(
            lambda o: o.status == 'sent' and o.expiry and o.expiry > fields.Datetime.now()
        )
        if not otp:
            raise UserError(_("No valid OTP found. Please send a new one."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Verify OTP'),
            'res_model': 'delivery.otp.verify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_otp_id': otp[0].id},
        }

    def action_skip_otp(self):
        """Bypass OTP (Inventory Admins only) then continue normal validation."""
        self.ensure_one()
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_("Only Inventory Administrators can skip OTP verification."))
        if self.state in ('done', 'cancel'):
            raise UserError(_("This delivery has already been processed."))

        self.otp_skipped = True
        self.message_post(body=_("OTP verification skipped by %s.", self.env.user.name))
        # button_validate() will now pass because otp_skipped is True.
        return self.button_validate()

    def button_validate(self):
        for picking in self:
            if not picking.delivery_otp_required:
                continue
            if picking.otp_verified or picking.otp_skipped:
                continue

            valid_otp = picking.otp_ids.filtered(
                lambda o: o.status == 'sent' and o.expiry
                and o.expiry > fields.Datetime.now()
            )
            if valid_otp:
                raise UserError(_(
                    "OTP has been sent but not yet verified. "
                    "Please enter the OTP to confirm delivery."
                ))
            raise UserError(_(
                "OTP verification is required for this delivery. "
                "Please send an OTP first."
            ))
        return super().button_validate()