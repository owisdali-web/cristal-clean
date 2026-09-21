# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64


class WhatsappComposer(models.TransientModel):
    _name = 'adv.whatsapp.composer'
    _description = 'WhatsApp Message Composer'

    phone       = fields.Char(string="Phone Number", required=True)
    body        = fields.Text(string="Message Body")

    # نوع الإرسال
    send_type   = fields.Selection([
        ('text',  'نص فقط'),
        ('video', 'فيديو'),
        ('pdf',   'PDF مرفق'),
    ], string="نوع الرسالة", default='text', required=True)

    # مرفق PDF (موجود مسبقاً)
    attachment_id = fields.Many2one('ir.attachment', string="PDF Attachment")

    # فيديو
    video_file    = fields.Binary(string="الفيديو", attachment=True)
    video_filename= fields.Char(string="اسم الفيديو")

    def action_send_whatsapp_with_pdf(self):
        """إرسال رسالة واتساب حسب نوع الإرسال المختار."""
        self.ensure_one()

        vals = {
            'phone': self.phone,
            'body':  self.body or '',
        }

        if self.send_type == 'text':
            vals['type'] = 'text'

        elif self.send_type == 'video':
            if not self.video_file:
                from odoo.exceptions import UserError
                raise UserError("يرجى رفع ملف الفيديو أولاً.")
            vals.update({
                'type':           'media',
                'media':          self.video_file,
                'media_filename': self.video_filename or 'video.mp4',
            })

        elif self.send_type == 'pdf':
            if not self.attachment_id:
                from odoo.exceptions import UserError
                raise UserError("لا يوجد مرفق PDF.")
            vals.update({
                'type':           'media',
                'media':          self.attachment_id.datas,
                'media_filename': self.attachment_id.name,
            })

        msg = self.env['adv.whatsapp.out'].create(vals)
        msg.sudo().action_send_whatsapp()

        return {'type': 'ir.actions.act_window_close'}
