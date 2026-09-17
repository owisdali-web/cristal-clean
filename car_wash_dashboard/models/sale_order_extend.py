# -*- coding: utf-8 -*-

from odoo import fields, models


VEHICLE_SIZE_SELECTION = [
    ('small', 'Small'),
    ('large', 'Large'),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Legacy vehicle category used by the existing project. Keep it untouched.
    vehicle_type = fields.Selection(
        [
            ('car', 'سيارة'),
            ('truck', 'شاحنة'),
            ('van', 'فان'),
            ('pickup', 'بيك أب'),
        ],
        string='Vehicle Type',
    )

    # Explicit operational size for the car-wash workflow. This intentionally
    # does not infer Small/Large from vehicle_type; the business meaning is
    # different and must be chosen explicitly.
    car_wash_vehicle_size = fields.Selection(
        VEHICLE_SIZE_SELECTION,
        string='Car Wash Vehicle Size',
        help='Operational car-wash size used by the station dashboard.',
    )
