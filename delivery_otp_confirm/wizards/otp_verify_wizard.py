# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DeliveryOtpVerifyWizard(models.TransientModel):
    _name = 'delivery.otp.verify.wizard'
    _description = 'Verify Delivery OTP Wizard'

    otp_id = fields.Many2one('delivery.otp', string='OTP', required=True)
    code = fields.Char(string='OTP Code', required=True, size=10)

    # Regular field (NOT related) — populated by default_get.
    # This ensures the full field-metadata payload is sent to the client,
    # so the standard Field wrapper does not receive an undefined `field` prop.
    expiry = fields.Datetime(string='Expiry Time', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        otp_id = self.env.context.get('default_otp_id')
        if otp_id:
            otp = self.env['delivery.otp'].browse(otp_id)
            if otp.exists():
                res['expiry'] = otp.expiry
        return res

    def action_verify(self):
        self.ensure_one()
        if not self.code:
            from odoo.exceptions import UserError
            raise UserError(_("Please enter the OTP code."))
        self.otp_id.verify_code(self.code)
        return {
            'type': 'ir.actions.act_window_close',
            'effect': {
                'fadeout': 'slow',
                'message': _('OTP verified successfully!'),
                'type': 'rainbow_man',
            }
        }