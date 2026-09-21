from odoo import models, fields, api, _


class PhoneDuplicateWizard(models.TransientModel):
    _name = 'phone.duplicate.wizard'
    _description = 'Duplicate Phone Resolution Wizard'

    existing_partner_id = fields.Many2one(
        'res.partner', string='Existing Contact', readonly=True)
    current_partner_id = fields.Integer(
        string='Current Partner ID', readonly=True)
    current_partner_name = fields.Char(
        string='Current Partner Name', readonly=True)
    phone_input = fields.Char(string='Phone', readonly=True)
    message = fields.Text(
        string='Message', compute='_compute_message')

    @api.depends('existing_partner_id', 'phone_input', 'current_partner_name')
    def _compute_message(self):
        for wiz in self:
            wiz.message = _(
                "The phone number '%(phone)s' is already used by '%(existing)s'.\n\n"
                "What would you like to do?\n\n"
                "• Add as related contact — links the existing contact under "
                "the current partner's company so both can share the phone.\n"
                "• Open existing contact — jump to that record.\n"
                "• Cancel — discard the change."
            ) % {
                'phone': wiz.phone_input or '',
                'existing': wiz.existing_partner_id.name or '',
            }

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def action_link_existing(self):
        """Attach the existing partner under the current partner's company."""
        self.ensure_one()
        existing = self.existing_partner_id
        if not existing:
            return self.action_cancel()

        if not self.current_partner_id:
            return self._notify(
                _('Cannot Link'),
                _('Please save the current contact first, then try again.'),
                'warning',
            )

        current = self.env['res.partner'].browse(self.current_partner_id)
        if not current.exists():
            return self._notify(
                _('Cannot Link'),
                _('The current contact no longer exists.'),
                'warning',
            )

        # Pick the target parent:
        #   - if current is a company  -> use it as the parent
        #   - if current is a person   -> use its company (parent_id) if any,
        #                                 else fall back to the current person
        if current.is_company:
            target_parent = current
        else:
            target_parent = current.parent_id or current

        # Avoid making a record its own parent
        if existing.id == target_parent.id:
            return self._notify(
                _('Nothing to do'),
                _("'%s' is the same contact.") % existing.name,
                'info',
            )

        if existing.parent_id.id != target_parent.id:
            existing.sudo().write({'parent_id': target_parent.id})

        return self._notify(
            _('Contact Linked'),
            _("'%(child)s' is now related to '%(parent)s'.") % {
                'child': existing.name,
                'parent': target_parent.name,
            },
            'success',
        )

    def action_open_existing(self):
        """Open the existing (duplicate) contact for review."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Existing Contact'),
            'res_model': 'res.partner',
            'res_id': self.existing_partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _notify(self, title, message, level):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': level,        # 'success' | 'warning' | 'info' | 'danger'
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }