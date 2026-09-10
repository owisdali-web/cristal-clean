# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError, ValidationError
import base64

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_send_whatsapp(self):
        for order in self:
            partner = order.partner_id
            phone = partner.mobile or partner.phone
            if not phone:
                raise ValidationError('لا يوجد رقم هاتف للعميل.')
            
            message_body = f'مرحباً {partner.name}، طلبك {order.name} جارٍ معالجته.'
            
            whatsapp_message = self.env['adv.whatsapp.out'].create({
                'type': 'text',
                'phone': phone,
                'body': message_body,
                'status': 'pending',
            })
            whatsapp_message.action_send_whatsapp()

        # إظهار إشعار للمستخدم
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم الإرسال',
                'message': 'تم إرسال رسالة واتساب بنجاح ✅',
                'sticky': False,
                'type': 'success',  # success / warning / danger
            }
        }

    def action_send_whatsapp_invoice(self):
        """
        إرسال عرض السعر كملف PDF عبر الواتساب مباشرة
        """
        self.ensure_one()

        if not self.partner_id.phone and not self.partner_id.mobile:
            raise UserError("لا يوجد رقم هاتف أو جوال مسجل لهذا العميل.")

        phone_number = self.partner_id.mobile or self.partner_id.phone
        
        report_template_name = 'sale.action_report_saleorder'
        report = self.env['ir.actions.report']._get_report_from_name(report_template_name)
        pdf_content, content_type = report._render_qweb_pdf(report_ref=report_template_name, res_ids=self.ids)

        pdf_base64 = base64.b64encode(pdf_content)
        filename = f"عرض_سعر_{self.name}.pdf"

        message_body = f"مرحباً {self.partner_id.name},\n\nمرفق نسخة من عرض السعر رقم {self.name}.\n\nشكراً لك."

        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': phone_number,
            'body': message_body,
            'media': pdf_base64,
            'media_filename': filename,
            'status': 'pending',
        })
        whatsapp_message.action_send_whatsapp()

        # إظهار إشعار نجاح
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم الإرسال',
                'message': 'تم إرسال عرض السعر عبر واتساب بنجاح ✅',
                'sticky': False,
                'type': 'success',
            }
        }
