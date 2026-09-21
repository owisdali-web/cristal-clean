# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging
import base64

_logger = logging.getLogger(__name__)

class WhatsappGroup(models.Model):
    _name = 'adv.whatsapp.group'
    _description = 'WhatsApp Group'
    _order = 'name asc'
    
    # ✅ الحقول
    name = fields.Char(required=True, string='Group Name', index=True)
    group_id = fields.Char(required=True, unique=True, string='Group ID', 
                          help="Format: 123456789-987654321@g.us", index=True)
    description = fields.Text()
    participant_count = fields.Integer(string='Participants', default=0)
    group_icon = fields.Binary("Group Icon", attachment=True)
    active = fields.Boolean(default=True)
    last_sync = fields.Datetime(string='Last Sync', readonly=True)
    is_admin = fields.Boolean(string='Is Admin', default=False)
    
    # ✅ التحقق من صحة Group ID
    @api.constrains('group_id')
    def _check_group_id_format(self):
        for rec in self:
            if rec.group_id and '@g.us' not in rec.group_id:
                raise ValidationError("Invalid Group ID format. It should end with @g.us")
    
    # ✅ جلب مفتاح API
    @api.model
    def _get_api_key(self):
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('tag_whatsapp.was_api_key')
        if not api_key:
            raise ValidationError("Please configure Wasender API Key in System Parameters")
        return api_key

    # ✅ الدالة الرئيسية: جلب المجموعات من API
    def action_fetch_groups_from_api(self):
        """Fetch all WhatsApp groups from Wasender API"""
        API_URL = "https://wasenderapi.com/api/groups"
        api_key = self._get_api_key()
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        try:
            _logger.info("[WhatsApp Groups] Fetching groups from API...")
            response = requests.get(API_URL, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    # ✅ التصحيح: استخدام 'data' بدلاً من 'groups'
                    groups = data.get('data', [])
                    
                    if not groups:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'Info',
                                'message': 'No groups found in your WhatsApp account',
                                'type': 'info',
                                'sticky': False,
                            }
                        }
                    
                    created = updated = 0
                    for group in groups:
                        # ✅ استخراج البيانات - قد تختلف أسماء الحقول حسب API
                        g_id = group.get('id') or group.get('groupId') or group.get('jid')
                        g_name = group.get('subject') or group.get('name') or group.get('groupName') or 'Unknown'
                        participants = group.get('participants') or group.get('members') or []
                        is_admin = group.get('isAdmin') or group.get('admin') or False
                        
                        if not g_id:
                            _logger.warning(f"Skipping group with no ID: {group}")
                            continue
                        
                        existing = self.search([('group_id', '=', g_id)], limit=1)
                        
                        values = {
                            'name': g_name,
                            'participant_count': len(participants),
                            'is_admin': is_admin,
                            'last_sync': fields.Datetime.now(),
                            'active': True,
                        }
                        
                        if existing:
                            existing.write(values)
                            updated += 1
                        else:
                            values['group_id'] = g_id
                            self.create(values)
                            created += 1
                    
                    message = f"✅ Sync: {created} new, {updated} updated"
                    _logger.info(f"[WhatsApp Groups] {message}")
                    
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'Success',
                            'message': message,
                            'type': 'success',
                            'sticky': False,
                            'next': {'type': 'ir.actions.act_window_close'},
                        }
                    }
                else:
                    raise ValidationError(f"API Error: {data.get('error') or data.get('message') or 'Unknown'}")
            
            elif response.status_code == 401:
                raise ValidationError("Invalid API Key")
            elif response.status_code == 403:
                raise ValidationError("Access Denied")
            else:
                raise ValidationError(f"HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            raise ValidationError("Connection Timeout")
        except requests.exceptions.ConnectionError:
            raise ValidationError("Could not reach API server")
        except Exception as e:
            _logger.exception("[WhatsApp Groups] Error: %s", str(e))
            raise ValidationError(f"Error: {str(e)}")

    # ✅ دالة مساعدة لتحميل الأيقونة
    def _download_image(self, url):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return base64.b64encode(resp.content)
        except:
            pass
        return False

    # ✅ تحديث مجموعة يدوياً
    def action_refresh_single_group(self):
        for rec in self:
            rec.last_sync = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Refreshed',
                'message': f'{len(self)} group(s) refreshed',
                'type': 'success',
                'sticky': False,
            }
        }

    # ✅ Cron Job للمزامنة التلقائية
    @api.model
    def cron_sync_all_groups(self):
        _logger.info("[WhatsApp CRON] Starting auto sync...")
        try:
            self.action_fetch_groups_from_api()
        except Exception as e:
            _logger.error("[WhatsApp CRON] Failed: %s", str(e))























