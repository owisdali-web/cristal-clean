from odoo import models, api, exceptions, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.constrains('partner_id', 'session_id')
    def _check_partner_required(self):
        for rec in self:
            if rec.session_id.config_id.require_customer != 'no' \
                    and not rec.partner_id:
                raise exceptions.ValidationError(
                    _("Customer is required for this order and is missing.")
                )