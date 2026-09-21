# -*- coding: utf-8 -*-
import logging
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools import format_amount

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = "pos.order"

    whatsapp_auto_sent = fields.Boolean(default=False, copy=False)
    whatsapp_auto_due = fields.Datetime(readonly=True, copy=False)
    whatsapp_out_id = fields.Many2one(
        "adv.whatsapp.out", string="WhatsApp Message", copy=False, readonly=True
    )

    # --- config from system params ---
    def _pos_whatsapp_conf(self):
        ICP = self.env["ir.config_parameter"].sudo()
        enabled = ICP.get_param("pos_whatsapp_auto.enabled", "1") in ("1", "true", "yes", "on")
        cc = ICP.get_param("pos_whatsapp.default_cc", "218")
        return enabled, cc

    # --- internal helpers ---
    def _get_partner_phone(self, cc="218"):
        self.ensure_one()
        phone = (self.partner_id.mobile or self.partner_id.phone or "").strip()
        if not phone:
            return False
        return self._normalize_phone_local(phone, cc)

    def _normalize_phone_local(self, phone, cc):
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0"):
            phone = phone[1:]
        if not phone.startswith("+"):
            phone = f"+{cc}{phone}"
        return phone

    # --- build WhatsApp body ---
    def _build_whatsapp_body(self):
        self.ensure_one()
        partner = self.partner_id
        company = self.company_id
        currency = self.currency_id or company.currency_id
        local_dt = fields.Datetime.context_timestamp(self, self.date_order)
        amount_txt = format_amount(self.env, self.amount_total, currency)

        # إضافة تفاصيل الأصناف
        lines = []
        for line in self.lines:
            lines.append(f"- {line.product_id.display_name} x {line.qty}")
        items_text = "\n".join(lines)

        return (
            f"🧾 إيصال عملية بيع جديدة\n\n"
            f"العميل: {partner.name or 'عميل'}\n"
            f"الطلب: {self.name}\n"
            f"الإجمالي: {amount_txt}\n"
            f"التاريخ: {local_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"تفاصيل الأصناف:\n{items_text}\n\n"
            f"شكراً لتعاملكم مع {company.name}"
        )

    # --- send WhatsApp now (manual or auto) ---
    def action_send_whatsapp_now(self):
        enabled, cc = self._pos_whatsapp_conf()
        for order in self:
            if order.whatsapp_auto_sent or not enabled:
                continue

            phone = order._get_partner_phone(cc)
            if not phone:
                _logger.info("POSWHA skip %s: no partner phone", order.name)
                continue

            body = order._build_whatsapp_body()
            AdvOut = self.env["adv.whatsapp.out"].sudo()
            vals = {
                "phone": phone,
                "type": "text",
                "body": body,
                "status": "pending",
            }
            out = AdvOut.create(vals)
            order.whatsapp_out_id = out.id
            order.whatsapp_auto_sent = True
            order.whatsapp_auto_due = fields.Datetime.now()

            try:
                out.action_send_whatsapp()
                _logger.warning(
                    "[POS WhatsApp] Sent order %s to %s (status=%s)", order.name, phone, out.status
                )
            except Exception as e:
                _logger.exception("[POS WhatsApp] Failed to send order %s: %s", order.name, e)

    # --- auto trigger on Validate ---
    def write(self, vals):
        res = super().write(vals)
        if "state" in vals and vals["state"] in ("paid", "done", "invoiced"):
            enabled, _cc = self._pos_whatsapp_conf()
            if enabled:
                for order in self:
                    if not order.whatsapp_auto_sent and order.partner_id and order._get_partner_phone(_cc):
                        try:
                            order.action_send_whatsapp_now()
                        except Exception:
                            _logger.exception("POSWHA auto send failed for %s", order.name)
        return res

    # --- cron for backfill ---
    @api.model
    def _cron_pos_whatsapp_auto(self):
        recent_since = fields.Datetime.now() - relativedelta(days=7)
        domain = [
            ("state", "in", ["paid", "done", "invoiced"]),
            ("whatsapp_auto_sent", "=", False),
            ("partner_id", "!=", False),
            ("date_order", ">=", recent_since),
        ]
        orders = self.search(domain, order="id asc", limit=100)
        _logger.info("POSWHA cron found %s orders", len(orders))
        for order in orders:
            try:
                order.action_send_whatsapp_now()
            except Exception as e:
                _logger.exception("POSWHA cron failed for %s: %s", order.name, e)
