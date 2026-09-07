# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    vehicle_type = fields.Selection(
        [
            ("car", "Car"),
            ("truck", "Truck"),
            ("van", "Van"),
            ("pickup", "Pickup"),
        ],
        string="Vehicle Type",
    )