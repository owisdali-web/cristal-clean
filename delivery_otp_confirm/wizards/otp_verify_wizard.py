# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DeliveryOtpVerifyWizard(models.TransientModel):
    _name = 'delivery.otp.verify.wizard'
    _description = 'Verify Delivery OTP Wizard'

    otp_id = fields.Many2one('delivery.otp', string='OTP', required=True)
    code = fields.Char(string='OTP Code', required=True, size=10)

    def action_verify(self):
        self.ensure_one()
        if not self.code:
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