from odoo import models, fields

class ServiceLocationLine(models.Model):
    _name = 'service.location.line'
    _description = 'Service Flow Step'
    _order = 'step_sequence'

    service_id = fields.Many2one('car.wash.service', string='Service', required=True, ondelete='cascade')
    location_id = fields.Many2one('car.wash.location', string='Location', required=True)
    step_sequence = fields.Integer(string='Step Order', default=1, required=True)