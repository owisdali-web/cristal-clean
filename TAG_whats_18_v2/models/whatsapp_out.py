# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import re
import base64
from datetime import timedelta
import logging
import mimetypes

_logger = logging.getLogger(__name__)


API_URL = "https://wasenderapi.com/api/send-message" 
UPLOAD_URL = "https://www.wasenderapi.com/api/upload"
HARDCODED_API_KEY = "ebc42cdec0e1ebf86ab219ae2308574952e4ac99197925898a8439916ea4e69e"

class WhatsappOut(models.Model):
    _name = 'adv.whatsapp.out'
    _description = 'WhatsApp out message'

    type = fields.Selection([
        ('text', 'Text Message'),
        ('media', 'Media Message'),
    ], default='text')

    # ✅ الحقول الجديدة - يجب إضافتها هنا أولاً
    recipient_type = fields.Selection([
        ('individual', 'Individual'),
        ('group', 'Group'),
    ], default='individual', string='Recipient Type')
    
    phone = fields.Char()  # أصبح اختياريًا
    group_id = fields.Char(string='Group ID')  # حقل جديد
 
    
    body = fields.Text()
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], default='pending', tracking=True)

    media = fields.Binary("Media File", attachment=True)
    media_filename = fields.Char("Media Filename")
    attempts = fields.Integer(default=0)
    next_try = fields.Datetime()
    last_error = fields.Text()

    # ---- Chat / dashboard support ----
    direction = fields.Selection([
        ('out', 'Outbound'),
        ('in', 'Inbound'),
    ], default='out', required=True, index=True, string='Direction')

    wa_message_id = fields.Char(string='WhatsApp Message ID', index=True, copy=False,
                                 help="External message id returned by Wasender API, used to match "
                                      "delivery/read status updates and avoid duplicate inbound messages.")
    partner_id = fields.Many2one('res.partner', string='Contact', index=True,
                                  help="Contact this message thread belongs to, matched by phone number.")
    message_datetime = fields.Datetime(string='Message Date', default=fields.Datetime.now, index=True)
    is_read = fields.Boolean(default=True, string='Read',
                              help="Unchecked for inbound messages not yet opened in the Chat view.")

    @api.model
    def _api_key(self):
        icp = self.env['ir.config_parameter'].sudo()
        return icp.get_param('tag_whatsapp.was_api_key') or HARDCODED_API_KEY

    def _normalize_phone(self, phone: str) -> str:
        if not phone:
            raise ValidationError("Phone number is required.")
        p = phone.strip()
        trans_map = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
        digits = re.sub(r"\D", "", p.translate(trans_map))
        if digits.startswith("0"):
            cc = self.env['ir.config_parameter'].sudo().get_param('tag_whatsapp.default_cc')
            if not cc:
                raise ValidationError("Local number detected. Set default country code in System Parameters.")
            digits = cc + digits.lstrip("0")
        if len(digits) < 6:
            raise ValidationError("Phone number too short after normalization.")
        return digits

    def _upload_media_file(self, media_data, filename):
        """Upload media file to Wasender API and return the public URL."""
        try:
            media_data_string = media_data.decode('utf-8')
            
            # تحديد نوع الملف (MIME type) ديناميكياً بناءً على اسم الملف
            mime_type, _ = mimetypes.guess_type(filename)
            
            # إذا لم يتمكن من التعرف عليه، نضع قيماً افتراضية شائعة
            if not mime_type:
                ext = filename.lower().split('.')[-1] if filename else ''
                if ext in ['mp4']:
                    mime_type = 'video/mp4'
                elif ext in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                elif ext in ['png']:
                    mime_type = 'image/png'
                elif ext in ['pdf']:
                    mime_type = 'application/pdf'
                else:
                    mime_type = 'application/octet-stream'

            # استخدام النوع الصحيح بدلاً من النوع الثابت
            full_base64_string = f"data:{mime_type};base64,{media_data_string}"
            
            headers = {
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "base64": full_base64_string
            }

            resp = requests.post(UPLOAD_URL, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                response_data = resp.json()
                if response_data.get('success'):
                    return response_data.get('publicUrl')
                else:
                    error_message = response_data.get('error', 'Unknown error from Wasender')
                    raise ValidationError(f"Upload failed: {error_message}")
            else:
                raise ValidationError(f"Upload failed with status {resp.status_code}: {resp.text}")
                
        except Exception as e:
            raise ValidationError(f"Error during media file upload: {str(e)}")

    def action_send_to_individual(self):
        """Send WhatsApp message to an individual phone number."""
        for rec in self:
            try:
                rec.attempts += 1
                phone_plain = self._normalize_phone(rec.phone)
                text = (rec.body or "").strip()

                headers = {
                    "Authorization": f"Bearer {self._api_key()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                payload = {"to": phone_plain}

                # Check if this is a media message
                if rec.type == 'media' and rec.media and rec.media_filename:
                    media_url = self._upload_media_file(rec.media, rec.media_filename)
                    ext = rec.media_filename.lower().split('.')[-1] if rec.media_filename else ''

                    if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt']:
                        payload.update({"documentUrl": media_url, "fileName": rec.media_filename})
                    elif ext in ['jpg', 'jpeg', 'png', 'gif']:
                        payload.update({"imageUrl": media_url})
                    elif ext in ['mp4', 'avi', 'mov']:
                        payload.update({"videoUrl": media_url})
                    elif ext in ['mp3', 'wav', 'ogg']:
                        payload.update({"audioUrl": media_url})
                    else:
                        payload.update({"documentUrl": media_url, "fileName": rec.media_filename})

                    if text:
                        payload["text"] = text
                else:
                    # Text only
                    if not text:
                        raise ValidationError("Text message cannot be empty.")
                    payload["text"] = text

                _logger.info("[WhatsApp API] Sending to Individual ID=%s to=%s type=%s", rec.id, phone_plain, rec.type)

                resp = requests.post(API_URL, json=payload, headers=headers, timeout=20)

                if resp.status_code == 200:
                    resp_json = resp.json()
                    if resp_json.get("success"):
                        rec.status = 'sent'
                        rec.next_try = False
                        rec.last_error = False
                        rec.wa_message_id = rec._extract_wa_message_id(resp_json)
                        if not rec.partner_id:
                            rec.partner_id = rec._find_partner_by_phone(phone_plain)
                        _logger.info("[WhatsApp API] ✅ Sent to Individual ID=%s to=%s", rec.id, phone_plain)
                    else:
                        rec.status = 'failed'
                        rec.last_error = str(resp_json)
                        _logger.error("[WhatsApp API] ❌ Failed ID=%s response=%s", rec.id, resp_json)

                elif resp.status_code == 429:  # Too many requests
                    retry_after = int(resp.json().get("retry_after") or 60)
                    rec.status = 'pending'
                    rec.next_try = fields.Datetime.now() + timedelta(seconds=retry_after)
                    rec.last_error = f"Rate limited. Retry after {retry_after}s"
                    _logger.warning("[WhatsApp API] ⏳ Rate limited for ID=%s. Retry after %s seconds", rec.id,
                                    retry_after)

                else:
                    rec.status = 'failed'
                    rec.last_error = f"{resp.status_code}: {resp.text}"
                    _logger.error("[WhatsApp API] ❌ HTTP error for ID=%s code=%s resp=%s", rec.id,
                                  resp.status_code, resp.text)

            except Exception as e:
                rec.status = 'failed'
                rec.last_error = str(e)
                _logger.exception("[WhatsApp API] ❌ Exception for ID=%s: %s", rec.id, e)

    def action_send_to_group(self):
        """Send WhatsApp message to a group using Group ID."""
        for rec in self:
            try:
                rec.attempts += 1
                
                # Validate Group ID
                group_id = rec.phone.strip()
                if not group_id:
                    raise ValidationError("Group ID is required. Please enter the WhatsApp Group ID.")
                
                # Validate Group ID format (should contain @g.us)
                if '@g.us' not in group_id:
                    raise ValidationError("Invalid Group ID format. Group ID should end with @g.us (e.g., 123456789-987654321@g.us)")
                
                text = (rec.body or "").strip()

                headers = {
                    "Authorization": f"Bearer {self._api_key()}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }

                payload = {"to": group_id}

                # Check if this is a media message
                if rec.type == 'media' and rec.media and rec.media_filename:
                    media_url = self._upload_media_file(rec.media, rec.media_filename)
                    ext = rec.media_filename.lower().split('.')[-1] if rec.media_filename else ''

                    if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt']:
                        payload.update({"documentUrl": media_url, "fileName": rec.media_filename})
                    elif ext in ['jpg', 'jpeg', 'png', 'gif']:
                        payload.update({"imageUrl": media_url})
                    elif ext in ['mp4', 'avi', 'mov']:
                        payload.update({"videoUrl": media_url})
                    elif ext in ['mp3', 'wav', 'ogg']:
                        payload.update({"audioUrl": media_url})
                    else:
                        payload.update({"documentUrl": media_url, "fileName": rec.media_filename})

                    if text:
                        payload["text"] = text
                else:
                    # Text only
                    if not text:
                        raise ValidationError("Text message cannot be empty.")
                    payload["text"] = text

                _logger.info("[WhatsApp API] Sending to Group ID=%s to=%s type=%s", rec.id, group_id, rec.type)

                resp = requests.post(API_URL, json=payload, headers=headers, timeout=20)

                if resp.status_code == 200:
                    resp_json = resp.json()
                    if resp_json.get("success"):
                        rec.status = 'sent'
                        rec.next_try = False
                        rec.last_error = False
                        rec.wa_message_id = rec._extract_wa_message_id(resp_json)
                        _logger.info("[WhatsApp API] ✅ Sent to Group ID=%s to=%s", rec.id, group_id)
                    else:
                        rec.status = 'failed'
                        rec.last_error = str(resp_json)
                        _logger.error("[WhatsApp API] ❌ Failed Group ID=%s response=%s", rec.id, resp_json)

                elif resp.status_code == 429:  # Too many requests
                    retry_after = int(resp.json().get("retry_after") or 60)
                    rec.status = 'pending'
                    rec.next_try = fields.Datetime.now() + timedelta(seconds=retry_after)
                    rec.last_error = f"Rate limited. Retry after {retry_after}s"
                    _logger.warning("[WhatsApp API] ⏳ Rate limited for Group ID=%s. Retry after %s seconds", rec.id,
                                    retry_after)

                else:
                    rec.status = 'failed'
                    rec.last_error = f"{resp.status_code}: {resp.text}"
                    _logger.error("[WhatsApp API] ❌ HTTP error for Group ID=%s code=%s resp=%s", rec.id,
                                  resp.status_code, resp.text)

            except Exception as e:
                rec.status = 'failed'
                rec.last_error = str(e)
                _logger.exception("[WhatsApp API] ❌ Exception for Group ID=%s: %s", rec.id, e)

    def action_send_whatsapp(self):
        """
        دالة موحّدة للإرسال — تُستدعى من جميع نماذج التأجير والمحاسبة والمبيعات.
        تُحدد تلقائياً هل الإرسال لفرد أم مجموعة بناءً على recipient_type أو محتوى phone.
        """
        for rec in self:
            if rec.recipient_type == 'group' or (rec.phone and '@g.us' in (rec.phone or '')):
                rec.action_send_to_group()
            else:
                rec.action_send_to_individual()

    @api.model
    def cron_send_pending(self):
        """Cron job to retry pending messages."""
        domain = [
            ('status', '=', 'pending'),
            '|',
            ('next_try', '=', False),
            ('next_try', '<=', fields.Datetime.now())
        ]
        records = self.search(domain, limit=20, order='create_date asc')
        _logger.info("[WhatsApp CRON] Found %s pending records to send", len(records))
        for rec in records:
            # توجيه الإرسال حسب النوع: مجموعة أم فرد
            if rec.recipient_type == 'group' or (rec.phone and '@g.us' in (rec.phone or '')):
                rec.action_send_to_group()
            else:
                rec.action_send_to_individual()

    # ------------------------------------------------------------------
    # Helpers shared by chat / dashboard / webhook
    # ------------------------------------------------------------------
    @api.model
    def _extract_wa_message_id(self, resp_json):
        """Best-effort extraction of the provider message id from a send response."""
        data = resp_json.get('data') or {}
        return (
            data.get('msgId') or data.get('id')
            or (data.get('key') or {}).get('id')
            or resp_json.get('msgId') or resp_json.get('id')
        )

    @api.model
    def _find_partner_by_phone(self, phone_plain):
        """Match a normalized (digits-only) phone against res.partner phone/mobile."""
        if not phone_plain:
            return False
        tail = phone_plain[-9:]
        partner_fields = self.env['res.partner']._fields
        phone_fields = [f for f in ('phone', 'mobile') if f in partner_fields]
        if not phone_fields:
            return False
        domain = [(f, 'like', tail) for f in phone_fields]
        if len(domain) > 1:
            domain = ['|'] * (len(domain) - 1) + domain
        partner = self.env['res.partner'].search(domain, limit=1)
        return partner.id if partner else False

    @api.model
    def create_incoming_message(self, phone_plain, body, wa_message_id=False, media_url=False):
        """Store an inbound WhatsApp message received via the webhook controller.

        Deduplicates on wa_message_id, links the message to a matching partner,
        and returns the created (or existing) record.
        """
        if wa_message_id:
            existing = self.search([('wa_message_id', '=', wa_message_id), ('direction', '=', 'in')], limit=1)
            if existing:
                return existing

        partner_id = self._find_partner_by_phone(phone_plain)
        vals = {
            'direction': 'in',
            'phone': phone_plain,
            'recipient_type': 'individual',
            'body': body or (media_url and f"[Media] {media_url}") or '',
            'status': 'sent',
            'wa_message_id': wa_message_id,
            'partner_id': partner_id,
            'message_datetime': fields.Datetime.now(),
            'is_read': False,
        }
        record = self.create(vals)
        _logger.info("[WhatsApp Webhook] Stored inbound message ID=%s from=%s", record.id, phone_plain)
        return record

    @api.model
    def get_dashboard_stats(self):
        """Aggregated data for the WhatsApp dashboard client action."""
        Message = self.sudo()
        total_sent = Message.search_count([('direction', '=', 'out'), ('status', '=', 'sent')])
        total_pending = Message.search_count([('status', '=', 'pending')])
        total_failed = Message.search_count([('status', '=', 'failed')])
        total_received = Message.search_count([('direction', '=', 'in')])
        total_contacts = len(Message.search([('partner_id', '!=', False)]).mapped('partner_id'))

        since = fields.Datetime.now() - timedelta(days=13)
        recent = Message.search([('create_date', '>=', since)])
        by_day = {}
        for rec in recent:
            day = fields.Datetime.context_timestamp(rec, rec.create_date).strftime('%Y-%m-%d')
            entry = by_day.setdefault(day, {'sent': 0, 'received': 0})
            entry['received' if rec.direction == 'in' else 'sent'] += 1

        days = []
        today = fields.Date.context_today(self)
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            key = d.strftime('%Y-%m-%d')
            entry = by_day.get(key, {'sent': 0, 'received': 0})
            days.append({'date': key, 'label': d.strftime('%d/%m'), 'sent': entry['sent'], 'received': entry['received']})

        top_partners = Message.read_group(
            [('partner_id', '!=', False)], ['partner_id'], ['partner_id'], limit=5, orderby='partner_id_count desc'
        )
        top_contacts = [{
            'partner_id': g['partner_id'][0],
            'name': g['partner_id'][1],
            'count': g['partner_id_count'],
        } for g in top_partners]

        return {
            'total_sent': total_sent,
            'total_pending': total_pending,
            'total_failed': total_failed,
            'total_received': total_received,
            'total_contacts': total_contacts,
            'series': days,
            'top_contacts': top_contacts,
        }

    @api.model
    def get_chat_threads(self, search=''):
        """Return one row per contact (or unmatched phone) with the last message, for the chat sidebar."""
        Message = self.sudo()
        domain = []
        if search:
            domain = ['|', ('phone', 'like', search), ('partner_id.name', 'ilike', search)]
        messages = Message.search(domain, order='message_datetime desc, create_date desc', limit=500)

        threads = {}
        for rec in messages:
            key = rec.partner_id.id if rec.partner_id else ('phone_%s' % rec.phone)
            if key in threads:
                if not rec.is_read and rec.direction == 'in':
                    threads[key]['unread'] += 1
                continue
            threads[key] = {
                'key': key,
                'partner_id': rec.partner_id.id if rec.partner_id else False,
                'name': rec.partner_id.name if rec.partner_id else (rec.phone or 'Unknown'),
                'phone': rec.phone,
                'last_message': rec.body,
                'last_date': fields.Datetime.to_string(rec.message_datetime or rec.create_date),
                'direction': rec.direction,
                'unread': 1 if (not rec.is_read and rec.direction == 'in') else 0,
            }
        return sorted(threads.values(), key=lambda t: t['last_date'], reverse=True)

    @api.model
    def get_chat_messages(self, key):
        """Return the ordered message history for one thread key (partner id or 'phone_<number>')."""
        Message = self.sudo()
        if isinstance(key, str) and key.startswith('phone_'):
            domain = [('phone', '=', key[len('phone_'):]), ('partner_id', '=', False)]
        else:
            domain = [('partner_id', '=', int(key))]
        records = Message.search(domain, order='message_datetime asc, create_date asc', limit=200)
        records.filtered(lambda r: r.direction == 'in' and not r.is_read).write({'is_read': True})
        return [{
            'id': r.id,
            'body': r.body,
            'direction': r.direction,
            'status': r.status,
            'date': fields.Datetime.to_string(r.message_datetime or r.create_date),
            'media_filename': r.media_filename or False,
        } for r in records]

    @api.model
    def send_chat_message(self, key, body):
        """Send a text message from the chat client action to the given thread key."""
        Message = self.sudo()
        phone = False
        partner_id = False
        if isinstance(key, str) and key.startswith('phone_'):
            phone = key[len('phone_'):]
        else:
            partner_id = int(key)
            partner = self.env['res.partner'].browse(partner_id)
            phone = getattr(partner, 'mobile', False) or partner.phone
        if not phone:
            raise ValidationError("No phone number available for this contact.")

        record = Message.create({
            'direction': 'out',
            'recipient_type': 'individual',
            'phone': phone,
            'body': body,
            'type': 'text',
            'partner_id': partner_id or Message._find_partner_by_phone(phone),
            'message_datetime': fields.Datetime.now(),
        })
        record.action_send_to_individual()
        return self.get_chat_messages(key)


class WhatsappGroup(models.Model):
    _name = 'adv.whatsapp.group'
    _description = 'WhatsApp Group'
    
    name = fields.Char(required=True, string='Group Name')
    group_id = fields.Char(required=True, unique=True, string='Group ID', 
                          help="WhatsApp Group ID (e.g., 123456789-987654321@g.us)")
    description = fields.Text()
    participant_count = fields.Integer(string='Participants')
    active = fields.Boolean(default=True)
    last_sync = fields.Datetime(string='Last Sync')
    
    @api.constrains('group_id')
    def _check_group_id_format(self):
        for rec in self:
            if rec.group_id and '@g.us' not in rec.group_id:
                raise ValidationError("Invalid Group ID format. It should end with @g.us")
    
    def action_sync_participants(self):
        """Sync group participants from Wasender API."""
        # يمكنك إضافة كود لجلب المشاركين من API
        pass
