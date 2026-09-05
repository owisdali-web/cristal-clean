from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CarWashPricelist(models.Model):
    _name = 'car.wash.pricelist'
    _description = 'Car Wash Pricing Matrix'
    _rec_name = 'display_name'

    car_type_id = fields.Many2one('car.wash.type', string='Car Type', required=True)
    service_id = fields.Many2one('car.wash.service', string='Service', required=True)
    price = fields.Float(string='Price', required=True, default=0.0)

    display_name = fields.Char(compute='_compute_display_name', store=False)

    @api.depends('car_type_id', 'service_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.car_type_id.name} - {rec.service_id.name}"

    _sql_constraints = [
        ('unique_car_service', 'unique(car_type_id, service_id)', 'This pricing combination already exists!')
    ]