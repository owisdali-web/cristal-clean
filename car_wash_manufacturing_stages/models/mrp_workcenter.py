from odoo import fields, models


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    car_wash_sequence = fields.Integer(
        string="Car Wash Sequence",
        default=10,
        help=(
            "Defines the stage order for car-wash manufacturing. "
            "Work orders on the same sequence can be processed together. "
            "A later sequence waits until all work orders from the previous "
            "used sequence of the same manufacturing order are completed."
        ),
        index=True,
    )
