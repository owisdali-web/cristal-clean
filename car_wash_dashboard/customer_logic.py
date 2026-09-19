# -*- coding: utf-8 -*-
"""Pure customer-intelligence helpers with no Odoo imports."""

import math


FREQUENT_VISITS_MIN = 5
INACTIVE_DAYS = 30


def high_value_cutoff(values):
    """Return the minimum value that belongs to the top 20% of spend values."""
    cleaned = sorted(float(value or 0.0) for value in values if value is not None)
    if not cleaned:
        return 0.0
    index = min(len(cleaned) - 1, int(math.ceil(len(cleaned) * 0.8)))
    return cleaned[index]


def customer_segment(visits, total_spend, days_since_last, high_value_threshold):
    visits = int(visits or 0)
    total_spend = float(total_spend or 0.0)
    days_since_last = int(days_since_last or 0)
    high_value_threshold = float(high_value_threshold or 0.0)

    if days_since_last > INACTIVE_DAYS:
        return 'inactive'
    if high_value_threshold > 0 and total_spend >= high_value_threshold and visits > 1:
        return 'high_value'
    if visits >= FREQUENT_VISITS_MIN:
        return 'frequent'
    if visits <= 1:
        return 'new'
    return 'regular'
