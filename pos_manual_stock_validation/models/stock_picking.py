from itertools import groupby

from odoo import api, models
from odoo.tools import float_is_zero


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _create_picking_from_pos_order_lines(
        self, location_dest_id, lines, picking_type, partner=False
    ):
        """Create POS transfers without automatically completing them.

        Odoo's standard POS flow creates the stock moves, marks them picked,
        and immediately calls ``_action_done()``.  This override deliberately
        stops after confirmation/reservation so the warehouse user validates
        the transfer manually, like a normal Sales delivery order.
        """
        pickings = self.env["stock.picking"]
        stockable_lines = lines.filtered(
            lambda line: line.product_id.type == "consu"
            and not float_is_zero(
                line.qty, precision_rounding=line.product_id.uom_id.rounding
            )
        )
        if not stockable_lines:
            return pickings

        positive_lines = stockable_lines.filtered(lambda line: line.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env["stock.picking"].create(
                self._prepare_picking_vals(
                    partner, picking_type, location_id, location_dest_id
                )
            )
            positive_picking._create_move_from_pos_order_lines(positive_lines)
            pickings |= positive_picking

        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env["stock.picking"].create(
                self._prepare_picking_vals(
                    partner,
                    return_picking_type,
                    location_dest_id,
                    return_location_id,
                )
            )
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            pickings |= negative_picking

        return pickings

    def _create_move_from_pos_order_lines(self, lines):
        """Create and reserve POS moves, but never mark them picked/done."""
        self.ensure_one()

        def get_grouping_key(line):
            return (
                line.product_id.id,
                tuple(sorted(line.attribute_value_ids.ids)),
            )

        lines_by_product_and_attrs = groupby(
            sorted(lines, key=get_grouping_key), key=get_grouping_key
        )
        move_vals = []
        for _group_key, grouped_lines in lines_by_product_and_attrs:
            order_lines = self.env["pos.order.line"].concat(*grouped_lines)
            move_vals.append(
                self._prepare_stock_move_vals(order_lines[0], order_lines)
            )

        moves = self.env["stock.move"].create(move_vals)
        confirmed_moves = moves._action_confirm()
        self._reserve_pos_moves_for_manual_validation(confirmed_moves, lines)
        self._link_owner_on_return_picking(lines)

    def _reserve_pos_moves_for_manual_validation(self, moves, lines):
        """Reserve stock while preserving POS-selected lots/serials.

        Untracked products use the normal stock reservation engine.  For a
        tracked product where the cashier selected lot/serial numbers, the
        selected lots are reserved explicitly.  In every case ``picked`` stays
        false, therefore pressing Validate in Inventory remains mandatory.
        """
        if not moves:
            return

        selected_lot_product_ids = set(
            lines.filtered(lambda line: line.pack_lot_ids.filtered("lot_name"))
            .mapped("product_id")
            .ids
        )

        lot_moves = moves.filtered(
            lambda move: move.product_id.id in selected_lot_product_ids
            and move.product_id.tracking != "none"
            and (
                move.picking_type_id.use_existing_lots
                or move.picking_type_id.use_create_lots
            )
        )

        if lot_moves:
            # _action_confirm() may already have reserved stock according to
            # the removal strategy. Clear those reservations before enforcing
            # the lot/serial numbers selected in POS.
            lot_moves._do_unreserve()
            lot_lines = lines.filtered(
                lambda line: line.product_id.id in lot_moves.product_id.ids
            )
            lot_moves._add_mls_related_to_order(
                lot_lines, are_qties_done=False
            )
            lot_moves._recompute_state()

        regular_moves = moves - lot_moves
        if regular_moves:
            regular_moves._action_assign()

        # Defensive guarantee: neither the move nor its lines are considered
        # picked before the warehouse user explicitly validates the transfer.
        moves.picked = False
