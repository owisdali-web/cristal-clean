# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    vehicle_type = fields.Selection(
        [
            ("car", "سيارة"),
            ("truck", "شاحنة"),
            ("van", "فان"),
            ("pickup", "بيك أب"),
        ],
        string="Vehicle Type",
    )