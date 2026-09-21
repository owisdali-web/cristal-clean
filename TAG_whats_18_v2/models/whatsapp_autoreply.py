# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WhatsappAutoreplyRule(models.Model):
    _name = 'adv.whatsapp.autoreply.rule'
    _description = 'WhatsApp Auto-Reply Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    match_type = fields.Selection([
        ('contains', 'Contains'),
        ('equals', 'Equals'),
        ('starts_with', 'Starts With'),
    ], default='contains', required=True)
    keyword = fields.Char(required=True, help="Keyword or phrase to match against the incoming message text.")
    reply_body = fields.Text(required=True, string='Reply Message')

    @api.model
    def get_reply_for_text(self, text):
        """Return the reply body of the first active rule matching the given text, or False."""
        if not text:
            return False
        text_low = text.strip().lower()
        for rule in self.search([('active', '=', True)], order='sequence, id'):
            kw = (rule.keyword or '').strip().lower()
            if not kw:
                continue
            if rule.match_type == 'equals' and text_low == kw:
                return rule.reply_body
            if rule.match_type == 'starts_with' and text_low.startswith(kw):
                return rule.reply_body
            if rule.match_type == 'contains' and kw in text_low:
                return rule.reply_body
        return False
