from odoo import models
from odoo.exceptions import ValidationError
import base64


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_send_whatsapp(self):
        for inv in self:
            partner = inv.partner_id
            phone =  partner.phone
            if not phone:
                raise ValidationError('Customer has no phone number.')
            return {
                'type': 'ir.actions.act_window',
                'name': 'Send WhatsApp',
                'res_model': 'whatsapp.composer',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_phone': phone,
                    'default_body': f'Hello {partner.name}, your invoice {inv.name} is ready.',
                }
            }
    def action_send_whatsapp_account(self):
        """
        هذه الدالة تقوم بإنشاء تقرير الفاتورة كملف PDF وإرساله
        عبر الواتساب باستخدام المديول المخصص 'adv.whatsapp.out'.
        """
        self.ensure_one()

        if not self.partner_id.phone :
            raise UserError("There is no phone number or mobile number registered for this customer.")

        phone_number = self.partner_id.phone
        
        # 1. نحدد اسم التقرير
        # 1. نحدد اسم التقرير الصحيح
        report_template_name = 'account.account_invoices'
        
        # 2. نحصل على كائن التقرير
        report = self.env['ir.actions.report']._get_report_from_name(report_template_name)
        
        # ✅ الحل: نمرر اسم التقرير (report_ref) ومعرفات السجلات (res_ids)
        pdf_content, content_type = report._render_qweb_pdf(report_ref=report_template_name, res_ids=self.ids)

        # تحويل محتوى PDF إلى Base64 لإرساله
        pdf_base64 = base64.b64encode(pdf_content)

        # إنشاء اسم للملف
        filename = f"Quotation_{self.name}.pdf"

        # رسالة نصية اختيارية مع الفاتورة
        message_body = f"Hello {self.partner_id.name},\n\nAttached is a copy of payment receip {self.name}.\n\nThank you."

        # استخدام المديول 'adv.whatsapp.out' لإنشاء وإرسال الرسالة
        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': phone_number,
            'body': message_body,
            'media': pdf_base64,
            'media_filename': filename,
            'status': 'pending',
        })      
