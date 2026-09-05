from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CarWashOrder(models.Model):
    _name = 'car.wash.order'
    _description = 'Car Wash Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Ticket #',
                       default=lambda self: _('New'), copy=False)
    customer_name = fields.Char(string='Customer Name', required=True)
    customer_phone = fields.Char(string='Phone Number', required=True)
    car_type_id = fields.Many2one(
        'car.wash.type', string='Car Type', required=True)
    service_ids = fields.Many2many(
        'car.wash.service', string='Cleaning Services', required=True)
    current_location_id = fields.Many2one(
        'car.wash.location', string='Current Location', tracking=True)
    current_path_index = fields.Integer(string='Current Step Index', default=0)
    path_line_ids = fields.One2many(
        'order.path.line', 'order_id', string='Planned Path')
    total_price = fields.Float(
        string='Total Price', compute='_compute_total_price', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'car.wash.order') or _('New')
        order = super().create(vals)
        # Generate path after creation (order has id)
        order._generate_path()
        return order

    def write(self, vals):
        res = super().write(vals)
        # If services changed, regenerate path
        if 'service_ids' in vals:
            for order in self:
                order._generate_path()
        return res

    @api.depends('car_type_id', 'service_ids')
    def _compute_total_price(self):
        for order in self:
            total = 0.0
            if order.car_type_id and order.service_ids:
                pricelist = self.env['car.wash.pricelist'].search([
                    ('car_type_id', '=', order.car_type_id.id),
                    ('service_id', 'in', order.service_ids.ids)
                ])
                total = sum(pricelist.mapped('price'))
            order.total_price = total

    def _generate_path(self):
        """Build the merged path based on service priorities and their step sequences."""
        self.path_line_ids.unlink()
        if not self.service_ids:
            self.current_location_id = False
            self.current_path_index = 0
            return

        # Get services sorted by global sequence
        sorted_services = self.service_ids.sorted('sequence')
        combined_steps = []
        for service in sorted_services:
            for step in service.location_ids.sorted('step_sequence'):
                combined_steps.append({
                    'location_id': step.location_id.id,
                    'sequence': len(combined_steps) + 1,
                    'is_visited': False,
                })

        if not combined_steps:
            raise ValidationError(
                _("One or more selected services have no flow steps defined. Please configure them first."))

        # Create path lines
        for step_data in combined_steps:
            self.env['order.path.line'].create({
                'order_id': self.id,
                'location_id': step_data['location_id'],
                'sequence': step_data['sequence'],
                'is_visited': False,
            })

        # Assign first location with capacity, else waiting zone
        first_location = self.path_line_ids.sorted('sequence')[0].location_id
        if self._check_location_capacity(first_location):
            self.current_location_id = first_location
            self.current_path_index = 1
        else:
            wait_zone = self.env['car.wash.location'].search(
                [('is_waiting_zone', '=', True)], limit=1)
            if wait_zone and self._check_location_capacity(wait_zone):
                self.current_location_id = wait_zone
            else:
                self.current_location_id = False
            self.current_path_index = 0

    def _check_location_capacity(self, location):
        if not location:
            return False
        count = self.env['car.wash.order'].search_count([
            ('current_location_id', '=', location.id),
            ('state', 'in', ['draft', 'in_progress']),
            ('id', '!=', self.id)
        ])
        return count < location.capacity

    # ... (keep action_next_step, action_manual_override, etc. unchanged)

    def action_next_step(self):
        """Manual 'Next' button: move car to the next location in the planned path."""
        self.ensure_one()
        if self.state in ['done', 'cancelled']:
            raise UserError(_("Cannot move a completed or cancelled order."))

        next_index = self.current_path_index + 1
        next_path_line = self.path_line_ids.filtered(
            lambda p: p.sequence == next_index)
        if not next_path_line:
            # No more steps: mark as done
            done_loc = self.env['car.wash.location'].search(
                [('is_final_zone', '=', True)], limit=1)
            if done_loc and self._check_location_capacity(done_loc):
                self.current_location_id = done_loc
                self.state = 'done'
                self.current_path_index = next_index - 1  # keep it at last step
            else:
                raise UserError(
                    _("No final zone defined or it is full. Please manually override."))
            return

        next_location = next_path_line.location_id
        if not self._check_location_capacity(next_location):
            raise UserError(_("Cannot move to '%s' (Capacity is full: %s/%s). Please free a spot or use Manual Override.")
                            % (next_location.name, next_location.current_count, next_location.capacity))

        # Move the car
        self.current_location_id = next_location
        self.current_path_index = next_index
        # Mark the step as visited (optional, for visual progress)
        next_path_line.is_visited = True

        # If this is the last location, auto-complete? We'll let the user click 'Next' again to go to Done.
        if self.current_path_index == len(self.path_line_ids):
            # Last step done, next click will move to Done zone as per logic above.
            pass

    def action_manual_override(self):
        """Opens the wizard for manual location assignment."""
        return {
            'name': 'Send to Specific Location',
            'type': 'ir.actions.act_window',
            'res_model': 'manual.override.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_mark_done(self):
        """Quick action to mark as done (move to final zone)."""
        self.ensure_one()
        done_loc = self.env['car.wash.location'].search(
            [('is_final_zone', '=', True)], limit=1)
        if not done_loc:
            raise UserError(
                _("No final zone defined in the system. Please configure one."))
        if not self._check_location_capacity(done_loc):
            raise UserError(_("Final zone is full. Cannot complete."))
        self.current_location_id = done_loc
        self.state = 'done'
        # Mark all remaining path lines as visited
        self.path_line_ids.filtered(
            lambda p: not p.is_visited).write({'is_visited': True})
        self.current_path_index = len(self.path_line_ids)

    def action_reset_to_draft(self):
        """Allow resetting a cancelled/done order back to draft for re-processing."""
        self.ensure_one()
        self.state = 'draft'
        self.current_location_id = False
        self.current_path_index = 0
        self.path_line_ids.write({'is_visited': False})
