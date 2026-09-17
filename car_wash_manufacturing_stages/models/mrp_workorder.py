from odoo import _, models
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _check_car_wash_blocking(self):
        for workorder in self:
            if not workorder.production_id.car_wash_routing_enabled:
                continue
            blocking = workorder.blocked_by_workorder_ids.filtered(
                lambda wo: wo.state not in ("done", "cancel")
            )
            if blocking:
                raise UserError(_(
                    "You cannot start '%(wo)s' yet. "
                    "These operations must be finished first: %(blocking)s",
                    wo=workorder.name,
                    blocking=", ".join(blocking.mapped("name")),
                ))

    def button_start(self, *args, **kwargs):
        self._check_car_wash_blocking()
        return super().button_start(*args, **kwargs)