# -*- coding: utf-8 -*-


def bootstrap_station_topology(env):
    """Backfill only Crystal Clean Work Centers that already follow CC-WC-A* codes.

    This never changes Work Center IDs, names, native codes, sequences, capacities,
    BoMs, operations or historical Work Orders.
    """
    Workcenter = env['mrp.workcenter'].sudo().with_context(active_test=False)
    candidates = Workcenter.search([('code', '=like', 'CC-WC-A%')])
    changed = Workcenter.browse()

    for workcenter in candidates:
        inferred = Workcenter._cw_topology_values_from_identifiers(workcenter.code, workcenter.name)
        if not inferred:
            continue

        vals = {}
        # New topology fields are authoritative after bootstrap. We intentionally
        # do not touch any native MRP field.
        for field_name, value in inferred.items():
            if workcenter[field_name] != value:
                vals[field_name] = value

        if vals:
            workcenter.write(vals)
            changed |= workcenter

    return changed


def post_init_hook(env):
    bootstrap_station_topology(env)
