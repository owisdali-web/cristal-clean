# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import UserError
import base64

class WhatsappMultiRecipientWizard(models.TransientModel):
    _name = 'whatsapp.multi.recipient.wizard'
    _description = 'WhatsApp Multi-Recipient Wizard'

    recipient_ids = fields.Many2many('res.partner', string='Recipients')
    message = fields.Text(string='Message', required=True)
    
    # حقول لتخزين معلومات المرفق
    attachment_name = fields.Char('Attachment Name')
    attachment_data = fields.Binary('Attachment Data', readonly=True) # Binary لتخزين بيانات الملف
    
    # حقول لتخزين مرجع للمستند الأصلي
    res_model = fields.Char('Related Document Model')
    res_id = fields.Integer('Related Document ID')

    # في ملف models/whatsapp_multi_recipient_wizard.py

    @api.model
    def default_get(self, fields_list):
        res = super(WhatsappMultiRecipientWizard, self).default_get(fields_list)
        context = self.env.context
        
        if context.get('active_model') == 'sale.order' and context.get('active_id'):
            sale_order = self.env['sale.order'].browse(context['active_id'])
            
            recipients = sale_order.partner_id
            manager = sale_order.user_id.partner_id
            if manager:
                recipients |= manager
            
            default_message = f"Hello {sale_order.partner_id.name},\n\nAttached is a copy of quote number {sale_order.name}.\n\nThank you."
    
            report_template_name = 'sale.action_report_saleorder'
            report = self.env['ir.actions.report']._get_report_from_name(report_template_name)
            pdf_content, _ = report._render_qweb_pdf(report_ref=report_template_name, res_ids=sale_order.ids)
            
            res.update({
                # === السطر الذي تم تصحيحه ===
                'recipient_ids': [Command.set(recipients.ids)] if recipients else False,
                
                'message': default_message,
                'res_model': 'sale.order',
                'res_id': sale_order.id,
                'attachment_name': f"Quotation_{sale_order.name}.pdf",
                'attachment_data': base64.b64encode(pdf_content),
            })
        return res


    def action_send_whatsapp_multi(self):
        """
        هذه الدالة تقوم بإرسال الرسالة مع المرفق إلى كل المستلمين.
        """
        self.ensure_one()
        if not self.recipient_ids:
            raise UserError("Please select at least one recipient.")

        for recipient in self.recipient_ids:
            phone = recipient.mobile or recipient.phone
            if not phone:
                continue 

            # استخدام الموديل 'adv.whatsapp.out' لإرسال رسالة مع وسائط
            self.env['adv.whatsapp.out'].create({
                'type': 'media', # تغيير النوع إلى 'media'
                'phone': phone,
                'body': self.message,
                'media': self.attachment_data, # تمرير بيانات الملف
                'media_filename': self.attachment_name, # تمرير اسم الملف
                'status': 'pending',
            })
        
        return {'type': 'ir.actions.act_window_close'}
