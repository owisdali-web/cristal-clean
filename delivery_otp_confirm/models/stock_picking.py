# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    otp_verified = fields.Boolean(
        string='OTP Verified', default=False, copy=False)
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

    # ------------------------------------------------------------------
    #  Shared helper: create (or reset) an OTP record for this picking
    # ------------------------------------------------------------------
    def _create_delivery_otp(self):
        """Create a fresh OTP for this picking and return the delivery.otp record."""
        self.ensure_one()
        settings = self._get_otp_settings()

        if not settings['enabled']:
            raise UserError(_("OTP feature is disabled in settings."))
        if not self.delivery_otp_required:
            raise UserError(_("OTP is not required for this operation."))
        if not self.partner_id.phone:
            raise UserError(_("Customer has no phone number."))

        # reset previous state
        self.write({'otp_verified': False, 'otp_skipped': False})
        self.otp_ids.filtered(lambda o: o.status in ('pending', 'sent')).write(
            {'status': 'expired'}
        )

        code = self.env['delivery.otp']._generate_otp(length=4)
        expiry = fields.Datetime.now(
        ) + timedelta(minutes=settings['expiry_minutes'])

        otp = self.env['delivery.otp'].create({
            'picking_id': self.id,
            'phone': self.partner_id.phone,
            'code': code,
            'expiry': expiry,
            'status': 'pending',
        })
        return otp, settings

    # ------------------------------------------------------------------
    #  Existing: Send OTP via SMS
    # ------------------------------------------------------------------


def action_send_delivery_otp(self):
    self.ensure_one()
    channel = self.env['ir.config_parameter'].sudo().get_param(
        'delivery_otp.send_channel', 'sms'
    )
    if channel == 'whatsapp':
        return self.action_send_delivery_otp_whatsapp()

    otp, _settings = self._create_delivery_otp()
    otp.send_otp()

    if otp.status == 'sent':
        notif_type = 'success'
        notif_msg = _(
            "A 4-digit OTP has been sent to the customer's phone via SMS.")
    else:
        notif_type = 'danger'
        notif_msg = _("SMS send failed: %s") % (otp.last_error or '')

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': _('OTP SMS'),
            'message': notif_msg,
            'sticky': False,
            'type': notif_type,
        },
    }

    # ------------------------------------------------------------------
    #  NEW: Send OTP via WhatsApp (using adv.whatsapp.out from TAG_whats_18)
    # ------------------------------------------------------------------
    def action_send_delivery_otp_whatsapp(self):
        self.ensure_one()

        if 'adv.whatsapp.out' not in self.env:
            raise UserError(_(
                "WhatsApp module (TAG_whats_18) is not installed. "
                "Please install it to use this feature."
            ))

        otp, settings = self._create_delivery_otp()

        # Build message (same wording as SMS)
        message = _(
            "Your delivery confirmation code is: %s. It will expire in %d minutes."
        ) % (otp.code, settings['expiry_minutes'])

        # Create outgoing WhatsApp message record
        wa_out = self.env['adv.whatsapp.out'].sudo().create({
            'phone': self.partner_id.phone,
            'type': 'text',
            'body': message,
            'status': 'pending',
        })

        try:
            wa_out.action_send_whatsapp()
        except Exception as e:
            _logger.exception(
                "Delivery OTP WhatsApp send failed for picking %s", self.name)
            otp.status = 'failed'
            otp.last_error = str(e)
            raise UserError(_("Failed to send OTP via WhatsApp: %s") % e)

        if wa_out.status == 'sent':
            otp.status = 'sent'
            otp.last_error = False
            notif_type = 'success'
            notif_msg = _(
                "A 4-digit OTP has been sent to the customer's phone via WhatsApp.")
        else:
            otp.status = 'failed'
            otp.last_error = wa_out.last_error or _("WhatsApp send failed.")
            notif_type = 'danger'
            notif_msg = _("WhatsApp send failed: %s") % (
                wa_out.last_error or '')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OTP WhatsApp'),
                'message': notif_msg,
                'sticky': False,
                'type': notif_type,
            },
        }

    # ------------------------------------------------------------------
    #  Verification wizard (unchanged)
    # ------------------------------------------------------------------
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
            raise UserError(
                _("Only Inventory Administrators can skip OTP verification."))
        if self.state in ('done', 'cancel'):
            raise UserError(_("This delivery has already been processed."))

        self.otp_skipped = True
        self.message_post(
            body=_("OTP verification skipped by %s.", self.env.user.name))
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
