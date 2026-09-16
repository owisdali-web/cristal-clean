# Run inside Odoo Shell AFTER upgrading car_wash_dashboard to 18.0.14.0.
# READ ONLY: this script does not create, write, unlink or commit anything.

exec(r'''
W = 150
checks = []


def check(name, condition, detail=''):
    ok = bool(condition)
    checks.append((name, ok, detail))
    print(('%-72s %s %s') % (name, 'PASS' if ok else 'FAIL', detail or ''))
    return ok


def hr(title):
    print('\n' + '=' * W)
    print(title)
    print('=' * W)


hr('CRYSTAL CLEAN 18.0.14.0 - STATION TOPOLOGY VALIDATION - READ ONLY')

company = env['res.company'].search([('name', 'ilike', 'كريستال')], limit=1) or env.company
ctx = dict(env.context, allowed_company_ids=[company.id])
WC = env['mrp.workcenter'].with_company(company).with_context(ctx, active_test=False)
WO = env['mrp.workorder'].with_company(company).with_context(ctx)
MO = env['mrp.production'].with_company(company).with_context(ctx)
Module = env['ir.module.module']

module = Module.search([('name', '=', 'car_wash_dashboard')], limit=1)
check('Module installed', module.state == 'installed', 'state=%s' % (module.state if module else 'missing'))
check('Module version 18.0.14.0', module.installed_version == '18.0.14.0', 'version=%s' % (module.installed_version if module else 'missing'))

expected = {
    11: ('A1', 'CC-WC-A1', 'A1', 10, 'general'),
    2: ('A2', 'CC-WC-A2', 'A2', 20, 'general'),
    3: ('A3', 'CC-WC-A3', 'A3', 30, 'general'),
    4: ('A4', 'CC-WC-A4', 'A4', 40, 'general'),
    5: ('A5', 'CC-WC-A5', 'A5', 50, 'general'),
    6: ('A6', 'CC-WC-A6', 'A6', 60, 'general'),
    7: ('A7', 'CC-WC-A7', 'A7', 70, 'general'),
    12: ('A8', 'CC-WC-A8', 'A8', 80, 'general'),
    8: ('A9 - الغسيل الآلي', 'CC-WC-A9-AUTO', 'A9', 90, 'auto'),
    1: ('A10 - اللمعة', 'CC-WC-A10-POLISH', 'A10', 100, 'polish'),
}

hr('1) NATIVE WORKCENTER IDENTITY + NEW TOPOLOGY FIELDS')
stations = WC.browse(list(expected)).exists()
check('All 10 original Work Center IDs still exist', set(stations.ids) == set(expected), 'ids=%s' % sorted(stations.ids))

for wc_id, (name, native_code, station_code, station_order, kind) in expected.items():
    wc = WC.browse(wc_id)
    check('WC %s native name unchanged' % wc_id, wc.name == name, 'name=%s' % wc.name)
    check('WC %s native code unchanged' % wc_id, wc.code == native_code, 'code=%s' % wc.code)
    check('WC %s marked as wash station' % wc_id, wc.cc_is_car_wash_station is True)
    check('WC %s station code' % wc_id, wc.cc_station_code == station_code, 'station_code=%s' % wc.cc_station_code)
    check('WC %s station order' % wc_id, wc.cc_station_order == station_order, 'order=%s' % wc.cc_station_order)
    check('WC %s station kind' % wc_id, wc.cc_station_kind == kind, 'kind=%s' % wc.cc_station_kind)
    check('WC %s manual state open' % wc_id, wc.cc_station_manual_state == 'open', 'state=%s' % wc.cc_station_manual_state)

hr('2) BACKEND TOPOLOGY CONTRACT')
payload = MO.get_station_topology()
rows = payload.get('stations', [])
row_ids = [r.get('id') for r in rows]
row_codes = [r.get('station_code') for r in rows]
check('Topology returns exactly 10 stations', len(rows) == 10, 'count=%s' % len(rows))
check('Topology Work Center IDs are exact', set(row_ids) == set(expected), 'ids=%s' % row_ids)
check('Topology stable order A1..A10', row_codes == ['A%s' % i for i in range(1, 11)], 'codes=%s' % row_codes)
check('A9 kind comes from backend topology', next((r.get('kind') for r in rows if r.get('station_code') == 'A9'), None) == 'auto')
check('A10 kind comes from backend topology', next((r.get('kind') for r in rows if r.get('station_code') == 'A10'), None) == 'polish')
check('All topology rows explicit', all(r.get('topology_explicit') for r in rows))
check('Runtime state values valid', all(r.get('runtime_state') in {'available', 'queued', 'busy', 'overloaded', 'maintenance', 'closed'} for r in rows))
check('Capacity/occupancy fields present', all({'capacity', 'occupancy', 'queue_count', 'over_capacity'} <= set(r) for r in rows))

hr('3) DASHBOARD BACKWARD COMPATIBILITY')
dash = MO.get_dashboard_data()
check('Dashboard V14 contract active', dash.get('dashboard_version') == '14.0-station-topology', 'version=%s' % dash.get('dashboard_version'))
check('Legacy workcenter_load still returned', len(dash.get('workcenter_load', [])) == 10, 'count=%s' % len(dash.get('workcenter_load', [])))
check('Dashboard workcenter IDs match topology', set(r.get('id') for r in dash.get('workcenter_load', [])) == set(expected))
check('Station overload KPI present', 'station_overloaded' in dash)
check('Station maintenance KPI present', 'station_maintenance' in dash)
check('Station closed KPI present', 'station_closed' in dash)

hr('4) HISTORICAL SAFETY')
# Baseline counts from the pre-upgrade read-only diagnostic. Counts may only stay
# equal or increase if normal business activity continued after that snapshot.
baseline_history = {11: 0, 2: 25, 3: 5, 4: 5, 5: 2, 6: 2, 7: 4, 12: 0, 8: 23, 1: 3}
for wc_id, minimum in baseline_history.items():
    count = WO.with_context(active_test=False).search_count([('workcenter_id', '=', wc_id)])
    check('WC %s historical Work Orders preserved' % wc_id, count >= minimum, 'count=%s baseline=%s' % (count, minimum))

hr('5) CURRENT SERVICE BOM ROUTING - OBSERVATION ONLY')
services = MO._cw_service_templates()
ops = env['mrp.routing.workcenter'].search([
    ('bom_id.product_tmpl_id', 'in', services.ids),
])
print('Current service templates:', [(r.id, r.display_name) for r in services])
print('Current routing operations:', [(op.id, op.name, op.workcenter_id.id, op.workcenter_id.display_name) for op in ops])
print('NOTE: V14 does not rewrite BOMs, routing operations or alternative Work Centers.')

hr('RESULT')
failed = [name for name, ok, detail in checks if not ok]
print('checks=%s failed=%s' % (len(checks), len(failed)))
if failed:
    print('RESULT: FAIL')
    for name in failed:
        print(' -', name)
else:
    print('RESULT: PASS 100%')
print('NO DATA MODIFIED')
print('=' * W)
''')
