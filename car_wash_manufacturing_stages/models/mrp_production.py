import logging

from odoo import Command, fields, models

_logger = logging.getLogger(__name__)

ACTIVE_MO_STATES = ("confirmed", "progress", "to_close")


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    car_wash_routing_enabled = fields.Boolean(
        string="Car Wash Work Center Sequencing",
        default=True,
        copy=True,
    )
    car_wash_ref = fields.Char(
        string="Car Wash Visit",
        index=True,
        copy=False,
        help=(
            "Manufacturing orders with the same visit reference are treated "
            "as one car. If empty, the Source document is used, "
            "otherwise the MO reference."
        ),
    )

    # -------------------------------------------------------------------------
    # Visit grouping
    # -------------------------------------------------------------------------
    def _get_car_wash_key(self):
        self.ensure_one()
        return self.car_wash_ref or self.origin or self.name

    def _get_car_wash_visit_productions(self):
        """All active, enabled MOs that belong to the same car visits as self."""
        keys = {production._get_car_wash_key() for production in self}
        if not keys:
            return self.browse()
        keys = list(keys)
        candidates = self.search([
            ("car_wash_routing_enabled", "=", True),
            ("state", "in", ACTIVE_MO_STATES),
            ("company_id", "in", self.company_id.ids),
            "|", "|",
            ("car_wash_ref", "in", keys),
            ("origin", "in", keys),
            ("name", "in", keys),
        ])
        return candidates.filtered(lambda p: p._get_car_wash_key() in keys)

    # -------------------------------------------------------------------------
    # Core logic
    # -------------------------------------------------------------------------
    def _apply_car_wash_workorder_dependencies(self):
        WorkOrder = self.env["mrp.workorder"]

        # MOs where routing was disabled: remove their dependencies.
        disabled = self.filtered(lambda p: not p.car_wash_routing_enabled)
        if disabled:
            disabled_wos = disabled.workorder_ids.filtered(
                lambda wo: wo.state not in ("done", "cancel")
            )
            disabled_wos.write({"blocked_by_workorder_ids": [Command.clear()]})
            disabled_wos._car_wash_sync_state()

        visits = {}
        for production in self._get_car_wash_visit_productions():
            key = production._get_car_wash_key()
            visits.setdefault(key, self.browse())
            visits[key] |= production

        for key, visit in visits.items():
            workorders = visit.workorder_ids.filtered(
                lambda wo: wo.state != "cancel" and wo.workcenter_id
            )
            if not workorders:
                continue

            visit.filtered(
                lambda p: not p.allow_workorder_dependencies
            ).write({"allow_workorder_dependencies": True})

            # Our routing owns the dependency graph of the whole visit.
            workorders.write({"blocked_by_workorder_ids": [Command.clear()]})

            groups = {}
            for workorder in workorders:
                sequence = workorder.workcenter_id.car_wash_sequence
                groups.setdefault(sequence, WorkOrder)
                groups[sequence] |= workorder

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

            workorders._car_wash_sync_state()

            _logger.info(
                "Car wash routing applied on visit %s: %s",
                key,
                [
                    (
                        wo.production_id.name,
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
        productions = self.filtered(lambda p: p.state in ACTIVE_MO_STATES)
        if productions:
            productions._apply_car_wash_workorder_dependencies()

    # -------------------------------------------------------------------------
    # Standard overrides
    # -------------------------------------------------------------------------
    def _link_workorders_and_moves(self):
        result = super()._link_workorders_and_moves()
        self._prepare_car_wash_routing()
        return result

    def action_confirm(self):
        result = super().action_confirm()
        self._prepare_car_wash_routing()
        return result

    def write(self, vals):
        result = super().write(vals)
        if {"car_wash_ref", "car_wash_routing_enabled"} & set(vals):
            self._prepare_car_wash_routing()
        return result

    # -------------------------------------------------------------------------
    # Button
    # -------------------------------------------------------------------------
    def action_apply_car_wash_routing(self):
        self.ensure_one()
        if self.state in ("done", "cancel"):
            return True
        if not self.car_wash_routing_enabled:
            self.car_wash_routing_enabled = True
        self._prepare_car_wash_routing()
        return True