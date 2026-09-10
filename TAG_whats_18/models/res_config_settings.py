# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


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
