# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import json


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ---------------------------------------------------------
    # OTP STATUS
    # ---------------------------------------------------------

    otp_verified = fields.Boolean(
        string='OTP Verified',
        default=False,
        copy=False,
    )

    otp_skipped = fields.Boolean(
        string='OTP Skipped',
        default=False,
        copy=False,
        help='OTP requirement was bypassed by an authorized user.',
    )

    otp_ids = fields.One2many(
        'delivery.otp',
        'picking_id',
        string='OTPs',
    )

    # ---------------------------------------------------------
    # COMPUTED OTP SETTINGS
    # ---------------------------------------------------------

    delivery_otp_enabled = fields.Boolean(
        compute='_compute_delivery_otp_enabled',
        string='OTP Enabled for Deliveries',
    )

    delivery_otp_required = fields.Boolean(
        compute='_compute_delivery_otp_required',
        string='OTP Required for this Operation',
    )

    # ---------------------------------------------------------
    # OTP ENABLED
    # ---------------------------------------------------------

    def _compute_delivery_otp_enabled(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'delivery_otp.enabled',
            default='False',
        )

        enabled = str(enabled).lower() in (
            'true',
            '1',
            'yes',
        )

        for rec in self:
            rec.delivery_otp_enabled = enabled

    # ---------------------------------------------------------
    # OTP REQUIRED
    # ---------------------------------------------------------

    def _compute_delivery_otp_required(self):
        Config = self.env['ir.config_parameter'].sudo()

        enabled = Config.get_param(
            'delivery_otp.enabled',
            default='False',
        )

        enabled = str(enabled).lower() in (
            'true',
            '1',
            'yes',
        )

        # -----------------------------------------------------
        # Warehouses
        # -----------------------------------------------------

        warehouse_param = Config.get_param(
            'delivery_otp.warehouse_ids',
            default='[]',
        )

        try:
            warehouse_ids = json.loads(warehouse_param)
            warehouse_ids = [
                int(x) for x in warehouse_ids
            ]
        except Exception:
            warehouse_ids = []

        # -----------------------------------------------------
        # Operation Types
        # -----------------------------------------------------

        operation_param = Config.get_param(
            'delivery_otp.operation_type_ids',
            default='[]',
        )

        try:
            operation_type_ids = json.loads(operation_param)
            operation_type_ids = [
                int(x) for x in operation_type_ids
            ]
        except Exception:
            operation_type_ids = []

        for rec in self:

            # Default
            rec.delivery_otp_required = False

            if not enabled:
                continue

            # -------------------------------------------------
            # Find warehouse
            # -------------------------------------------------

            warehouse = (
                rec.picking_type_id.warehouse_id
                or rec.location_id.warehouse_id
            )

            if not warehouse:
                continue

            # -------------------------------------------------
            # Warehouse must match
            # -------------------------------------------------

            if warehouse_ids:
                if warehouse.id not in warehouse_ids:
                    continue
            else:
                # No warehouses selected = OTP nowhere
                continue

            # -------------------------------------------------
            # Operation type
            # -------------------------------------------------

            if operation_type_ids:

                if not rec.picking_type_id:
                    continue

                if rec.picking_type_id.id not in operation_type_ids:
                    continue

            # -------------------------------------------------
            # All conditions passed
            # -------------------------------------------------

            rec.delivery_otp_required = True

    # ---------------------------------------------------------
    # SETTINGS
    # ---------------------------------------------------------

    @api.model
    def _get_otp_settings(self):
        Config = self.env['ir.config_parameter'].sudo()

        return {
            'enabled': str(
                Config.get_param(
                    'delivery_otp.enabled',
                    default='False',
                )
            ).lower() in (
                'true',
                '1',
                'yes',
            ),

            'expiry_minutes': int(
                Config.get_param(
                    'delivery_otp.expiry_minutes',
                    default=5,
                )
            ),
        }

    # ---------------------------------------------------------
    # SEND OTP
    # ---------------------------------------------------------

    def action_send_delivery_otp(self):
        self.ensure_one()

        if not self.partner_id.phone:
            raise UserError(
                _("Customer has no phone number.")
            )

        settings = self._get_otp_settings()

        if not settings['enabled']:
            raise UserError(
                _("OTP feature is disabled in settings.")
            )

        if not self.delivery_otp_required:
            raise UserError(
                _("OTP is not required for this operation.")
            )

        # Reset previous bypass/verification state
        self.write({
            'otp_verified': False,
            'otp_skipped': False,
        })

        # Invalidate previous OTPs
        self.otp_ids.filtered(
            lambda o: o.status in (
                'pending',
                'sent',
            )
        ).write({
            'status': 'expired',
        })

        code = self.env['delivery.otp']._generate_otp(
            length=4
        )

        expiry = (
            fields.Datetime.now()
            + timedelta(
                minutes=settings['expiry_minutes']
            )
        )

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
                'message': _(
                    'A 4-digit OTP has been sent to the customer\'s phone.'
                ),
                'sticky': False,
                'type': 'success',
            },
        }

    # ---------------------------------------------------------
    # VERIFY OTP
    # ---------------------------------------------------------

    def action_verify_delivery_otp(self):
        self.ensure_one()

        otp = self.otp_ids.filtered(
            lambda o:
                o.status == 'sent'
                and o.expiry
                and o.expiry > fields.Datetime.now()
        )

        if not otp:
            raise UserError(
                _(
                    "No valid OTP found. "
                    "Please send a new one."
                )
            )

        otp = otp[0]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Verify OTP'),
            'res_model': 'delivery.otp.verify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_otp_id': otp.id,
            },
        }

    # ---------------------------------------------------------
    # SKIP OTP
    # ---------------------------------------------------------

    def action_skip_otp(self):
        """
        Allow Inventory Administrators to bypass OTP and
        continue with the normal stock validation process.
        """

        self.ensure_one()

        if not self.env.user.has_group(
            'stock.group_stock_manager'
        ):
            raise UserError(
                _(
                    "Only Inventory Administrators "
                    "can skip OTP verification."
                )
            )

        if self.state in ('done', 'cancel'):
            raise UserError(
                _("This delivery cannot be validated.")
            )

        # -----------------------------------------------------
        # Mark OTP as bypassed
        # -----------------------------------------------------

        self.write({
            'otp_skipped': True,
            'otp_verified': False,
        })

        self.message_post(
            body=_(
                "OTP verification skipped by %s."
            ) % self.env.user.name
        )

        # -----------------------------------------------------
        # IMPORTANT:
        # Continue directly into the normal Odoo validation.
        #
        # button_validate() will see otp_skipped=True and
        # allow the operation.
        # -----------------------------------------------------

        return self.button_validate()

    # ---------------------------------------------------------
    # VALIDATE
    # ---------------------------------------------------------

    def button_validate(self):
        """
        Prevent validation when OTP is required and has not
        been verified or explicitly skipped.
        """

        for picking in self:

            # -------------------------------------------------
            # OTP is not required
            # -------------------------------------------------

            if not picking.delivery_otp_required:
                continue

            # -------------------------------------------------
            # OTP was verified
            # -------------------------------------------------

            if picking.otp_verified:
                continue

            # -------------------------------------------------
            # OTP was explicitly skipped
            # -------------------------------------------------

            if picking.otp_skipped:
                continue

            # -------------------------------------------------
            # Check active OTP
            # -------------------------------------------------

            valid_otp = picking.otp_ids.filtered(
                lambda o:
                    o.status == 'sent'
                    and o.expiry
                    and o.expiry > fields.Datetime.now()
            )

            if valid_otp:
                raise UserError(
                    _(
                        "OTP has been sent but not yet verified. "
                        "Please enter the OTP to confirm delivery."
                    )
                )

            # -------------------------------------------------
            # No valid OTP
            # -------------------------------------------------

            raise UserError(
                _(
                    "OTP verification is required for this "
                    "delivery. Please send an OTP first."
                )
            )

        # -----------------------------------------------------
        # Normal Odoo validation
        # -----------------------------------------------------

        return super(StockPicking, self).button_validate()
