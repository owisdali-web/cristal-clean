from odoo import models, fields

class CarWashService(models.Model):
    _name = 'car.wash.service'
    _description = 'Cleaning Service Type'
    _order = 'sequence'

    name = fields.Char(string='Service Name', required=True)
    sequence = fields.Integer(string='Global Priority', default=10,
                              help='Lower number means this service is performed first')
    location_ids = fields.One2many('service.location.line', 'service_id', string='Flow Steps')
    active = fields.Boolean(default=True)