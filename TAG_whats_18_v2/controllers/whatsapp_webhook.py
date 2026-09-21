# -*- coding: utf-8 -*-
import logging
import re

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WhatsappWebhookController(http.Controller):
    """Receives inbound messages and status updates pushed by Wasender API.

    Wasender must be configured to POST JSON to /whatsapp/webhook, including
    the token configured in Settings > WhatsApp either as header
    'X-Webhook-Token' or as query string '?token=...'.
    """

    def _check_token(self):
        icp = request.env['ir.config_parameter'].sudo()
        expected = icp.get_param('tag_whatsapp.webhook_token')
        if not expected:
            # No token configured: accept everything (not recommended, but avoids locking
            # the integration out before the admin has set one up).
            return True
        got = request.httprequest.headers.get('X-Webhook-Token') or request.httprequest.args.get('token')
        return got == expected

    @staticmethod
    def _normalize_digits(raw):
        if not raw:
            return False
        digits = re.sub(r'\D', '', str(raw))
        return digits or False

    def _extract_message(self, payload):
        """Best-effort normalization of the various Wasender webhook payload shapes."""
        data = payload.get('data') or payload
        msg = data.get('messages') or data.get('message') or data

        key = msg.get('key') or {}
        from_me = key.get('fromMe', msg.get('fromMe', False))
        remote_jid = key.get('remoteJid') or msg.get('from') or msg.get('sender') or data.get('from')
        phone = self._normalize_digits((remote_jid or '').split('@')[0]) if remote_jid else False

        message_obj = msg.get('message') or {}
        text = (
            message_obj.get('conversation')
            or (message_obj.get('extendedTextMessage') or {}).get('text')
            or msg.get('text')
            or msg.get('body')
            or ''
        )

        media_url = (
            msg.get('mediaUrl') or msg.get('imageUrl') or msg.get('videoUrl')
            or msg.get('documentUrl') or msg.get('audioUrl') or False
        )

        wa_message_id = key.get('id') or msg.get('id') or msg.get('msgId')

        return {
            'from_me': bool(from_me),
            'phone': phone,
            'text': text,
            'media_url': media_url,
            'wa_message_id': wa_message_id,
        }

    @http.route('/whatsapp/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        payload = request.get_json_data() if hasattr(request, 'get_json_data') else (request.jsonrequest or {})
        _logger.info("[WhatsApp Webhook] Payload received: %s", payload)

        if not self._check_token():
            _logger.warning("[WhatsApp Webhook] Rejected: invalid or missing token")
            return {'success': False, 'error': 'invalid_token'}

        event = payload.get('event') or (payload.get('data') or {}).get('event') or ''
        if event and 'message' not in event and 'upsert' not in event:
            # Status / ack / other events - nothing to store for now.
            return {'success': True, 'ignored': event}

        try:
            parsed = self._extract_message(payload)
        except Exception:
            _logger.exception("[WhatsApp Webhook] Failed to parse payload")
            return {'success': False, 'error': 'parse_error'}

        if parsed['from_me'] or not parsed['phone']:
            return {'success': True, 'skipped': True}

        Message = request.env['adv.whatsapp.out'].sudo()
        record = Message.create_incoming_message(
            phone_plain=parsed['phone'],
            body=parsed['text'],
            wa_message_id=parsed['wa_message_id'],
            media_url=parsed['media_url'],
        )

        self._maybe_autoreply(record, parsed)
        return {'success': True, 'id': record.id}

    def _maybe_autoreply(self, record, parsed):
        icp = request.env['ir.config_parameter'].sudo()
        if icp.get_param('tag_whatsapp.autoreply_enabled') != 'True':
            return
        reply_body = request.env['adv.whatsapp.autoreply.rule'].sudo().get_reply_for_text(parsed['text'])
        if not reply_body:
            return
        Message = request.env['adv.whatsapp.out'].sudo()
        reply = Message.create({
            'direction': 'out',
            'recipient_type': 'individual',
            'phone': parsed['phone'],
            'body': reply_body,
            'type': 'text',
            'partner_id': record.partner_id.id if record.partner_id else False,
        })
        reply.action_send_to_individual()
