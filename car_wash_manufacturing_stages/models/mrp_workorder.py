from odoo import _, models
from odoo.exceptions import UserError


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def _car_wash_blocking_workorders(self):
        self.ensure_one()
        if not self.production_id.car_wash_routing_enabled:
            return self.browse()
        return self.blocked_by_workorder_ids.filtered(
            lambda wo: wo.state not in ("done", "cancel")
        )

    def _check_car_wash_blocking(self):
        if self.env.context.get("car_wash_skip_check"):
            return
        for workorder in self:
            # Work orders processed together in the same call don't block each other.
            blocking = workorder._car_wash_blocking_workorders() - self
            if blocking:
                raise UserError(_(
                    "You cannot process '%(wo)s' (%(mo)s) yet.\n"
                    "These operations must be finished first:\n%(blocking)s",
                    wo=workorder.name,
                    mo=workorder.production_id.name,
                    blocking="\n".join(
                        f"- {wo.name} ({wo.workcenter_id.name} / {wo.production_id.name})"
                        for wo in blocking
                    ),
                ))

    def _car_wash_sync_state(self):
        """Mirror the standard pending logic explicitly (works across MOs)."""
        for workorder in self.with_context(car_wash_skip_check=True):
            if workorder.state not in ("pending", "waiting", "ready"):
                continue
            if workorder._car_wash_blocking_workorders():
                if workorder.state != "pending":
                    workorder.state = "pending"
            elif workorder.state == "pending":
                workorder.state = (
                    "ready"
                    if workorder.production_id.reservation_state == "assigned"
                    else "waiting"
                )

    def _car_wash_refresh_dependents(self):
        dependents = self.search([("blocked_by_workorder_ids", "in", self.ids)])
        dependents._car_wash_sync_state()

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------
    def button_start(self, *args, **kwargs):
        self._check_car_wash_blocking()
        return super().button_start(*args, **kwargs)

    def button_finish(self, *args, **kwargs):
        self._check_car_wash_blocking()
        return super().button_finish(*args, **kwargs)

    def write(self, vals):
        if vals.get("state") in ("progress", "done"):
            self._check_car_wash_blocking()
        result = super().write(vals)
        if vals.get("state") in ("done", "cancel"):
            self._car_wash_refresh_dependents()
        return result