# -*- coding: utf-8 -*-
from odoo import models, api, fields, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    is_main = fields.Boolean(string="Main Warehouse", default=False)
    partner_id = fields.Many2one('res.partner', string="Responsible Person")


class StockAlert(models.Model):
    _name = "stock.alert"
    _description = "Automatic Stock Alerts"

    @api.model
    def check_stock_levels(self):
        """فحص مستويات المخزون وإضافة رسائل واتساب عند النقص لكل مخزن"""
        warehouses = self.env['stock.warehouse'].search([])
        orderpoints = self.env['stock.warehouse.orderpoint'].search([])

        for warehouse in warehouses:
            low_stock_products = []
            for orderpoint in orderpoints.filtered(lambda o: o.warehouse_id == warehouse):
                product = orderpoint.product_id
                min_qty = orderpoint.product_min_qty
                qty = self.env['stock.quant']._get_available_quantity(product, warehouse.lot_stock_id)
                if min_qty and qty < min_qty:
                    low_stock_products.append((product.name, qty, min_qty))

            if low_stock_products and warehouse.partner_id and warehouse.partner_id.phone:
                # إنشاء رسالة واحدة لكل المخزن تحتوي على جميع المنتجات الناقصة
                message_lines = [f"⚠️ تنبيه نقص المنتجات في {warehouse.name}:"]
                for name, qty, min_qty in low_stock_products:
                    message_lines.append(f"- {name}: الكمية المتاحة {qty}، الحد الأدنى {min_qty}")
                message_lines.append("يرجى تزويد هذه المنتجات في أقرب وقت ممكن.")
                message = "\n".join(message_lines)

                # نضيف الرسالة إلى جدول adv.whatsapp.out فقط
                self.env['adv.whatsapp.out'].create({
                    'phone': warehouse.partner_id.phone,
                    'body': message,
                })


def create_stock_alert_cron(cr, registry):
    """إنشاء Scheduled Action عند تثبيت الموديول"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron_model = env['ir.cron']

    # تحقق إذا لم يكن موجود مسبقًا
    existing = cron_model.search([('name', '=', 'Check Stock Levels WhatsApp')])
    if existing:
        return

    cron_model.create({
        'name': 'Check Stock Levels WhatsApp',      # اسم العملية
        'model_id': env.ref('your_module_name.model_stock_alert').id,
        'state': 'code',
        'code': 'model.check_stock_levels()',
        'interval_number': 1,                        # كل ساعة
        'interval_type': 'days',                     # الوحدة الزمنية: أيام بدل ساعات
        'numbercall': -1,                            # عدد مرات التنفيذ غير محدود
        'active': True,                              # نشط تلقائيًا
    })

    _logger.info("Stock Alert Cron created successfully!")
