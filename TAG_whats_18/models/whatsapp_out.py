# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import re
import base64
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


API_URL = "https://wasenderapi.com/api/send-message" 
UPLOAD_URL = "https://www.wasenderapi.com/api/upload"
HARDCODED_API_KEY = "abfbb0189ccd55e90910c2a1060e2aa98099c97f410b7e2809d0373d84ec6cfb"

class WhatsappOut(models.Model):
    _name = 'adv.whatsapp.out'
    _description = 'WhatsApp out message'

    type = fields.Selection([
        ('text', 'Text Message'),
        ('media', 'Media Message'),
    ], default='text')

    phone = fields.Char(required=True)
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

# -*- coding: utf-8 -*-
# ... (بقية الكود)

    def _upload_media_file(self, media_data, filename):
        """Upload media file to Wasender API and return the public URL."""
        try:
            # ✅ الحل: تبسيط الكود ليتطابق مع الوثائق بدقة
            
            # 1. media_data من Odoo هي bytes، نحولها إلى نص Base64
            media_data_string = media_data.decode('utf-8')

            # 2. نحدد نوع MIME. بما أننا نرسل فاتورة، فهو دائمًا PDF.
            mime_type = 'application/pdf'

            # 3. نبني سلسلة البيانات الكاملة تمامًا كما في الوثائق
            full_base64_string = f"data:{mime_type};base64,{media_data_string}"
            
            headers = {
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "base64": full_base64_string
            }

            # 4. إرسال الطلب
            resp = requests.post(UPLOAD_URL, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 200:
                response_data = resp.json()
                if response_data.get('success'):
                    return response_data.get('publicUrl')
                else:
                    # نستخدم raise ValidationError لعرض الخطأ للمستخدم بشكل أفضل
                    error_message = response_data.get('error', 'Unknown error from Wasender')
                    raise ValidationError(f"Upload failed: {error_message}")
            else:
                # هذا هو المكان الذي كنا نرى فيه خطأ 500
                raise ValidationError(f"Upload failed with status {resp.status_code}: {resp.text}")
                
        except Exception as e:
            # هذا يلتقط أي خطأ آخر، مثل فشل الاتصال
            raise ValidationError(f"Error during media file upload: {str(e)}")

# ... (بقية الكود)

    def action_send_whatsapp(self):
        """Send WhatsApp message via Wasender API."""
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

                # ✅ Check if this is a media message
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
                    # ✅ Text only
                    if not text:
                        raise ValidationError("Text message cannot be empty.")
                    payload["text"] = text

                _logger.info("[WhatsApp API] Sending message ID=%s to=%s type=%s", rec.id, phone_plain, rec.type)

                resp = requests.post(API_URL, json=payload, headers=headers, timeout=20)

                if resp.status_code == 200:
                    resp_json = resp.json()
                    if resp_json.get("success"):
                        rec.status = 'sent'
                        rec.next_try = False
                        rec.last_error = False
                        _logger.info("[WhatsApp API] ✅ Sent message ID=%s to=%s", rec.id, phone_plain)
                    else:
                        rec.status = 'failed'
                        rec.last_error = str(resp_json)
                        _logger.error("[WhatsApp API] ❌ Failed message ID=%s response=%s", rec.id, resp_json)

                elif resp.status_code == 429:  # Too many requests
                    retry_after = int(resp.json().get("retry_after") or 60)
                    rec.status = 'pending'
                    rec.next_try = fields.Datetime.now() + timedelta(seconds=retry_after)
                    rec.last_error = f"Rate limited. Retry after {retry_after}s"
                    _logger.warning("[WhatsApp API] ⏳ Rate limited for message ID=%s. Retry after %s seconds", rec.id,
                                    retry_after)

                else:
                    rec.status = 'failed'
                    rec.last_error = f"{resp.status_code}: {resp.text}"
                    _logger.error("[WhatsApp API] ❌ HTTP error for message ID=%s code=%s resp=%s", rec.id,
                                  resp.status_code, resp.text)

            except Exception as e:
                rec.status = 'failed'
                rec.last_error = str(e)
                _logger.exception("[WhatsApp API] ❌ Exception for message ID=%s: %s", rec.id, e)

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
            rec.action_send_whatsapp()

