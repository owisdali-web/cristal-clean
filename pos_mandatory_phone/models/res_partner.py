import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('phone')
    def _check_phone_required_and_unique(self):
        for partner in self:
            # 1. Enforce Mandatory Phone for main records (Companies or Individual People)
            # We still allow adding delivery/invoice sub-addresses without throwing errors
            if not partner.parent_id and not partner.phone:
                raise ValidationError(_("A phone number is mandatory for all main contacts."))

            if not partner.phone:
                continue

            # 2. Normalize current input (Keep only digits)
            current_digits = re.sub(r'\D', '', partner.phone)
            if not current_digits:
                continue  # Skip if phone only contains symbols like '+++'

            # 3. Retrieve all other contacts to check for digit-level duplicates
            # (Excluding current record to allow updating it cleanly)
            all_partners = self.search([('id', '!=', partner.id), ('phone', '!=', False)])
            
            for existing_partner in all_partners:
                existing_digits = re.sub(r'\D', '', existing_partner.phone)
                
                if current_digits == existing_digits:
                    raise ValidationError(_(
                        "The phone number '%s' matches an existing record:\n\n"
                        "• Contact Name: %s\n"
                        "• Odoo Record ID: %s\n\n"
                        "Please open and use the existing contact layout instead."
                    ) % (partner.phone, existing_partner.name, existing_partner.id))
