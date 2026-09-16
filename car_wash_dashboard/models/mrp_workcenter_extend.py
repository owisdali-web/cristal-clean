# -*- coding: utf-8 -*-
from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    car_wash_enabled = fields.Boolean(
        string='Show on Car Wash Dashboard',
        default=False,
        help='Include this work center as a physical car-wash station on the dashboard.',
    )
    car_wash_station_type = fields.Selection(
        [
            ('automatic', 'Automatic'),
            ('polishing', 'Polishing'),
            ('general', 'General'),
        ],
        string='Car Wash Station Type',
        default='general',
        required=True,
    )
    car_wash_sequence = fields.Integer(
        string='Dashboard Sequence',
        default=10,
        help='Lower numbers appear first on the car-wash dashboard.',
    )
