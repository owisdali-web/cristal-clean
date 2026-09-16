from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    cc_dashboard_theme = fields.Selection(
        selection=[('dark', 'داكن'), ('light', 'فاتح')],
        string='Crystal Clean Dashboard Theme',
        default='dark',
    )
