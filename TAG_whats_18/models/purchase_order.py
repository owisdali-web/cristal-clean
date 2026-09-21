# -*- coding: utf-8 -*-
from odoo import models, api
from odoo.exceptions import UserError, ValidationError
import base64

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def action_send_whatsapp(self):
        for order in self:
            partner = order.partner_id
            phone = partner.mobile or partner.phone
            if not phone:
                raise ValidationError('لا يوجد رقم هاتف للمورد.')
            # إنشاء سجل واتساب وفتح النموذج مع البيانات المعبأة مسبقًا
            return {
                'type': 'ir.actions.act_window',
                'name': 'إرسال واتساب',
                'res_model': 'whatsapp.composer',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_phone': phone,
                    'default_body': f'مرحباً {partner.name}، أمر الشراء الخاص بك {order.name} جارٍ معالجته.',
                }
            }

    def action_send_whatsapp_po(self):
        """
        هذه الدالة تقوم بإنشاء تقرير أمر الشراء كملف PDF وإرساله
        عبر الواتساب باستخدام الموديول المخصص 'adv.whatsapp.out'.
        """
        self.ensure_one()

        if not self.partner_id.phone and not self.partner_id.mobile:
            raise UserError("لا يوجد رقم هاتف أو جوال مسجل لهذا المورد.")

        phone_number = self.partner_id.mobile or self.partner_id.phone
        
        # 1. نحدد اسم تقرير أمر الشراء الافتراضي
        report_template_name = 'purchase.action_report_purchase_order'
        
        # 2. نحصل على كائن التقرير
        report = self.env['ir.actions.report']._get_report_from_name(report_template_name)
        
        # ✅ الحل: نمرر اسم التقرير (report_ref) ومعرفات السجلات (res_ids)
        pdf_content, content_type = report._render_qweb_pdf(report_ref=report_template_name, res_ids=self.ids)

        # تحويل محتوى PDF إلى Base64 لإرساله
        pdf_base64 = base64.b64encode(pdf_content)

        # إنشاء اسم للملف
        filename = f"أمر_شراء_{self.name}.pdf"

        # رسالة نصية اختيارية مع أمر الشراء
        message_body = f"مرحباً {self.partner_id.name},\n\nمرفق نسخة من أمر الشراء رقم {self.name}.\n\nشكراً لك."

        # استخدام الموديول 'adv.whatsapp.out' لإنشاء وإرسال الرسالة
        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': phone_number,
            'body': message_body,
            'media': pdf_base64,
            'media_filename': filename,
            'status': 'pending',
        })

        # محاولة إرسال الرسالة فورًا
        whatsapp_message.action_send_whatsapp()

        # إشعار نجاح للمستخدم
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم بنجاح',
                'message': f'تم إرسال أمر الشراء إلى {phone_number} بنجاح ✅',
                'type': 'success',
                'sticky': False,
            }
        }
