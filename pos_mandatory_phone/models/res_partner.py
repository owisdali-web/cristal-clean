import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, RedirectWarning

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('phone')
    def _check_phone_required_and_unique(self):
        for partner in self:
            # 1. Enforce Mandatory Phone for main records
            if not partner.parent_id and not partner.phone:
                raise ValidationError(_("A phone number is mandatory for all main contacts."))

            if not partner.phone:
                continue

            # 2. Normalize current input (Keep only digits)
            current_digits = re.sub(r'\D', '', partner.phone)
            if not current_digits:
                continue 

            # 3. Retrieve all other contacts to check for duplicates
            all_partners = self.search([('id', '!=', partner.id), ('phone', '!=', False)])
            
            for existing_partner in all_partners:
                existing_digits = re.sub(r'\D', '', existing_partner.phone)
                
                if current_digits == existing_digits:
                    # Look up Odoo's native layout action ID safely
                    action = self.env.ref('base.action_partner_form')
                    
                    # Instead of an inline dict, inject our destination ID into the native context registry
                    redirect_action = action.read(['name', 'type', 'res_model', 'view_mode'])[0]
                    redirect_action.update({
                        'res_id': existing_partner.id,
                        'view_mode': 'form',
                        'views': [(False, 'form')],
                        'target': 'current',
                    })

                    # Trigger the dialog window natively without breaking Javascript
                    raise RedirectWarning(
                        message=_(
                            "The phone number '%s' matches an existing contact record:\n\n"
                            "• Contact Name: %s\n"
                            "• Odoo Record ID: %s\n\n"
                            "Click the button below to view and edit that contact."
                        ) % (partner.phone, existing_partner.name, existing_partner.id),
                        action=redirect_action,
                        button_text=_("Open Existing Contact Layout")
                    )
