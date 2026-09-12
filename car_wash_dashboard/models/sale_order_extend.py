# -*- coding: utf-8 -*-

from odoo import fields, models


WASH_METHODS = [
    ("automatic", "غسيل آلي"),
    ("manual", "غسيل يدوي"),
]


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

    wash_method = fields.Selection(
        WASH_METHODS,
        string="نوع الغسيل",
        index=True,
        help="التصنيف التشغيلي المعتمد للغسيل الآلي أو اليدوي. لا يتم افتراض قيمة للسجلات القديمة.",
    )

    def write(self, vals):
        res = super().write(vals)
        if (
            "wash_method" in vals
            and not self.env.context.get("cw_sync_wash_method")
            and "mrp.production" in self.env
        ):
            productions = self.env["mrp.production"].search([
                ("sale_line_id.order_id", "in", self.ids),
            ])
            if productions:
                productions.with_context(cw_sync_wash_method=True).write({
                    "wash_method": vals.get("wash_method") or False,
                })
        return res
