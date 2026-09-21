from odoo import models, api, fields


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    # تمييز المخزن الرئيسي
    is_main = fields.Boolean(string="Main Warehouse", default=False)

    # ربط مخزن بشخص (شريك) لإرسال الرسائل إليه
    partner_id = fields.Many2one(
        'res.partner',
        string="Responsible Person"
    )


class StockAlert(models.Model):
    _name = "stock.alert"
    _description = "Automatic Stock Alerts"

    @api.model
    def check_stock_levels(self):
        """فحص مستويات المخزون وإرسال رسالة واتساب عند النقص"""

        products = self.env['product.product'].search([])
        warehouses = self.env['stock.warehouse'].search([])
        orderpoints = self.env['stock.warehouse.orderpoint'].search([])

        # تحديد المخزن الرئيسي
        main_warehouse = self.env['stock.warehouse'].search([('is_main', '=', True)], limit=1)
        if not main_warehouse:
            return

        for orderpoint in orderpoints:
            product = orderpoint.product_id
            min_qty = orderpoint.product_min_qty
            warehouse = orderpoint.warehouse_id

            # الشرط: لازم يكون فيه حد أدنى
            if not min_qty or warehouse.is_main:
                continue

            qty = self.env['stock.quant']._get_available_quantity(product, warehouse.lot_stock_id)

            if qty < min_qty:
                message = (
                    f"⚠️ المنتج {product.name} "
                    f"نفذ أو نقص في {warehouse.name}. "
                    f"يرجى تزويده من {main_warehouse.name}."
                )

                # إرسال رسالة للمسؤول عن المخزن الرئيسي
                if main_warehouse.partner_id and main_warehouse.partner_id.phone:
                    self.env['adv.whatsapp.out'].create({
                        'phone': main_warehouse.partner_id.phone,
                        'body': message,
                    }).action_send_whatsapp()
