exec(r'''
from datetime import timedelta
from odoo import fields

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


header('CRYSTAL CLEAN V16 - OPERATIONAL INTELLIGENCE - READ ONLY')
print('Database :', env.cr.dbname)
print('Company  :', env.company.id, env.company.display_name)
print('User     :', env.user.id, env.user.display_name)
print('Timezone :', env.user.tz or 'UTC')

Module = env['ir.module.module']
mod = Module.search([('name', '=', 'car_wash_dashboard')], limit=1)
check('Module installed', bool(mod and mod.state == 'installed'), str(mod.state if mod else None))
check('Module version 18.0.16.0', bool(mod and mod.installed_version == '18.0.16.0'), str(mod.installed_version if mod else None))

M = env['mrp.production']
WO = env['mrp.workorder']
WC = env['mrp.workcenter']

check('V16 public API exists', hasattr(M, 'get_operational_intelligence_data'))
check('V15 operations API retained', hasattr(M, 'get_operations_data'))
check('V15 queue API retained', hasattr(M, 'get_queue_data'))
check('V15 station details API retained', hasattr(M, 'get_station_details'))

# ---------------------------------------------------------------------
# Read-only baseline fingerprints
# ---------------------------------------------------------------------

def fingerprint(model, domain=None):
    recs = model.search(domain or [])
    writes = [x.write_date for x in recs if x.write_date]
    return (len(recs), max(writes) if writes else False, tuple(recs.ids))

base_fp = {
    'wc': fingerprint(WC.with_context(active_test=False), []),
    'wo': fingerprint(WO.with_context(active_test=False), []),
    'mo': fingerprint(M.with_context(active_test=False), []),
}

# ---------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------
header('[1] CONTRACT')
data = M.get_operational_intelligence_data()

check('Contract is dict', isinstance(data, dict))
check('Contract version exact', data.get('contract_version') == '16.0-operational-intelligence', str(data.get('contract_version')))
check('Company exact', data.get('company_id') == env.company.id, str(data.get('company_id')))
check('Company name present', bool(data.get('company_name')))
check('Generated timestamp present', bool(data.get('generated_at')))
check('Timezone exact', data.get('timezone') == (env.user.tz or 'UTC'), str(data.get('timezone')))
check('KPIs dict', isinstance(data.get('kpis'), dict))
check('Stations list', isinstance(data.get('stations'), list))
check('Diagnostics dict', isinstance(data.get('diagnostics'), dict))
check('Semantics dict', isinstance(data.get('semantics'), dict))

for key in ('delay', 'queue_age', 'eta', 'throughput'):
    check(f'Semantics {key} documented', bool(data['semantics'].get(key)))

# ---------------------------------------------------------------------
# Expected raw sets
# ---------------------------------------------------------------------
now = fields.Datetime.now()
today_start, today_end, _ = M._cw_day_bounds(0)
hour_start = fields.Datetime.to_string(now - timedelta(minutes=60))
active_domain = M._cw_operations_workorder_domain()
active = WO.search(active_domain)

finished_base = [
    ('production_id.company_id', '=', env.company.id),
    ('state', '=', 'done'),
] + M._cw_workorder_wash_domain()
if 'date_finished' in WO._fields:
    done_today = WO.search(finished_base + [
        ('date_finished', '>=', today_start),
        ('date_finished', '<', today_end),
    ])
    done_hour = WO.search(finished_base + [
        ('date_finished', '>=', hour_start),
        ('date_finished', '<=', fields.Datetime.to_string(now)),
    ])
else:
    done_today = WO.browse()
    done_hour = WO.browse()

explicit_wc = M._cw_station_workcenters()
station_map = {row['station_id']: row for row in data['stations']}

check('Station IDs exact topology', set(station_map) == set(explicit_wc.ids), f"API={sorted(station_map)} DB={sorted(explicit_wc.ids)}")
check('Station count exact topology', len(data['stations']) == len(explicit_wc), f"{len(data['stations'])} vs {len(explicit_wc)}")

# ---------------------------------------------------------------------
# KPI exactness
# ---------------------------------------------------------------------
header('[2] KPI EXACTNESS')
k = data['kpis']
expected_running = active.filtered(lambda wo: wo.state == 'progress')
expected_queue = active.filtered(lambda wo: wo.state in ('pending', 'waiting', 'ready'))

check('KPI active_workorders exact', k.get('active_workorders') == len(active), f"{k.get('active_workorders')} vs {len(active)}")
check('KPI running_jobs exact', k.get('running_jobs') == len(expected_running), f"{k.get('running_jobs')} vs {len(expected_running)}")
check('KPI queued_jobs exact', k.get('queued_jobs') == len(expected_queue), f"{k.get('queued_jobs')} vs {len(expected_queue)}")
check('KPI completed_today exact', k.get('completed_today') == len(done_today), f"{k.get('completed_today')} vs {len(done_today)}")
check('KPI completed_last_60_minutes exact', k.get('completed_last_60_minutes') == len(done_hour), f"{k.get('completed_last_60_minutes')} vs {len(done_hour)}")

real_durations = [float(wo.duration or 0.0) for wo in done_today if 'duration' in wo._fields and (wo.duration or 0.0) > 0]
expected_avg = round((sum(real_durations) / len(real_durations)) if real_durations else 0.0, 2)
check('KPI avg completed duration exact', k.get('avg_completed_duration_today_minutes') == expected_avg, f"{k.get('avg_completed_duration_today_minutes')} vs {expected_avg}")

for key in ('active_workorders', 'running_jobs', 'queued_jobs', 'delayed_running_jobs', 'completed_today', 'completed_last_60_minutes'):
    check(f'KPI {key} nonnegative', (k.get(key) or 0) >= 0, str(k.get(key)))
for key in ('avg_completed_duration_today_minutes', 'max_queue_age_minutes', 'projected_system_clear_minutes'):
    check(f'KPI {key} nonnegative', (k.get(key) or 0) >= 0, str(k.get(key)))

# ---------------------------------------------------------------------
# Per-station exactness and ETA policy
# ---------------------------------------------------------------------
header('[3] STATION INTELLIGENCE')
all_delayed = []
all_queue_ages = []
reliable_clearances = []
unreliable_ids = []

for wc in explicit_wc:
    row = station_map.get(wc.id)
    check(f'Station {wc.id} payload exists', bool(row))
    if not row:
        continue

    station_active = active.filtered(lambda wo: wo.workcenter_id.id == wc.id)
    station_running = station_active.filtered(lambda wo: wo.state == 'progress')
    station_queue = station_active.filtered(lambda wo: wo.state in ('pending', 'waiting', 'ready'))
    capacity = max(int(wc.default_capacity or 1), 1)
    overloaded = len(station_running) > capacity

    check(f'{wc.display_name} station code', bool(row.get('station_code')))
    check(f'{wc.display_name} capacity exact', row.get('capacity') == capacity, f"{row.get('capacity')} vs {capacity}")
    check(f'{wc.display_name} occupancy exact', row.get('occupancy') == len(station_running), f"{row.get('occupancy')} vs {len(station_running)}")
    check(f'{wc.display_name} queue count exact', row.get('queue_count') == len(station_queue), f"{row.get('queue_count')} vs {len(station_queue)}")
    check(f'{wc.display_name} over capacity exact', row.get('over_capacity') is overloaded, f"{row.get('over_capacity')} vs {overloaded}")
    check(f'{wc.display_name} running ids exact', {r['workorder_id'] for r in row.get('running_jobs', [])} == set(station_running.ids), str(station_running.ids))
    check(f'{wc.display_name} queue ids exact', {r['workorder_id'] for r in row.get('queue', [])} == set(station_queue.ids), str(station_queue.ids))

    expected_done_today = done_today.filtered(lambda wo: wo.workcenter_id.id == wc.id)
    expected_done_hour = done_hour.filtered(lambda wo: wo.workcenter_id.id == wc.id)
    check(f'{wc.display_name} done today exact', row.get('done_today') == len(expected_done_today), f"{row.get('done_today')} vs {len(expected_done_today)}")
    check(f'{wc.display_name} done 60m exact', row.get('done_last_60_minutes') == len(expected_done_hour), f"{row.get('done_last_60_minutes')} vs {len(expected_done_hour)}")

    station_real = [float(wo.duration or 0.0) for wo in expected_done_today if 'duration' in wo._fields and (wo.duration or 0.0) > 0]
    station_expected = [float(wo.duration_expected or 0.0) for wo in expected_done_today if 'duration_expected' in wo._fields and (wo.duration_expected or 0.0) > 0]
    avg_real = round((sum(station_real) / len(station_real)) if station_real else 0.0, 2)
    avg_exp = round((sum(station_expected) / len(station_expected)) if station_expected else 0.0, 2)
    check(f'{wc.display_name} avg real exact', row.get('avg_duration_today_minutes') == avg_real, f"{row.get('avg_duration_today_minutes')} vs {avg_real}")
    check(f'{wc.display_name} avg expected exact', row.get('avg_expected_today_minutes') == avg_exp, f"{row.get('avg_expected_today_minutes')} vs {avg_exp}")

    running_rows = {r['workorder_id']: r for r in row.get('running_jobs', [])}
    station_delayed = []
    for wo in station_running:
        rr = running_rows[wo.id]
        expected = float(wo.duration_expected or 0.0) if 'duration_expected' in wo._fields else 0.0
        check(f'WO {wo.id} expected exact', rr.get('expected_minutes') == round(expected, 2), f"{rr.get('expected_minutes')} vs {round(expected,2)}")
        check(f'WO {wo.id} elapsed nonnegative', rr.get('elapsed_minutes', -1) >= 0, str(rr.get('elapsed_minutes')))
        check(f'WO {wo.id} remaining nonnegative', rr.get('remaining_minutes', -1) >= 0, str(rr.get('remaining_minutes')))
        check(f'WO {wo.id} delay nonnegative', rr.get('delay_minutes', -1) >= 0, str(rr.get('delay_minutes')))
        check(f'WO {wo.id} progress bounded', 0 <= rr.get('progress_ratio', -1) <= 100, str(rr.get('progress_ratio')))
        check(f'WO {wo.id} eta_known exact', rr.get('eta_known') is bool(expected > 0), f"{rr.get('eta_known')} vs {bool(expected > 0)}")
        check(f'WO {wo.id} over expected coherent', rr.get('over_expected') is bool(expected > 0 and rr.get('elapsed_minutes', 0) > expected), str(rr.get('over_expected')))
        if rr.get('over_expected'):
            station_delayed.append(wo.id)
            all_delayed.append(wo.id)

    check(f'{wc.display_name} delayed count exact', row.get('delayed_running_jobs') == len(station_delayed), f"{row.get('delayed_running_jobs')} vs {len(station_delayed)}")

    queue_rows = row.get('queue', [])
    positions = [q.get('position') for q in queue_rows]
    check(f'{wc.display_name} queue positions contiguous', positions == list(range(1, len(queue_rows) + 1)), str(positions))
    for q in queue_rows:
        check(f"Queue WO {q['workorder_id']} age nonnegative", q.get('queue_age_minutes', -1) >= 0, str(q.get('queue_age_minutes')))
        check(f"Queue WO {q['workorder_id']} expected nonnegative", q.get('expected_minutes', -1) >= 0, str(q.get('expected_minutes')))
        all_queue_ages.append(q.get('queue_age_minutes', 0))

    if overloaded:
        unreliable_ids.append(wc.id)
        check(f'{wc.display_name} projection disabled when overloaded', row.get('projection_reliable') is False)
        check(f'{wc.display_name} projection reason', row.get('projection_reason') == 'station_over_capacity', str(row.get('projection_reason')))
        check(f'{wc.display_name} clear ETA suppressed', row.get('projected_clear_minutes') is False, str(row.get('projected_clear_minutes')))
        for q in queue_rows:
            check(f"Queue WO {q['workorder_id']} start ETA suppressed", q.get('estimated_start_in_minutes') is False)
            check(f"Queue WO {q['workorder_id']} finish ETA suppressed", q.get('estimated_finish_in_minutes') is False)
            check(f"Queue WO {q['workorder_id']} estimate unreliable", q.get('estimate_reliable') is False)
    else:
        check(f'{wc.display_name} projection reliable', row.get('projection_reliable') is True)
        check(f'{wc.display_name} projection reason empty', row.get('projection_reason') == '', str(row.get('projection_reason')))
        check(f'{wc.display_name} clear ETA nonnegative', row.get('projected_clear_minutes', -1) >= 0, str(row.get('projected_clear_minutes')))
        reliable_clearances.append(float(row.get('projected_clear_minutes') or 0.0))
        for q in queue_rows:
            start = q.get('estimated_start_in_minutes')
            finish = q.get('estimated_finish_in_minutes')
            check(f"Queue WO {q['workorder_id']} start ETA numeric", isinstance(start, (int, float)), str(start))
            check(f"Queue WO {q['workorder_id']} finish ETA numeric", isinstance(finish, (int, float)), str(finish))
            check(f"Queue WO {q['workorder_id']} start ETA nonnegative", start >= 0, str(start))
            check(f"Queue WO {q['workorder_id']} finish >= start", finish >= start, f"{finish} vs {start}")
            check(f"Queue WO {q['workorder_id']} estimate reliable", q.get('estimate_reliable') is True)

# ---------------------------------------------------------------------
# Global diagnostic coherence
# ---------------------------------------------------------------------
header('[4] GLOBAL DIAGNOSTICS')
diag = data['diagnostics']
check('Projection policy exact', diag.get('projection_policy') == 'read_only_existing_mrp_assignment', str(diag.get('projection_policy')))
check('Unreliable station IDs exact', set(diag.get('unreliable_projection_station_ids') or []) == set(unreliable_ids), f"API={diag.get('unreliable_projection_station_ids')} expected={unreliable_ids}")
check('Overloaded station IDs exact', set(diag.get('overloaded_station_ids') or []) == set(unreliable_ids), f"API={diag.get('overloaded_station_ids')} expected={unreliable_ids}")
check('Delayed WO IDs exact', set(diag.get('delayed_workorder_ids') or []) == set(all_delayed), f"API={diag.get('delayed_workorder_ids')} expected={all_delayed}")
check('Global delayed count exact', k.get('delayed_running_jobs') == len(all_delayed), f"{k.get('delayed_running_jobs')} vs {len(all_delayed)}")
expected_max_age = round(max(all_queue_ages, default=0.0), 2)
check('Global max queue age exact', k.get('max_queue_age_minutes') == expected_max_age, f"{k.get('max_queue_age_minutes')} vs {expected_max_age}")
expected_clear = round(max(reliable_clearances), 2) if reliable_clearances else 0.0
check('Global projected clear exact', k.get('projected_system_clear_minutes') == expected_clear, f"{k.get('projected_system_clear_minutes')} vs {expected_clear}")
check('Global reliability exact', k.get('projection_reliable_for_all_stations') is (not unreliable_ids), f"{k.get('projection_reliable_for_all_stations')} vs {not unreliable_ids}")

# ---------------------------------------------------------------------
# V15 compatibility
# ---------------------------------------------------------------------
header('[5] V15 BACKWARD COMPATIBILITY')
v15_ops = M.get_operations_data()
v15_queue = M.get_queue_data()
check('V15 operations contract unchanged', v15_ops.get('contract_version') == '15.0-operations', str(v15_ops.get('contract_version')))
check('V15 queue contract unchanged', v15_queue.get('contract_version') == '15.0-operations', str(v15_queue.get('contract_version')))
check('V15 stations still available', isinstance(v15_ops.get('stations'), list))
check('V15 queue still available', isinstance(v15_ops.get('queue'), dict))

# ---------------------------------------------------------------------
# Read-only verification
# ---------------------------------------------------------------------
header('[6] READ-ONLY VERIFICATION')
after_fp = {
    'wc': fingerprint(WC.with_context(active_test=False), []),
    'wo': fingerprint(WO.with_context(active_test=False), []),
    'mo': fingerprint(M.with_context(active_test=False), []),
}
check('Workcenter fingerprint unchanged', after_fp['wc'] == base_fp['wc'], f"before={base_fp['wc'][:2]} after={after_fp['wc'][:2]}")
check('Workorder fingerprint unchanged', after_fp['wo'] == base_fp['wo'], f"before={base_fp['wo'][:2]} after={after_fp['wo'][:2]}")
check('Production fingerprint unchanged', after_fp['mo'] == base_fp['mo'], f"before={base_fp['mo'][:2]} after={after_fp['mo'][:2]}")

header('RESULT')
print(f'checks={checks} failed={failed}')
print('RESULT:', 'PASS 100%' if failed == 0 else 'FAIL')
print('NO DATA MODIFIED')
print('=' * W)
''')
