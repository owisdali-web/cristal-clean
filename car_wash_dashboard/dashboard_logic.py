# -*- coding: utf-8 -*-
"""Pure helpers for the car-wash dashboard.

This module intentionally has no Odoo imports so its core logic can be
validated independently from an Odoo runtime.
"""
from collections import defaultdict


SMALL_VALUES = {'small'}
LARGE_VALUES = {'large'}


def normalize_vehicle_size(value, service_name=''):
    value = str(value or '').strip().lower()
    if value in SMALL_VALUES:
        return 'small'
    if value in LARGE_VALUES:
        return 'large'

    service = str(service_name or '').strip().lower()
    if 'small car' in service or 'سيارة صغيرة' in service:
        return 'small'
    if 'large car' in service or 'سيارة كبيرة' in service:
        return 'large'
    return ''



def calculate_progress_percent(elapsed_minutes, expected_minutes):
    """Return a bounded visual percentage from real timing values.

    ``False``/``None`` means Odoo has no usable timing value.  Numeric zero is
    valid for elapsed time but expected duration must be greater than zero.
    """
    if elapsed_minutes is False or elapsed_minutes is None:
        return False
    if expected_minutes is False or expected_minutes is None:
        return False
    try:
        elapsed = float(elapsed_minutes)
        expected = float(expected_minutes)
    except (TypeError, ValueError):
        return False
    if elapsed < 0 or expected <= 0:
        return False
    return max(0, min(100, int(round((elapsed / expected) * 100))))

def infer_station_type(name, configured_type=''):
    configured_type = str(configured_type or '').strip().lower()
    if configured_type in {'automatic', 'polishing', 'general'}:
        return configured_type

    lowered = str(name or '').strip().lower()
    if any(fragment in lowered for fragment in ('automatic', 'auto', 'آلي', 'الي')):
        return 'automatic'
    if any(fragment in lowered for fragment in ('polish', 'polishing', 'تلميع', 'لمعة', 'باستا')):
        return 'polishing'
    return 'general'


def build_station_slots(stations, target=10):
    target = max(0, int(target or 0))
    slots = []
    for index, station in enumerate(list(stations or [])[:target], start=1):
        item = dict(station)
        item.setdefault('is_placeholder', False)
        item['slot_number'] = index
        slots.append(item)

    while len(slots) < target:
        index = len(slots) + 1
        slots.append({
            'id': False,
            'name': f'Station {index}',
            'station_type': 'general',
            'status': 'not_configured',
            'current_car': False,
            'elapsed_minutes': False,
            'conflict_count': 0,
            'is_placeholder': True,
            'slot_number': index,
        })
    return slots


def group_progress_rows(rows):
    grouped = defaultdict(list)
    for row in rows or []:
        station_id = row.get('station_id')
        production_id = row.get('production_id')
        if not station_id or not production_id:
            continue
        if production_id not in grouped[station_id]:
            grouped[station_id].append(production_id)

    return {
        station_id: {
            'production_ids': production_ids,
            'conflict_count': len(production_ids),
        }
        for station_id, production_ids in grouped.items()
    }
