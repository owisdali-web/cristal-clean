# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_webhook_token = fields.Char(
        string='Webhook Verification Token',
        config_parameter='tag_whatsapp.webhook_token',
        help="Shared secret Wasender must send back as 'X-Webhook-Token' header or '?token=' "
             "query parameter when calling the webhook URL below.",
    )
    whatsapp_autoreply_enabled = fields.Boolean(
        string='Enable Auto-Reply',
        config_parameter='tag_whatsapp.autoreply_enabled',
        default=False,
        help="When enabled, incoming messages are matched against the Auto-Reply Rules "
             "and answered automatically.",
    )
    whatsapp_webhook_url = fields.Char(string='Webhook URL', compute='_compute_whatsapp_webhook_url')

    @api.depends_context('uid')
    def _compute_whatsapp_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for rec in self:
            rec.whatsapp_webhook_url = f"{base_url}/whatsapp/webhook"

    enable_receipt_notify = fields.Boolean(
        string='Enable Receipt WhatsApp Notifications',
        config_parameter='tag_whatsapp.enable_receipt_notify',
        default=True,
    )
    receipt_notify_only_po = fields.Boolean(
        string='Only for PO-related Receipts',
        config_parameter='tag_whatsapp.receipt_notify_only_po',
        default=True,
    )
    receipt_notify_max_lines = fields.Integer(
        string='Max Lines before Attachment',
        config_parameter='tag_whatsapp.receipt_notify_max_lines',
        default=150,
    )
    receipt_notify_phone = fields.Char(
        string='Fallback Phone Number',
        config_parameter='tag_whatsapp.receipt_notify_phone',
    )
