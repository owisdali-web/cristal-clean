from odoo import models, fields

class CarWashType(models.Model):
    _name = 'car.wash.type'
    _description = 'Car Type'

    name = fields.Char(string='Car Type', required=True)
    active = fields.Boolean(default=True)
    pricelist_ids = fields.One2many('car.wash.pricelist', 'car_type_id', string='Pricing Matrix')