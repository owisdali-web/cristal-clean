# -*- coding: utf-8 -*-
import base64
from odoo import models
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_send_statement_whatsapp(self):
        """
        إرسال كشف الحساب للعميل نفسه عبر الواتساب
        """
        self.ensure_one()

        if not self.phone :
            raise UserError("The customer does not have a registered phone or mobile number.")

        phone_number = self.phone
        report_xml_id = 'l9n_account_customer_statements.action_customer_statements_report'

        pdf_content, content_type = self.env['ir.actions.report']._render_qweb_pdf(
            report_ref=report_xml_id,
            res_ids=self.ids
        )

        pdf_base64 = base64.b64encode(pdf_content)
        filename = f"Statement_{self.name}.pdf"
        message_body = f"Hello {self.name},\n\nPlease find attached your account statement.\n\nThank you."

        whatsapp_message = self.env['adv.whatsapp.out'].create({
            'type': 'media',
            'phone': phone_number,
            'body': message_body,
            'media': pdf_base64,
            'media_filename': filename,
            'status': 'pending',
        })

        whatsapp_message.action_send_whatsapp()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'نجاح',
                'message': f'Account Statement sent to {phone_number} successfully',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_send_statement_wizard(self):
        """
        فتح نافذة اختيار جهة اتصال أخرى لإرسال كشف الحساب لها
        """
        self.ensure_one()
        return {
            'name': 'Send Statement',
            'type': 'ir.actions.act_window',
            'res_model': 'send.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }
