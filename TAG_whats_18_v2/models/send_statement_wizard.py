# -*- coding: utf-8 -*-
import base64
from odoo import models, fields
from odoo.exceptions import UserError

class SendStatementWizard(models.TransientModel):
    _name = 'send.statement.wizard'
    _description = 'Send Account Statement Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string="Recipient",
        required=True,
        help="Choose the contact to send the statement to."
    )

    def action_send(self):
        active_partner = self.env['res.partner'].browse(self.env.context.get('active_id'))
        recipient = self.partner_id

        if not recipient.phone and not recipient.mobile:
            raise UserError("The selected recipient does not have a registered phone or mobile number.")

        phone_number = recipient.mobile or recipient.phone
        report_xml_id = 'l9n_account_customer_statements.action_customer_statements_report'

        # توليد التقرير للعميل الأصلي (active_partner)
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
            report_ref=report_xml_id,
            res_ids=active_partner.ids
        )

        pdf_base64 = base64.b64encode(pdf_content)
        filename = f"Statement_{active_partner.name}.pdf"
        message_body = f"Hello {recipient.name},\n\nPlease find attached the account statement of {active_partner.name}."

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
