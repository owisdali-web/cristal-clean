# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WhatsappComposer(models.TransientModel):
    _name = 'whatsapp.composer'
    _description = 'WhatsApp Message Composer'

    # --- الحقول التي ستظهر في النافذة ---
    phone = fields.Char(string="Phone Number", required=True)
    body = fields.Text(string="Message Body")
    
    # --- حقل تقني لحفظ مرجع المرفق ---
    attachment_id = fields.Many2one('ir.attachment', string="attachment")

    def action_send_whatsapp_with_pdf(self):
        """
        هذه هي الدالة التي سيستدعيها زر "إرسال" في النافذة المنبثقة.
        """
        self.ensure_one()
        
        # إنشاء سجل الرسالة النهائية في adv.whatsapp.out
        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': self.phone,
            'body': self.body,
            'media': self.attachment_id.datas, # نحصل على بيانات PDF من المرفق
            'media_filename': self.attachment_id.name,
        })
        
        # محاولة إرسال الرسالة فورًا
        whatsapp_message.action_send_whatsapp()
        
        # إغلاق النافذة المنبثقة
        return {'type': 'ir.actions.act_window_close'}
