exec(r'''
from collections import defaultdict

W = 150
checks = 0
failed = 0


def check(label, condition, detail=''):
    global checks, failed
    checks += 1
    ok = bool(condition)
    if not ok:
        failed += 1
    print(f"{label:<92} {'PASS' if ok else 'FAIL'} {detail}")
    return ok


def hr(title):
    print('\n' + '=' * W)
    print(title)
    print('=' * W)


hr('CRYSTAL CLEAN V15 - OPERATIONS BACKEND CONTRACT - READ ONLY TEST')

M = env['mrp.production']
WO = env['mrp.workorder']
WC = env['mrp.workcenter']
Module = env['ir.module.module']
company = env.company

mod = Module.search([('name', '=', 'car_wash_dashboard')], limit=1)
check('Module installed', bool(mod and mod.state == 'installed'), mod.state if mod else 'NOT FOUND')
check('Module version is 18.0.15.0', bool(mod and mod.installed_version == '18.0.15.0'), mod.installed_version if mod else '-')

# Fingerprints prove these API calls do not mutate operational records.
def fingerprint():
    data = {}
    for model_name in ['mrp.production', 'mrp.workorder', 'mrp.workcenter', 'pos.order', 'stock.move', 'account.move']:
        if model_name not in env.registry.models:
            continue
        model = env[model_name]
        domain = []
        if 'company_id' in model._fields:
            domain = ['|', ('company_id', '=', False), ('company_id', '=', company.id)]
        rows = model.with_context(active_test=False).search(domain)
        write_dates = [x for x in rows.mapped('write_date') if x]
        data[model_name] = (len(rows), max(write_dates) if write_dates else False)
    return data

before = fingerprint()

hr('[1] OPERATIONS CONTRACT')
ops = M.get_operations_data()

check('operations is dict', isinstance(ops, dict))
check('contract_version', ops.get('contract_version') == '15.0-operations', ops.get('contract_version'))
check('company_id matches current company', ops.get('company_id') == company.id, str(ops.get('company_id')))
check('company_name populated', bool(ops.get('company_name')), str(ops.get('company_name')))
check('generated_at populated', bool(ops.get('generated_at')), str(ops.get('generated_at')))
check('timezone populated', bool(ops.get('timezone')), str(ops.get('timezone')))
check('kpis is dict', isinstance(ops.get('kpis'), dict))
check('stations is list', isinstance(ops.get('stations'), list))
check('queue is dict', isinstance(ops.get('queue'), dict))
check('cars is list', isinstance(ops.get('cars'), list))
check('diagnostics is dict', isinstance(ops.get('diagnostics'), dict))
check('domains is dict', isinstance(ops.get('domains'), dict))

stations = ops.get('stations') or []
kpis = ops.get('kpis') or {}
queue = ops.get('queue') or {}

explicit_wcs = WC.search([
    ('active', '=', True),
    ('cc_is_car_wash_station', '=', True),
    '|', ('company_id', '=', False), ('company_id', '=', company.id),
], order='cc_station_order,sequence,id')

check('Station count equals explicit topology', len(stations) == len(explicit_wcs), f"api={len(stations)} db={len(explicit_wcs)}")
check('Station IDs equal explicit topology', {x['id'] for x in stations} == set(explicit_wcs.ids), str([x['id'] for x in stations]))
check('Station IDs are unique', len({x['id'] for x in stations}) == len(stations))
check('Station codes are unique', len({x['station_code'] for x in stations}) == len(stations))
check('Stations sorted by display_order/id', [(x['display_order'], x['id']) for x in stations] == sorted((x['display_order'], x['id']) for x in stations))

allowed_runtime = {'available', 'queued', 'busy', 'overloaded', 'maintenance', 'closed'}
allowed_manual = {'open', 'maintenance', 'closed'}
allowed_kind = {'general', 'auto', 'polish'}

for st in stations:
    prefix = f"Station {st['station_code']} ({st['id']})"
    check(prefix + ' explicit topology', st.get('topology_explicit') is True)
    check(prefix + ' runtime state valid', st.get('runtime_state') in allowed_runtime, st.get('runtime_state'))
    check(prefix + ' manual state valid', st.get('manual_state') in allowed_manual, st.get('manual_state'))
    check(prefix + ' kind valid', st.get('kind') in allowed_kind, st.get('kind'))
    check(prefix + ' capacity >= 1', st.get('capacity', 0) >= 1, str(st.get('capacity')))
    check(prefix + ' occupancy >= 0', st.get('occupancy', -1) >= 0, str(st.get('occupancy')))
    check(prefix + ' queue_count >= 0', st.get('queue_count', -1) >= 0, str(st.get('queue_count')))
    check(prefix + ' load = occupancy + queue', st.get('load') == st.get('occupancy') + st.get('queue_count'), f"{st.get('load')} vs {st.get('occupancy')}+{st.get('queue_count')}")
    check(prefix + ' available capacity formula', st.get('available_capacity') == max(st.get('capacity') - st.get('occupancy'), 0))
    check(prefix + ' over_capacity formula', st.get('over_capacity') == (st.get('occupancy') > st.get('capacity')))
    if st.get('manual_state') == 'maintenance':
        check(prefix + ' maintenance precedence', st.get('runtime_state') == 'maintenance')
    if st.get('manual_state') == 'closed':
        check(prefix + ' closed precedence', st.get('runtime_state') == 'closed')
    if st.get('runtime_state') == 'overloaded':
        check(prefix + ' overloaded really exceeds capacity', st.get('occupancy') > st.get('capacity'))

check('KPI station_total', kpis.get('station_total') == len(stations), str(kpis.get('station_total')))
check('KPI available count', kpis.get('station_available') == sum(1 for s in stations if s['runtime_state'] == 'available'))
check('KPI busy count', kpis.get('station_busy') == sum(1 for s in stations if s['runtime_state'] in ('busy', 'overloaded')))
check('KPI maintenance count', kpis.get('station_maintenance') == sum(1 for s in stations if s['runtime_state'] == 'maintenance'))
check('KPI closed count', kpis.get('station_closed') == sum(1 for s in stations if s['runtime_state'] == 'closed'))
check('KPI overloaded count', kpis.get('station_overloaded') == sum(1 for s in stations if s['runtime_state'] == 'overloaded'))

hr('[2] QUEUE CONTRACT')
qrows = queue.get('rows') or []
by_station = queue.get('by_station') or []
check('Queue total matches rows', queue.get('total') == len(qrows), f"{queue.get('total')} vs {len(qrows)}")
check('Queue total matches station queue counters', queue.get('total') == sum(s.get('queue_count', 0) for s in stations))
check('Queue by_station has one bucket per station', len(by_station) == len(stations), f"{len(by_station)} vs {len(stations)}")
check('Queue rows have unique Work Order IDs', len({r['workorder_id'] for r in qrows}) == len(qrows))

station_map = {s['id']: s for s in stations}
rows_by_station = defaultdict(list)
for row in qrows:
    rows_by_station[row.get('station_id')].append(row)
    wo = WO.browse(row['workorder_id']).exists()
    check(f"Queue WO {row['workorder_id']} exists", bool(wo))
    if not wo:
        continue
    check(f"Queue WO {wo.id} state authoritative", row.get('mrp_state') == wo.state, f"api={row.get('mrp_state')} db={wo.state}")
    check(f"Queue WO {wo.id} is waiting state", wo.state in ('pending', 'waiting', 'ready'), wo.state)
    check(f"Queue WO {wo.id} production match", row.get('production_id') == wo.production_id.id)
    check(f"Queue WO {wo.id} station match", row.get('station_id') == wo.workcenter_id.id)
    check(f"Queue WO {wo.id} belongs explicit topology", row.get('station_id') in station_map)
    check(f"Queue WO {wo.id} nonnegative age", row.get('queue_age_minutes', -1) >= 0)
    check(f"Queue WO {wo.id} has vehicle payload", isinstance(row.get('vehicle'), dict) and row['vehicle'].get('id') == wo.production_id.id)

for bucket in by_station:
    station_id = bucket.get('station_id')
    expected = rows_by_station.get(station_id, [])
    check(f"Queue bucket {station_id} count", bucket.get('count') == len(expected), f"{bucket.get('count')} vs {len(expected)}")
    positions = [r.get('station_position') for r in bucket.get('rows', [])]
    check(f"Queue bucket {station_id} positions sequential", positions == list(range(1, len(positions) + 1)), str(positions))

queued_all = WO.search(M._cw_operations_workorder_domain(states=['pending', 'waiting', 'ready']))
expected_queue_unassigned = queued_all.filtered(lambda w: not w.workcenter_id).ids
expected_queue_foreign = queued_all.filtered(lambda w: w.workcenter_id and w.workcenter_id.id not in set(explicit_wcs.ids)).ids
check('Queue unassigned diagnostics exact', set(queue.get('unassigned_workorder_ids') or []) == set(expected_queue_unassigned), str(expected_queue_unassigned))
check('Queue foreign-station diagnostics exact', set(queue.get('foreign_station_workorder_ids') or []) == set(expected_queue_foreign), str(expected_queue_foreign))

hr('[3] VEHICLES / LIVE STATE')
active_domain = M._cw_wash_domain() + [('state', 'not in', ['done', 'cancel'])]
active_mos = M.search(active_domain)
check('Active vehicle count equals active wash MOs', len(ops.get('cars') or []) == len(active_mos), f"api={len(ops.get('cars') or [])} db={len(active_mos)}")
check('Active vehicle IDs unique', len({c['id'] for c in ops.get('cars') or []}) == len(ops.get('cars') or []))
check('Active vehicle IDs match DB', {c['id'] for c in ops.get('cars') or []} == set(active_mos.ids))
check('Ready delivery KPI', kpis.get('ready_for_delivery') == len(ops.get('ready_delivery') or []))

progress_domain = M._cw_operations_workorder_domain(states=['progress'])
progress_wos = WO.search(progress_domain)
check('In-service KPI uses distinct MOs', kpis.get('in_service') == len(set(progress_wos.mapped('production_id').ids)), f"api={kpis.get('in_service')} db={len(set(progress_wos.mapped('production_id').ids))}")
check('Waiting-for-station KPI equals queue', kpis.get('waiting_for_station') == queue.get('total'))

expected_orphans = WO.search(M._cw_operations_workorder_domain()).filtered(
    lambda w: w.workcenter_id and w.workcenter_id.id not in set(explicit_wcs.ids)
).ids
expected_unassigned = WO.search(M._cw_operations_workorder_domain()).filtered(lambda w: not w.workcenter_id).ids
check('Orphan diagnostics exact', set(ops['diagnostics'].get('orphan_active_workorder_ids') or []) == set(expected_orphans), str(expected_orphans))
check('Unassigned diagnostics exact', set(ops['diagnostics'].get('unassigned_active_workorder_ids') or []) == set(expected_unassigned), str(expected_unassigned))
check('Overloaded diagnostics exact', set(ops['diagnostics'].get('overloaded_station_ids') or []) == {s['id'] for s in stations if s['runtime_state'] == 'overloaded'})

hr('[4] SPLIT API CONTRACTS')
queue_api = M.get_queue_data()
check('get_queue_data contract version', queue_api.get('contract_version') == '15.0-operations')
check('get_queue_data company', queue_api.get('company_id') == company.id)
check('get_queue_data queue total', queue_api.get('queue', {}).get('total') == queue.get('total'))
check('get_queue_data same queued Work Orders', {r['workorder_id'] for r in queue_api.get('queue', {}).get('rows', [])} == {r['workorder_id'] for r in qrows})

for st in stations:
    detail = M.get_station_details(st['id'])
    check(f"Station detail {st['station_code']} found", detail.get('found') is True)
    if not detail.get('found'):
        continue
    check(f"Station detail {st['station_code']} ID", detail.get('station', {}).get('id') == st['id'])
    expected_active = WO.search(M._cw_operations_workorder_domain(station_id=st['id']))
    check(f"Station detail {st['station_code']} active WO IDs", set(detail.get('active_workorder_ids') or []) == set(expected_active.ids))
    expected_progress = expected_active.filtered(lambda w: w.state == 'progress')
    check(f"Station detail {st['station_code']} running jobs", {r['workorder_id'] for r in detail.get('running_jobs') or []} == set(expected_progress.ids))
    expected_queue = expected_active.filtered(lambda w: w.state in ('pending', 'waiting', 'ready'))
    check(f"Station detail {st['station_code']} queue", {r['workorder_id'] for r in detail.get('queue', {}).get('rows', [])} == set(expected_queue.ids))

invalid = M.get_station_details('not-an-id')
check('Invalid station ID safely rejected', invalid == {'found': False, 'reason': 'invalid_station_id'}, str(invalid))
missing = M.get_station_details(999999999)
check('Missing station safely rejected', missing == {'found': False, 'reason': 'station_not_found'}, str(missing))

hr('[5] CURRENT DASHBOARD BACKWARD COMPATIBILITY')
legacy = M.get_dashboard_data()
check('Legacy dashboard still returns dict', isinstance(legacy, dict))
check('Legacy dashboard version moved to V15', legacy.get('dashboard_version') == '15.0-operations-contract', str(legacy.get('dashboard_version')))
check('Legacy dashboard keeps workcenter_load', isinstance(legacy.get('workcenter_load'), list))
check('Legacy dashboard station IDs preserve topology', {r.get('id') for r in legacy.get('workcenter_load') or []} == set(explicit_wcs.ids))
check('Operations API excludes finance page', 'finance_page' not in ops)
check('Operations API excludes materials payload', 'materials' not in ops)
check('Operations API excludes HR/customer analytics', 'client_hr_page' not in ops and 'customer_page' not in ops)
check('Operations API excludes maintenance payload', 'maintenance_page' not in ops)

hr('[6] READ-ONLY GUARANTEE')
after = fingerprint()
for model_name, before_value in before.items():
    check(f'No mutation: {model_name}', after.get(model_name) == before_value, f"before={before_value} after={after.get(model_name)}")

hr('RESULT')
print(f'checks={checks} failed={failed}')
print('RESULT: PASS 100%' if failed == 0 else 'RESULT: FAIL')
print('NO DATA MODIFIED')
print('=' * W)
''')
