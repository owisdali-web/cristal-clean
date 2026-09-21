import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, RedirectWarning


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('phone')
    def _check_phone_required_and_unique(self):
        for partner in self:
            # 1. Mandatory phone for main contacts
            if not partner.parent_id and not partner.phone:
                raise ValidationError(
                    _("A phone number is mandatory for all main contacts.")
                )

            if not partner.phone:
                continue

            # 2. Normalize (digits only)
            current_digits = re.sub(r'\D', '', partner.phone)
            if not current_digits:
                continue

            # 3. Look for duplicates
            others = self.search([
                ('id', '!=', partner.id),
                ('phone', '!=', False),
            ])
            for existing in others:
                existing_digits = re.sub(r'\D', '', existing.phone or '')
                if existing_digits != current_digits:
                    continue

                # If both partners are already in the same company hierarchy,
                # sharing a phone is fine (e.g. employees of one branch).
                if self._same_company_hierarchy(partner, existing):
                    continue

                # 4. Route the user to the resolve wizard (multiple buttons!)
                action = {
                    'type': 'ir.actions.act_window',
                    'name': _('Duplicate Phone Detected'),
                    'res_model': 'phone.duplicate.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_existing_partner_id': existing.id,
                        'default_current_partner_id':
                            partner.id if isinstance(partner.id, int) else False,
                        'default_phone_input': partner.phone,
                        'default_current_partner_name': partner.name or '',
                    },
                }
                raise RedirectWarning(
                    message=_(
                        "The phone number '%s' is already used by '%s'.\n\n"
                        "Choose an action to resolve this conflict."
                    ) % (partner.phone, existing.name),
                    action=action,
                    button_text=_('Resolve Conflict'),
                )
                # only report the first duplicate
                break

    @api.model
    def _same_company_hierarchy(self, p1, p2):
        """True if both partners belong to the same company tree."""
        def get_root(partner):
            seen = set()
            while partner.parent_id and partner.id not in seen:
                seen.add(partner.id)
                partner = partner.parent_id
            return partner
        return get_root(p1) == get_root(p2)