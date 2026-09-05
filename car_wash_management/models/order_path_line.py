from odoo import models, fields

class OrderPathLine(models.Model):
    _name = 'order.path.line'
    _description = 'Planned Path per Order'
    _order = 'sequence'

    order_id = fields.Many2one('car.wash.order', string='Order', required=True, ondelete='cascade')
    location_id = fields.Many2one('car.wash.location', string='Location', required=True)
    sequence = fields.Integer(string='Step #', required=True)
    is_visited = fields.Boolean(string='Visited', default=False)