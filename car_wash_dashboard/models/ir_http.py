from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        """Expose this addon's OWL/JavaScript translations to the web client."""
        modules = list(super()._get_translation_frontend_modules_name())
        if 'car_wash_dashboard' not in modules:
            modules.append('car_wash_dashboard')
        return modules
