from odoo import Command, fields, models


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

    def _apply_car_wash_workorder_dependencies(self):
        """Build stage dependencies for each MO.

        This intentionally uses Odoo's standard work-order dependency field
        so the normal Ready/Waiting behavior and Shop Floor UI continue to
        work with the standard mrp.workorder model.
        """
        for production in self:
            if not production.car_wash_routing_enabled:
                continue

            workorders = production.workorder_ids.filtered(
                lambda wo: wo.state not in ("cancel",)
                and wo.workcenter_id
            )
            if not workorders:
                continue

            # Custom routing owns the dependency graph for this MO.
            # This removes the standard BOM-operation dependency chain so
            # operations in the same car-wash sequence remain parallel.
            workorders.blocked_by_workorder_ids = [Command.clear()]

            groups = {}
            for workorder in workorders:
                sequence = workorder.workcenter_id.car_wash_sequence
                groups.setdefault(sequence, self.env["mrp.workorder"])
                groups[sequence] |= workorder

            ordered_sequences = sorted(groups)

            previous_group = self.env["mrp.workorder"]
            for sequence in ordered_sequences:
                current_group = groups[sequence]

                if previous_group:
                    current_group.blocked_by_workorder_ids = [
                        Command.set(previous_group.ids)
                    ]

                previous_group = current_group

            # The dependency field drives the standard Odoo state computation.
            # Recompute it immediately for work orders created/confirmed in
            # the current transaction.
            workorders.invalidate_recordset(["state"])

    def _link_workorders_and_moves(self):
        result = super()._link_workorders_and_moves()

        custom_productions = self.filtered(
            lambda production: production.car_wash_routing_enabled
        )
        if custom_productions:
            # The standard method decides whether dependency mode is enabled
            # from the BOM. For the car-wash routing, it must be enabled even
            # when the BOM does not use Odoo's manual Operation Dependencies.
            custom_productions.write({"allow_workorder_dependencies": True})
            custom_productions._apply_car_wash_workorder_dependencies()

        return result

    def action_apply_car_wash_routing(self):
        """Manually rebuild the routing for an existing manufacturing order."""
        self.ensure_one()

        if self.state == "done":
            return True

        self.write({
            "allow_workorder_dependencies": True,
            "car_wash_routing_enabled": True,
        })
        self._link_workorders_and_moves()
        return True
