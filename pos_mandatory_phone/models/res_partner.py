import re
from odoo import models, api, _
from odoo.exceptions import ValidationError, RedirectWarning


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _normalize_phone(self, phone):
        return re.sub(r'\D', '', phone or '')

    @api.model
    def find_partner_by_phone(self, phone):
        """
        RPC used by the POS front-end.
        Returns a light dict {id, name, phone, email} for the first
        partner whose phone (digits only) matches `phone`, else False.
        """
        digits = self._normalize_phone(phone)
        if not digits:
            return False

        # PostgreSQL-specific but very fast and does exactly what we want
        self.env.cr.execute(
            """
            SELECT id
              FROM res_partner
             WHERE REGEXP_REPLACE(COALESCE(phone, ''), '[^0-9]', '', 'g') = %s
             LIMIT 1
            """,
            (digits,),
        )
        row = self.env.cr.fetchone()
        if not row:
            return False

        partner = self.browse(row[0])
        return {
            'id': partner.id,
            'name': partner.name,
            'phone': partner.phone or '',
            'email': partner.email or '',
        }

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('phone')
    def _check_phone_required_and_unique(self):
        # POS handles duplicates in JS with a nicer dialog.  If a caller
        # explicitly wants to bypass the check it can pass this context.
        if self.env.context.get('skip_phone_unique_check'):
            return

        for partner in self:
            # 1. Mandatory phone for main contacts
            if not partner.parent_id and not partner.phone:
                raise ValidationError(
                    _("A phone number is mandatory for all main contacts.")
                )

            if not partner.phone:
                continue

            current_digits = self._normalize_phone(partner.phone)
            if not current_digits:
                continue

            # 2. Search for duplicates (digits-only comparison)
            all_partners = self.search(
                [('id', '!=', partner.id), ('phone', '!=', False)]
            )
            for existing_partner in all_partners:
                if self._normalize_phone(existing_partner.phone) == current_digits:
                    action = self.env.ref('base.action_partner_form')
                    redirect_action = action.read(
                        ['name', 'type', 'res_model', 'view_mode']
                    )[0]
                    redirect_action.update({
                        'res_id': existing_partner.id,
                        'view_mode': 'form',
                        'views': [(False, 'form')],
                        'target': 'current',
                    })
                    raise RedirectWarning(
                        message=_(
                            "The phone number '%s' matches an existing contact record:\n\n"
                            "• Contact Name: %s\n"
                            "• Odoo Record ID: %s\n\n"
                            "Click the button below to view and edit that contact."
                        ) % (partner.phone, existing_partner.name, existing_partner.id),
                        action=redirect_action,
                        button_text=_("Open Existing Contact Layout"),
                    )