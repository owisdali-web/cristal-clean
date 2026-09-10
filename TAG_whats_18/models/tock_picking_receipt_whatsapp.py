# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_whatsapp_notified = fields.Boolean(
        string='WhatsApp Notified', copy=False, index=True)
    x_whatsapp_notified_on = fields.Datetime(
        string='WhatsApp Notified On', copy=False, readonly=True)
    x_whatsapp_out_id = fields.Many2one(
        'adv.whatsapp.out', string='WhatsApp Message', copy=False, readonly=True)

    def button_validate(self):
        res = super().button_validate()
        try:
            _logger.warning("=== WhatsApp DEBUG: button_validate called for %s", self.mapped("name"))
            self._enqueue_whatsapp_receipt_notifications()
        except Exception as e:
            _logger.exception("WhatsApp notify failed in button_validate: %s", e)
        return res

    def _action_done(self):
        res = super()._action_done()
        try:
            _logger.warning("=== WhatsApp DEBUG: _action_done called for %s", self.mapped("name"))
            self._enqueue_whatsapp_receipt_notifications()
        except Exception as e:
            _logger.exception("WhatsApp notify failed in _action_done: %s", e)
        return res

    def _enqueue_whatsapp_receipt_notifications(self):
        icp = self.env['ir.config_parameter'].sudo()
        enabled = icp.get_param('tag_whatsapp.enable_receipt_notify', 'True').lower() in ('1', 'true', 'yes', 'on')
        if not enabled:
            _logger.info("[WhatsApp Notify] Disabled in system params.")
            return

        only_po = icp.get_param('tag_whatsapp.receipt_notify_only_po', 'True').lower() in ('1', 'true', 'yes', 'on')
        max_lines = int(icp.get_param('tag_whatsapp.receipt_notify_max_lines', 15))
        default_cc = icp.get_param('tag_whatsapp.default_cc', '218')
        fallback_phone = (icp.get_param('tag_whatsapp.receipt_notify_phone', '') or '').strip()

        AdvOut = self.env['adv.whatsapp.out'].sudo()

        # فلترة الاستلامات
        pickings = self.filtered(
            lambda p: p.state == 'done'
            and p.picking_type_id.code == 'incoming'
            and not p.x_whatsapp_notified
        )
        if only_po:
            pickings = pickings.filtered(lambda p: any(m.purchase_line_id for m in p.move_ids_without_package))

        for p in pickings:
            phone = ((p.picking_type_id.warehouse_id.partner_id.mobile or '').strip()
                     or fallback_phone
                     or (p.company_id.partner_id.mobile or '').strip())
            if not phone:
                _logger.warning("[WhatsApp Notify] No phone found for picking %s; skipped", p.name)
                continue

            try:
                if hasattr(AdvOut, '_normalize_phone'):
                    phone_norm = AdvOut._normalize_phone(phone)
                else:
                    phone_norm = self._normalize_phone_local(phone, default_cc)
            except Exception as e:
                _logger.warning("[WhatsApp Notify] phone normalization failed for %s: %s", phone, e)
                phone_norm = self._normalize_phone_local(phone, default_cc)

            body, attach_vals = self._build_receipt_message(p, max_lines)

            vals = {
                'phone': phone_norm,
                'type': 'text' if not attach_vals else 'media',
                'body': body if not attach_vals else False,
                'media': attach_vals['media'] if attach_vals else False,
                'media_filename': attach_vals['media_filename'] if attach_vals else False,
                'status': 'pending',
            }
            out = AdvOut.create(vals)
            p.x_whatsapp_out_id = out.id
            p.x_whatsapp_notified = True
            p.x_whatsapp_notified_on = fields.Datetime.now()

            # 🔥 إرسال الرسالة مباشرة بعد الإنشاء
            try:
                out.action_send_whatsapp()
                _logger.warning("[WhatsApp Notify] Sent message for %s to %s (status=%s)", p.name, phone_norm, out.status)
            except Exception as e:
                _logger.exception("[WhatsApp Notify] Failed to send message for %s: %s", p.name, e)

        return True

    def _normalize_phone_local(self, phone, cc):
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = phone[1:]
        if not phone.startswith("+"):
            phone = f"+{cc}{phone}"
        return phone

    def _build_receipt_message(self, picking, max_lines):
        lines = []
        for m in picking.move_ids_without_package:
            lines.append(f"- {m.product_id.display_name} — {m.product_uom_qty} {m.product_uom.name}")

        header = (
            f"📦 إشعار استلام جديد\n\n"
            f"رقم الاستلام: {picking.name}\n"
            f"التاريخ: {fields.Datetime.to_string(fields.Datetime.now())[:10]}\n\n"
            f"____________________________\n"
            f"تفاصيل الأصناف:\n"
        )

        if len(lines) <= max_lines:
            body = header + "\n".join(lines) + "\n\n شكراً لتعاملكم معنا"
            return body, None
        else:
            return (
                f"📦 إشعار استلام {picking.name}: تم إرفاق ملف المنتجات (CSV).",
                {
                    'media': b'',
                    'media_filename': f"{picking.name}.csv",
                }
            )
