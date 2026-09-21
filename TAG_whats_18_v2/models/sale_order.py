from odoo import models, _
from odoo.exceptions import UserError
import logging
import base64

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # --------------------------------------------------
    # 1️⃣ إرسال واتساب تلقائي عند Quotation Sent
    # --------------------------------------------------
    def write(self, vals):
        res = super().write(vals)

        if vals.get('state') == 'sent':
            for order in self:
                try:
                    order._send_whatsapp_quotation_sent()
                except Exception as e:
                    _logger.exception(
                        "[WhatsApp] Failed to send quotation message for %s: %s",
                        order.name, e
                    )

        return res

    def _send_whatsapp_quotation_sent(self):
        self.ensure_one()
    
        phone = self.partner_id.phone
        if not phone:
            return
    
        message = (
            f"مرحبًا {self.partner_id.name} 👋\n\n"
            f"تم إرسال عرض السعر الخاص بك 📄\n"
            f"رقم العرض: {self.name}\n"
            f"الإجمالي: {self.amount_total:.2f} {self.currency_id.name}\n\n"
            f"نشكرك على ثقتك بنا 💚"
        )
    
        msg = self.env['adv.whatsapp.out'].sudo().create({
            'type': 'text',
            'phone': phone,
            'body': message,
            'status': 'pending',
        })
    
        # 🔥 هذا هو السطر الناقص
        msg.action_send_to_individual()

    # --------------------------------------------------
    # 2️⃣ زر إرسال واتساب يدوي
    # --------------------------------------------------
    def action_send_whatsapp(self):
        self.ensure_one()

        phone = self.partner_id.phone
        if not phone:
            raise UserError("Customer has no phone number.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'Send WhatsApp',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_phone': phone,
                'default_body': f'Hello {self.partner_id.name}, your quotation {self.name} has been sent.',
            }
        }

    # --------------------------------------------------
    # 3️⃣ زر إرسال PDF عبر واتساب
    # --------------------------------------------------
    def action_send_whatsapp_invoice(self):
        self.ensure_one()

        phone = self.partner_id.phone
        if not phone:
            raise UserError("Customer has no phone number.")

        report_name = 'sale.action_report_saleorder'
        report = self.env['ir.actions.report']._get_report_from_name(report_name)

        pdf_content, _ = report._render_qweb_pdf(
            report_ref=report_name,
            res_ids=self.ids
        )

        pdf_base64 = base64.b64encode(pdf_content)
        filename = f"Quotation_{self.name}.pdf"

        self.env['adv.whatsapp.out'].sudo().create({
            'type': 'media',
            'phone': phone,
            'body': f"Quotation {self.name}",
            'media': pdf_base64,
            'media_filename': filename,
            'status': 'pending',
        })
