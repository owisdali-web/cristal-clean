from odoo import models
from odoo.exceptions import ValidationError
import base64
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_send_whatsapp_payment(self):
        for payment in self:
            partner = payment.partner_id
            phone =  partner.phone
            if not phone:
                raise ValidationError("Customer has no phone number.")
            
            amount = payment.amount
            currency = payment.currency_id.name
            message = f"Dear {partner.name}, we have received your payment of {amount} {currency}. Thank you!"

            return {
                'type': 'ir.actions.act_window',
                'name': 'Send WhatsApp',
                'res_model': 'whatsapp.composer',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_phone': phone,
                    'default_body': message,
                    'default_type': 'text',
                }
            }
            
    def action_send_whatsapp_payment(self):
        """
        هذه الدالة تقوم بإنشاء تقرير الفاتورة كملف PDF وإرساله
        عبر الواتساب باستخدام المديول المخصص 'adv.whatsapp.out'.
        """
        self.ensure_one()

        if not self.partner_id.phone and not self.partner_id.mobile:
            raise UserError("There is no phone number or mobile number registered for this customer.")

        phone_number = self.partner_id.phone
        
        # 1. نحدد اسم التقرير
        report_template_name = 'account.action_report_payment_receipt'
        
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
