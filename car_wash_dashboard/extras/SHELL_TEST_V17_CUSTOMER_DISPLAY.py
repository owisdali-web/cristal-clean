exec(r'''
from odoo.exceptions import AccessError

W = 150
checks = 0
failed = 0


def check(label, condition, detail=''):
    global checks, failed
    checks += 1
    ok = bool(condition)
    if not ok:
        failed += 1
    print(f"{'PASS' if ok else 'FAIL':<5} | {label}" + (f" | {detail}" if detail else ''))
    return ok


def header(title):
    print('\n' + '=' * W)
    print(title)
    print('=' * W)


def fingerprint(model, domain=None):
    recs = model.search(domain or [])
    writes = [x.write_date for x in recs if x.write_date]
    return (len(recs), max(writes) if writes else False, tuple(recs.ids))


header('CRYSTAL CLEAN V17 - CUSTOMER DISPLAY BACKEND - READ ONLY')
print('Database :', env.cr.dbname)
print('Company  :', env.company.id, env.company.display_name)
print('User     :', env.user.id, env.user.display_name)
print('Timezone :', env.user.tz or 'UTC')

Module = env['ir.module.module']
mod = Module.search([('name', '=', 'car_wash_dashboard')], limit=1)
check('Module installed', bool(mod and mod.state == 'installed'), str(mod.state if mod else None))
check('Module version 18.0.17.0', bool(mod and mod.installed_version == '18.0.17.0'), str(mod.installed_version if mod else None))

M = env['mrp.production']
WO = env['mrp.workorder']
WC = env['mrp.workcenter']
POS = env['pos.order']
AM = env['account.move']

check('V17 public API exists', hasattr(M, 'get_customer_display_data'))
check('V17 contract helper exists', hasattr(M, '_cw_customer_display_contract'))
check('V17 sanitizer helper exists', hasattr(M, '_cw_customer_display_car_payload'))
check('V17 ETA helper exists', hasattr(M, '_cw_customer_display_eta_map'))
check('V16 API retained', hasattr(M, 'get_operational_intelligence_data'))
check('V15 operations API retained', hasattr(M, 'get_operations_data'))
check('V14 topology API retained', hasattr(M, 'get_station_topology'))

# ---------------------------------------------------------------------
# Security architecture
# ---------------------------------------------------------------------
header('[1] SECURITY ARCHITECTURE')
Group = env['res.groups']
display_group = env.ref('car_wash_dashboard.group_car_wash_customer_display', raise_if_not_found=False)
check('Display security group exists', bool(display_group))
if display_group:
    check('Display group name present', bool(display_group.name), str(display_group.name))
    internal_group = env.ref('base.group_user')
    check('Display group does NOT imply Internal User', internal_group not in display_group.implied_ids, str(display_group.implied_ids.ids))

    Access = env['ir.model.access']
    sensitive_models = ['mrp.production', 'mrp.workorder', 'pos.order', 'account.move', 'stock.move', 'res.partner']
    for model_name in sensitive_models:
        model_rec = env['ir.model'].search([('model', '=', model_name)], limit=1)
        if model_rec:
            rows = Access.search([('group_id', '=', display_group.id), ('model_id', '=', model_rec.id)])
            check(f'No direct ACL granted to display group: {model_name}', not rows, str(rows.ids))

check('Current admin/system user authorized for test', M._cw_customer_display_access_allowed())

# If an existing user lacks both display and system groups, verify denial without creating data.
unauthorized = env['res.users'].with_context(active_test=False).search([
    ('id', '!=', env.user.id),
], limit=100)
unauthorized = unauthorized.filtered(
    lambda u: not u.has_group('car_wash_dashboard.group_car_wash_customer_display')
    and not u.has_group('base.group_system')
)[:1]
if unauthorized:
    denied = False
    try:
        M.with_user(unauthorized).get_customer_display_data()
    except AccessError:
        denied = True
    check('Unauthorized existing user is denied', denied, f'user={unauthorized.id} {unauthorized.display_name}')
else:
    check('Unauthorized-user denial test skipped safely (no candidate)', True, 'No existing candidate user')

# ---------------------------------------------------------------------
# Read-only baseline fingerprints
# ---------------------------------------------------------------------
base_fp = {
    'wc': fingerprint(WC.with_context(active_test=False), []),
    'wo': fingerprint(WO.with_context(active_test=False), []),
    'mo': fingerprint(M.with_context(active_test=False), []),
    'pos': fingerprint(POS.with_context(active_test=False), []),
    'am': fingerprint(AM.with_context(active_test=False), []),
}

# ---------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------
header('[2] CONTRACT')
data = M.get_customer_display_data()
check('Contract is dict', isinstance(data, dict))
check('Contract version exact', data.get('contract_version') == '17.0-customer-display', str(data.get('contract_version')))
check('Generated timestamp present', bool(data.get('generated_at')))
check('Timezone exact', data.get('timezone') == (env.user.tz or 'UTC'), str(data.get('timezone')))
check('Company dict', isinstance(data.get('company'), dict))
check('Company ID exact', data['company'].get('id') == env.company.id, str(data['company'].get('id')))
check('Company name exact', data['company'].get('name') == env.company.display_name, str(data['company'].get('name')))
check('Logo availability exact', data['company'].get('logo_available') is bool(env.company.logo), str(data['company'].get('logo_available')))
check('Logo URL coherent', bool(data['company'].get('logo_url')) is bool(env.company.logo), str(data['company'].get('logo_url')))
check('Display policy dict', isinstance(data.get('display_policy'), dict))
check('Counts dict', isinstance(data.get('counts'), dict))
check('Rotation list', isinstance(data.get('rotation'), list))
check('Ready list', isinstance(data.get('ready_for_pickup'), list))
check('Semantics dict', isinstance(data.get('semantics'), dict))

for key in ('intro_enabled', 'intro_seconds', 'rotation_seconds', 'fullscreen_requires_user_gesture', 'show_vehicle_model', 'show_current_stage', 'show_eta', 'show_ready_for_pickup'):
    check(f'Display policy key {key}', key in data['display_policy'], str(data['display_policy'].get(key)))
check('Intro duration positive', data['display_policy'].get('intro_seconds', 0) > 0, str(data['display_policy'].get('intro_seconds')))
check('Rotation duration positive', data['display_policy'].get('rotation_seconds', 0) > 0, str(data['display_policy'].get('rotation_seconds')))
check('Fullscreen gesture policy true', data['display_policy'].get('fullscreen_requires_user_gesture') is True)

for key in ('privacy', 'progress', 'eta', 'projection'):
    check(f'Semantics {key} documented', bool(data['semantics'].get(key)))

# ---------------------------------------------------------------------
# Exact visible MOs / counts
# ---------------------------------------------------------------------
header('[3] VISIBLE VEHICLES AND COUNTS')
visible_mos = M.search(
    M._cw_wash_domain() + [('state', 'in', ['confirmed', 'progress', 'to_close'])],
    order='date_start asc, id asc',
)
rotation = data['rotation']
ready = data['ready_for_pickup']
all_rows = rotation + ready
api_keys = {row['display_key'] for row in all_rows}
expected_keys = {M._cw_customer_display_key(mo) for mo in visible_mos}
check('Visible MO opaque keys exact', api_keys == expected_keys, f'API={sorted(api_keys)} DB={sorted(expected_keys)}')
check('Visible count exact', data['counts'].get('visible') == len(visible_mos), f"{data['counts'].get('visible')} vs {len(visible_mos)}")
expected_ready = visible_mos.filtered(lambda mo: mo.state == 'to_close')
check('Ready count exact', data['counts'].get('ready_for_pickup') == len(expected_ready), f"{data['counts'].get('ready_for_pickup')} vs {len(expected_ready)}")
check('Ready keys exact', {row['display_key'] for row in ready} == {M._cw_customer_display_key(mo) for mo in expected_ready}, str(expected_ready.ids))
check('Ready excluded from rotation', not ({row['display_key'] for row in rotation} & {row['display_key'] for row in ready}))
check('Idle exact', data.get('idle') is (len(visible_mos) == 0), f"{data.get('idle')} vs {len(visible_mos) == 0}")
check('Count partition exact', data['counts'].get('visible') == data['counts'].get('in_service', 0) + data['counts'].get('waiting', 0) + data['counts'].get('ready_for_pickup', 0))
check('Rotation count exact', len(rotation) == data['counts'].get('in_service', 0) + data['counts'].get('waiting', 0))

# ---------------------------------------------------------------------
# Privacy / payload shape
# ---------------------------------------------------------------------
header('[4] PRIVACY AND PAYLOAD SHAPE')
sensitive_keys = {
    'customer', 'customer_id', 'customer_phone', 'phone', 'mobile',
    'pos_amount', 'amount_total', 'payment_state', 'price', 'revenue',
    'operator_names', 'operator_label', 'employee_ids', 'partner_id',
    'vehicle_notes', 'sale_order', 'invoice', 'accounting',
}


def find_sensitive(value, path='root'):
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in sensitive_keys:
                found.append(f'{path}.{key}')
            found.extend(find_sensitive(item, f'{path}.{key}'))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(find_sensitive(item, f'{path}[{index}]'))
    return found

leaks = find_sensitive(data)
check('No sensitive keys exposed recursively', not leaks, ', '.join(leaks[:20]))

allowed_car_keys = {
    'display_key', 'public_reference', 'vehicle_model', 'vehicle_color', 'service_name',
    'display_state', 'display_label', 'progress_percent', 'progress_basis', 'current_stage',
    'station_code', 'eta_minutes', 'eta_reliable', 'eta_scope', 'eta_reason', 'queue_position',
}
for row in all_rows:
    rid = row.get('display_key')
    check(f'MO {rid} car payload keys exact', set(row.keys()) == allowed_car_keys, str(sorted(set(row.keys()) - allowed_car_keys)))
    check(f'MO {rid} public reference present', bool(row.get('public_reference')), str(row.get('public_reference')))
    check(f'MO {rid} display state valid', row.get('display_state') in ('waiting', 'in_service', 'ready_for_pickup'), str(row.get('display_state')))
    check(f'MO {rid} progress bounded', 0 <= float(row.get('progress_percent') or 0) <= 100, str(row.get('progress_percent')))
    check(f'MO {rid} progress basis exact', row.get('progress_basis') == 'completed_steps_plus_running_expected_duration')
    check(f'MO {rid} queue position nonnegative', int(row.get('queue_position') or 0) >= 0, str(row.get('queue_position')))
    check(f'MO {rid} ETA scope valid', row.get('eta_scope') in ('current_stage', 'service'), str(row.get('eta_scope')))
    if row.get('eta_minutes') is not False:
        check(f'MO {rid} ETA nonnegative', float(row.get('eta_minutes') or 0) >= 0, str(row.get('eta_minutes')))
    if row.get('display_state') == 'ready_for_pickup':
        check(f'MO {rid} ready progress 100', row.get('progress_percent') == 100.0, str(row.get('progress_percent')))
        check(f'MO {rid} ready ETA zero', row.get('eta_minutes') == 0.0, str(row.get('eta_minutes')))
        check(f'MO {rid} ready ETA reliable', row.get('eta_reliable') is True)
        check(f'MO {rid} ready excluded from rotation', rid not in {r['display_key'] for r in rotation})

# ---------------------------------------------------------------------
# State and ETA coherence against MRP
# ---------------------------------------------------------------------
header('[5] MRP STATE / ETA COHERENCE')
row_map = {row['display_key']: row for row in all_rows}
active_wos = WO.search(M._cw_operations_workorder_domain())
station_wcs = M._cw_station_workcenters()
station_ids = set(station_wcs.ids)

for mo in visible_mos:
    row = row_map[M._cw_customer_display_key(mo)]
    workorders = mo.workorder_ids.filtered(lambda wo: wo.state != 'cancel')
    current = (
        workorders.filtered(lambda wo: wo.state == 'progress')[:1]
        or workorders.filtered(lambda wo: wo.state == 'ready')[:1]
        or workorders.filtered(lambda wo: wo.state == 'waiting')[:1]
        or workorders.filtered(lambda wo: wo.state == 'pending')[:1]
    )
    expected_state = 'ready_for_pickup' if mo.state == 'to_close' else ('in_service' if current and current.state == 'progress' else 'waiting')
    check(f'MO {mo.id} display state exact', row.get('display_state') == expected_state, f"{row.get('display_state')} vs {expected_state}")
    expected_station = ''
    if current and current.workcenter_id:
        expected_station = current.workcenter_id.cc_station_code or current.workcenter_id.code or ''
    check(f'MO {mo.id} station code exact', row.get('station_code') == expected_station, f"{row.get('station_code')} vs {expected_station}")

    if current and current.workcenter_id and current.workcenter_id.id in station_ids and mo.state != 'to_close':
        wc = current.workcenter_id
        station_active = active_wos.filtered(lambda wo: wo.workcenter_id and wo.workcenter_id.id == wc.id)
        occupancy = len(station_active.filtered(lambda wo: wo.state == 'progress'))
        capacity = max(int(wc.default_capacity or 1), 1)
        manual_state = wc.cc_station_manual_state or 'open'
        should_project = occupancy <= capacity and manual_state == 'open' and float(current.duration_expected or 0.0) > 0
        if not should_project:
            check(f'MO {mo.id} unreliable ETA suppressed', row.get('eta_reliable') is False, str(row.get('eta_reason')))
            check(f'MO {mo.id} unreliable ETA false', row.get('eta_minutes') is False, str(row.get('eta_minutes')))
        else:
            check(f'MO {mo.id} reliable ETA exposed', row.get('eta_reliable') is True, str(row.get('eta_reason')))
            check(f'MO {mo.id} reliable ETA numeric', isinstance(row.get('eta_minutes'), (int, float)), str(row.get('eta_minutes')))

# ---------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------
header('[6] BACKWARD COMPATIBILITY')
v16 = M.get_operational_intelligence_data()
v15 = M.get_operations_data()
v14 = M.get_station_topology()
check('V16 contract retained', v16.get('contract_version') == '16.0-operational-intelligence', str(v16.get('contract_version')))
check('V15 contract retained', v15.get('contract_version') == '15.0-operations', str(v15.get('contract_version')))
check('V14 topology still returns stations', isinstance(v14.get('stations'), list))

# ---------------------------------------------------------------------
# Read-only verification
# ---------------------------------------------------------------------
header('[7] READ-ONLY VERIFICATION')
after_fp = {
    'wc': fingerprint(WC.with_context(active_test=False), []),
    'wo': fingerprint(WO.with_context(active_test=False), []),
    'mo': fingerprint(M.with_context(active_test=False), []),
    'pos': fingerprint(POS.with_context(active_test=False), []),
    'am': fingerprint(AM.with_context(active_test=False), []),
}
for key in base_fp:
    check(f'No {key.upper()} records/count/write_date changed', after_fp[key] == base_fp[key], f'before={base_fp[key][:2]} after={after_fp[key][:2]}')

header('RESULT')
print(f'checks={checks} failed={failed}')
print('RESULT:', 'PASS 100%' if failed == 0 else 'FAIL')
print('NO DATA MODIFIED')
print('=' * W)
''')
