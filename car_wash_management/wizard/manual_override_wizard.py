from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ManualOverrideWizard(models.TransientModel):
    _name = 'manual.override.wizard'
    _description = 'Manual Override Location Selection'

    order_id = fields.Many2one('car.wash.order', string='Order', required=True)
    location_id = fields.Many2one('car.wash.location', string='Target Location', required=True)
    mark_previous_done = fields.Boolean(string='Mark skipped steps as done', default=True,
                                        help="If checked, all unvisited steps before this location will be marked as completed. "
                                             "If unchecked, the planned path index stays unchanged (use for temporary jumps).")

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            order = self.order_id
            if order.current_location_id == self.location_id:
                return {'warning': {'title': 'Warning', 'message': 'Car is already in this location.'}}
            # Check capacity
            count = self.env['car.wash.order'].search_count([
                ('current_location_id', '=', self.location_id.id),
                ('state', 'in', ['draft', 'in_progress']),
                ('id', '!=', order.id)
            ])
            if count >= self.location_id.capacity:
                return {'warning': {'title': 'Capacity Full', 'message': f'{self.location_id.name} is full ({count}/{self.location_id.capacity}).'}}

    def action_apply_override(self):
        order = self.order_id
        target = self.location_id

        # Check capacity again
        count = self.env['car.wash.order'].search_count([
            ('current_location_id', '=', target.id),
            ('state', 'in', ['draft', 'in_progress']),
            ('id', '!=', order.id)
        ])
        if count >= target.capacity:
            raise UserError(_("Cannot move: %s is full.") % target.name)

        # If target is the final zone, mark order done
        if target.is_final_zone:
            order.state = 'done'
            order.path_line_ids.filtered(lambda p: not p.is_visited).write({'is_visited': True})
            order.current_path_index = len(order.path_line_ids)
            order.current_location_id = target
            return

        # Find if this location exists in the planned path
        path_line = order.path_line_ids.filtered(lambda p: p.location_id == target)
        if path_line and self.mark_previous_done:
            # Mark all steps up to this one as visited
            max_seq = max(path_line.mapped('sequence'))
            order.path_line_ids.filtered(lambda p: p.sequence <= max_seq).write({'is_visited': True})
            order.current_path_index = max_seq
        elif path_line and not self.mark_previous_done:
            # Just move the car, don't update path index (temporary jump)
            order.current_location_id = target
            # We don't update index, so "Next" will still try the original next step.
            # To avoid confusion, we leave it as is.
            pass
        else:
            # Location not in path (e.g., "Wait" or custom). 
            # We just move it there without altering the path.
            order.current_location_id = target
            # Optionally, if target is a waiting zone, we keep the current index.

        order.current_location_id = target