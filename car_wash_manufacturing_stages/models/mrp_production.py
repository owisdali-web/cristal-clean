import logging

from odoo import Command, fields, models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    car_wash_routing_enabled = fields.Boolean(
        string="Car Wash Work Center Sequencing",
        default=True,
        copy=True,
        help=(
            "When enabled, work orders are grouped by the Car Wash Sequence "
            "of their work centers. Work orders with the same sequence can "
            "start together. A later sequence is blocked until every work "
            "order in the previous used sequence is completed."
        ),
    )

    # -------------------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------------------
    def _apply_car_wash_workorder_dependencies(self):
        """Build stage dependencies for each MO using the standard
        blocked_by_workorder_ids field, so Odoo's normal
        Waiting/Ready behavior and the Shop Floor keep working."""
        WorkOrder = self.env["mrp.workorder"]

        for production in self:
            if not production.car_wash_routing_enabled:
                continue

            workorders = production.workorder_ids.filtered(
                lambda wo: wo.state != "cancel" and wo.workcenter_id
            )
            if not workorders:
                continue

            # Our routing owns the dependency graph of this MO:
            # drop the standard BoM-operation chain first.
            workorders.write({"blocked_by_workorder_ids": [Command.clear()]})

            # Group work orders by car wash sequence.
            groups = {}
            for workorder in workorders:
                sequence = workorder.workcenter_id.car_wash_sequence
                groups.setdefault(sequence, WorkOrder)
                groups[sequence] |= workorder

            # Each group is blocked by ALL work orders of the previous group.
            previous_group = WorkOrder
            for sequence in sorted(groups):
                current_group = groups[sequence]
                if previous_group:
                    current_group.write({
                        "blocked_by_workorder_ids": [
                            Command.set(previous_group.ids)
                        ],
                    })
                previous_group = current_group

            # Force recomputation of the stored state field.
            state_field = WorkOrder._fields["state"]
            self.env.add_to_compute(state_field, workorders)
            workorders.flush_recordset(["state", "blocked_by_workorder_ids"])

            _logger.info(
                "Car wash routing applied on %s: %s",
                production.name,
                [
                    (
                        wo.name,
                        wo.workcenter_id.name,
                        wo.workcenter_id.car_wash_sequence,
                        wo.state,
                        wo.blocked_by_workorder_ids.mapped("name"),
                    )
                    for wo in workorders
                ],
            )

    def _prepare_car_wash_routing(self):
        """Enable dependency mode and rebuild the routing."""
        productions = self.filtered(
            lambda p: p.car_wash_routing_enabled
            and p.state not in ("done", "cancel")
        )
        if not productions:
            return
        productions.filtered(
            lambda p: not p.allow_workorder_dependencies
        ).write({"allow_workorder_dependencies": True})
        productions._apply_car_wash_workorder_dependencies()

    # -------------------------------------------------------------------------
    # Standard overrides
    # -------------------------------------------------------------------------
    def _link_workorders_and_moves(self):
        result = super()._link_workorders_and_moves()
        # Standard code rebuilds dependencies from the BoM;
        # re-apply the car wash routing on top of it.
        self._prepare_car_wash_routing()
        return result

    def action_confirm(self):
        result = super().action_confirm()
        # Safety net: make sure the routing exists after confirmation,
        # whatever path the standard confirmation took.
        self._prepare_car_wash_routing()
        return result

    # -------------------------------------------------------------------------
    # Button
    # -------------------------------------------------------------------------
    def action_apply_car_wash_routing(self):
        """Manually rebuild the routing for an existing manufacturing order."""
        self.ensure_one()
        if self.state in ("done", "cancel"):
            return True

        if not self.car_wash_routing_enabled:
            self.car_wash_routing_enabled = True
        self._prepare_car_wash_routing()
        return True