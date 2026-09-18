# -*- coding: utf-8 -*-
"""V6.1 Crystal Clean station and routing migration.

Confirmed project topology:
- A1..A8 are the eight General rooms.
- A9 is the Automatic wash room.
- A10 is the Polishing room.

The approved operating model is one service = one Work Order = one physical
station until completion.  The migration therefore configures the ten known
stations, makes the eight General rooms alternatives of each other, and
consolidates only the nine known CC-OPS service BoMs.  Extra operations are
archived (never deleted), which keeps the migration reversible and leaves any
unrecognised/custom BoM untouched.
"""
import re

from odoo import SUPERUSER_ID, api


STATION_TYPES = {
    'A1': 'general',
    'A2': 'general',
    'A3': 'general',
    'A4': 'general',
    'A5': 'general',
    'A6': 'general',
    'A7': 'general',
    'A8': 'general',
    'A9': 'automatic',
    'A10': 'polishing',
}

# Known operational carrier codes confirmed by the project diagnostic.
SERVICE_ROUTING = {
    'CC-OPS-AUTO': {'station': 'A9', 'label': 'الغسيل الآلي'},
    'CC-OPS-DEEP': {'station': 'general', 'label': 'غسيل عميق'},
    'CC-OPS-EXT': {'station': 'general', 'label': 'الغسيل اليدوي الخارجي'},
    'CC-OPS-FULL': {'station': 'general', 'label': 'الغسيل الشامل'},
    'CC-OPS-INT': {'station': 'general', 'label': 'الغسيل الداخلي'},
    'CC-OPS-PASTE': {'station': 'A10', 'label': 'الباستا والتلميع'},
    'CC-OPS-POWDER': {'station': 'general', 'label': 'غسيل الفودرة'},
    'CC-OPS-SALON': {'station': 'general', 'label': 'غسيل الصالة'},
    'CC-OPS-SHINE': {'station': 'A10', 'label': 'اللمعة'},
}


def _station_code(name):
    match = re.match(r'^\s*(A(?:10|[1-9]))(?:\s|$|-)', name or '', flags=re.IGNORECASE)
    return match.group(1).upper() if match else False


def _bom_service_code(bom):
    """Return a known CC-OPS code without guessing from arbitrary names."""
    candidates = []
    if bom.product_tmpl_id:
        candidates.append(bom.product_tmpl_id.default_code)
    if 'product_id' in bom._fields and bom.product_id:
        candidates.append(bom.product_id.default_code)
    candidates.append(bom.code if 'code' in bom._fields else False)
    for value in candidates:
        code = (value or '').strip().upper()
        if code in SERVICE_ROUTING:
            return code
    return False


def _configure_station_network(by_code):
    ordered = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10']
    for sequence, code in enumerate(ordered, start=1):
        by_code[code].write({
            'active': True,
            'car_wash_enabled': True,
            'car_wash_station_type': STATION_TYPES[code],
            'car_wash_sequence': sequence,
        })

    # Any General room can execute a General service.  Odoo's planning engine
    # may select an alternative work center when the primary room is busy or
    # unavailable. Automatic and Polishing stay restricted to their own rooms.
    if 'alternative_workcenter_ids' in by_code['A1']._fields:
        general = [by_code[f'A{number}'] for number in range(1, 9)]
        for workcenter in general:
            alternatives = [candidate.id for candidate in general if candidate.id != workcenter.id]
            workcenter.write({'alternative_workcenter_ids': [(6, 0, alternatives)]})
        by_code['A9'].write({'alternative_workcenter_ids': [(5, 0, 0)]})
        by_code['A10'].write({'alternative_workcenter_ids': [(5, 0, 0)]})


def _consolidate_known_service_boms(env, by_code, company_id):
    Operation = env['mrp.routing.workcenter'].with_context(active_test=False)
    Bom = env['mrp.bom'].with_context(active_test=False)

    general_ids = {by_code[f'A{number}'].id for number in range(1, 9)}
    general_primary = by_code['A1']

    boms = Bom.search([('company_id', '=', company_id)])
    for bom in boms:
        service_code = _bom_service_code(bom)
        if not service_code:
            continue
        rule = SERVICE_ROUTING[service_code]
        operations = Operation.search([('bom_id', '=', bom.id)], order='sequence, id')
        if not operations:
            continue

        # Prefer the operation already carrying the service semantics, and never
        # use a final-check operation as the retained operation when avoidable.
        active_ops = operations.filtered(lambda op: not ('active' in op._fields) or op.active)
        candidates = active_ops or operations
        non_final = candidates.filtered(
            lambda op: not any(term in (op.name or '').lower() for term in ('فحص', 'مسح نهائي', 'final'))
        )
        keeper = (non_final or candidates)[:1]
        if not keeper:
            continue

        if rule['station'] == 'A9':
            target = by_code['A9']
        elif rule['station'] == 'A10':
            target = by_code['A10']
        else:
            # Preserve an existing General room when possible; otherwise A1 is
            # the primary room and A2..A8 are configured as alternatives.
            target = keeper.workcenter_id if keeper.workcenter_id.id in general_ids else general_primary

        keeper_vals = {
            'workcenter_id': target.id,
            'name': rule['label'],
        }
        if 'active' in keeper._fields:
            keeper_vals['active'] = True
        keeper.write(keeper_vals)

        extras = operations - keeper

        # Preserve component/by-product operation assignments when collapsing
        # several operations into the single retained Work Order.
        if extras:
            material_lines = bom.bom_line_ids.filtered(lambda line: line.operation_id in extras)
            if material_lines:
                material_lines.write({'operation_id': keeper.id})
            if 'byproduct_ids' in bom._fields:
                byproduct_lines = bom.byproduct_ids.filtered(lambda line: line.operation_id in extras)
                if byproduct_lines:
                    byproduct_lines.write({'operation_id': keeper.id})

        # A single operation has no intra-BoM dependency chain.
        if 'blocked_by_operation_ids' in keeper._fields and keeper.blocked_by_operation_ids:
            keeper.write({'blocked_by_operation_ids': [(5, 0, 0)]})

        if extras and 'active' in Operation._fields:
            extras.write({'active': False})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Workcenter = env['mrp.workcenter'].with_context(active_test=False)

    for company in env['res.company'].search([]):
        candidates = Workcenter.search([('company_id', '=', company.id)])
        by_code = {}
        for workcenter in candidates:
            code = _station_code(workcenter.name)
            if code in STATION_TYPES and code not in by_code:
                by_code[code] = workcenter

        # Never mutate unrelated databases or incomplete station sets.
        if set(by_code) != set(STATION_TYPES):
            continue

        _configure_station_network(by_code)
        _consolidate_known_service_boms(env, by_code, company.id)
