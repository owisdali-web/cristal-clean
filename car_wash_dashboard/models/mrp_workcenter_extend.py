# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


_STATION_CODE_RE = re.compile(r'^CC-WC-A(\d+)(?:-(.*))?$', re.IGNORECASE)


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    cc_is_car_wash_station = fields.Boolean(
        string='Car Wash Station',
        default=False,
        index=True,
        copy=False,
        help='Marks this Work Center as part of the Crystal Clean car-wash station topology.',
    )
    cc_station_code = fields.Char(
        string='Car Wash Station Code',
        index=True,
        copy=False,
        help='Stable dashboard code such as A1, A2, A9 or A10. It is independent from the Work Center name.',
    )
    cc_station_order = fields.Integer(
        string='Car Wash Station Order',
        default=100,
        copy=False,
        help='Stable display/processing order for the car-wash topology.',
    )
    cc_station_kind = fields.Selection(
        selection=[
            ('general', 'General / Flexible'),
            ('auto', 'Automatic Wash'),
            ('polish', 'Polish / Shine'),
        ],
        string='Car Wash Station Kind',
        default='general',
        required=True,
        copy=False,
    )
    cc_station_manual_state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('maintenance', 'Maintenance'),
            ('closed', 'Closed'),
        ],
        string='Car Wash Manual State',
        default='open',
        required=True,
        copy=False,
        help='Administrative state only. Busy/queued/available are derived from real Work Orders at runtime.',
    )

    @api.model
    def _cw_topology_values_from_identifiers(self, code, name=''):
        """Infer a one-time topology bootstrap from the established Crystal Clean code convention.

        The returned values are only bootstrap defaults. Runtime dashboard logic reads the
        explicit cc_* fields and never assigns A9/A10 roles from their visual slot position.
        """
        match = _STATION_CODE_RE.match((code or '').strip())
        if not match:
            return {}

        number = int(match.group(1))
        suffix = (match.group(2) or '').strip().lower()
        text = '%s %s' % (suffix, (name or '').lower())

        kind = 'general'
        if number == 9 or any(token in text for token in ('auto', 'آلي', 'الي')):
            kind = 'auto'
        elif number == 10 or any(token in text for token in ('polish', 'لمعة', 'تلميع')):
            kind = 'polish'

        return {
            'cc_is_car_wash_station': True,
            'cc_station_code': 'A%s' % number,
            'cc_station_order': number * 10,
            'cc_station_kind': kind,
            'cc_station_manual_state': 'open',
        }

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for original in vals_list:
            vals = dict(original)
            inferred = self._cw_topology_values_from_identifiers(vals.get('code'), vals.get('name'))
            for field_name, value in inferred.items():
                vals.setdefault(field_name, value)
            prepared.append(vals)
        return super().create(prepared)
