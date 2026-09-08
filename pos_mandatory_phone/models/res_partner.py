from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('phone')
    def _check_phone_required_and_unique(self):
        for partner in self:
            # We skip validation for child contacts/addresses (like delivery/invoice addresses)
            # to avoid blocking operational workflows.
            if partner.parent_id:
                continue

            if not partner.phone:
                raise ValidationError(_("A phone number is mandatory for all main contacts."))

            # Search for other main contacts with the same phone number
            domain = [
                ('phone', '=', partner.phone),
                ('id', '!=', partner.id),
                ('parent_id', '=', False)
            ]
            duplicate = self.search(domain, limit=1)
            
            if duplicate:
                # Odoo v18 handles basic HTML/formatting in ValidationError messages, 
                # but standard practice is to clearly display the name and ID so the user can locate it.
                raise ValidationError(_(
                    "The phone number '%s' is already assigned to another contact: '%s' (ID: %s).\n"
                    "Please search for and open that contact instead."
                ) % (partner.phone, duplicate.name, duplicate.id))
