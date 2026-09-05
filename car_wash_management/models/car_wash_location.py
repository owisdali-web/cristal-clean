from odoo import models, fields, api

class CarWashLocation(models.Model):
    _name = 'car.wash.location'
    _description = 'Car Wash Location/Stage'
    _order = 'name'  # removed priority from ordering

    name = fields.Char(string='Location Name', required=True)
    capacity = fields.Integer(string='Maximum Capacity', default=10, required=True)
    is_waiting_zone = fields.Boolean(string='Waiting Zone', 
                                     help='Cars are placed here only manually when all paths are full')
    is_final_zone = fields.Boolean(string='Final/Done Zone',
                                   help='Cars placed here are considered complete')
    active = fields.Boolean(default=True)
    current_count = fields.Integer(string='Current Cars', compute='_compute_current_count', store=False)

    @api.depends('name')  # dummy depends to trigger compute on refresh
    def _compute_current_count(self):
        for loc in self:
            loc.current_count = self.env['car.wash.order'].search_count([
                ('current_location_id', '=', loc.id),
                ('state', 'in', ['draft', 'in_progress'])
            ])