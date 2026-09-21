# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError, ValidationError
import base64

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def action_send_whatsapp(self):
        for order in self:
            partner = order.partner_id
            phone =  partner.phone
            if not phone:
                raise ValidationError('Vendor has no phone number.')
            # Create WhatsApp Out record and open the form pre-filled
            return {
                'type': 'ir.actions.act_window',
                'name': 'Send WhatsApp',
                'res_model': 'whatsapp.composer',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_phone': phone,
                    'default_body': f'Hello {partner.name}, your purchase order {order.name} is being processed.',
                }
            }

    def action_send_whatsapp_po(self):
        """
        هذه الدالة تقوم بإنشاء تقرير أمر الشراء كملف PDF وإرساله
        عبر الواتساب باستخدام المديول المخصص 'adv.whatsapp.out'.
        """
        self.ensure_one()

        if not self.partner_id.phone and not self.partner_id.mobile:
            raise UserError("There is no phone number or mobile number registered for this vendor.")

        phone_number = self.partner_id.phone
        
        # 1. نحدد اسم تقرير أمر الشراء الافتراضي
        report_template_name = 'purchase.action_report_purchase_order'
        
        # 2. نحصل على كائن التقرير
        report = self.env['ir.actions.report']._get_report_from_name(report_template_name)
        
        # ✅ الحل: نمرر اسم التقرير (report_ref) ومعرفات السجلات (res_ids)
        pdf_content, content_type = report._render_qweb_pdf(report_ref=report_template_name, res_ids=self.ids)

        # تحويل محتوى PDF إلى Base64 لإرساله
        pdf_base64 = base64.b64encode(pdf_content)

        # إنشاء اسم للملف
        filename = f"PurchaseOrder_{self.name}.pdf"

        # رسالة نصية اختيارية مع الفاتورة
        message_body = f"Hello {self.partner_id.name},\n\nAttached is a copy of purchase order {self.name}.\n\nThank you."

        # استخدام المديول 'adv.whatsapp.out' لإنشاء وإرسال الرسالة
        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': phone_number,
            'body': message_body,
            'media': pdf_base64,
            'media_filename': filename,
            'status': 'pending',
        })

        # محاولة إرسال الرسالة فورًا
        whatsapp_message.action_send_to_individual()

        # يمكنك إضافة رسالة تأكيد للمستخدم
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'نجاح',
                'message': f' Purchase Order sent to {phone_number} successfully',
                'type': 'success',
                'sticky': False,
            }
        }
