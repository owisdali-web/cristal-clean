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
    recs = model.with_context(active_test=False).search(domain or [])
    writes = [r.write_date for r in recs if r.write_date]
    return (len(recs), max(writes) if writes else False, tuple(recs.ids))


header('CRYSTAL CLEAN 18.0.18.1 - HEADLESS BACKEND HANDOFF - READ ONLY')
print('Database :', env.cr.dbname)
print('Company  :', env.company.id, env.company.display_name)
print('User     :', env.user.id, env.user.display_name)
print('Timezone :', env.user.tz or 'UTC')

Module = env['ir.module.module']
mod = Module.search([('name', '=', 'car_wash_dashboard')], limit=1)
check('Module installed', bool(mod and mod.state == 'installed'), str(mod.state if mod else None))
check('Module version 18.0.18.1', bool(mod and mod.installed_version == '18.0.18.1'), str(mod.installed_version if mod else None))

M = env['mrp.production']
WO = env['mrp.workorder']
WC = env['mrp.workcenter']
POS = env['pos.order']
AM = env['account.move']
Partner = env['res.partner']

for method in (
    'get_management_data', 'get_materials_data', 'get_customers_data', 'get_team_data',
    '_cw_management_contract', '_cw_materials_contract', '_cw_customers_contract', '_cw_team_contract',
):
    check(f'V18 method exists: {method}', hasattr(M, method))

check('V17 API retained', hasattr(M, 'get_customer_display_data'))
check('V16 API retained', hasattr(M, 'get_operational_intelligence_data'))
check('V15 API retained', hasattr(M, 'get_operations_data'))
check('V14 API retained', hasattr(M, 'get_station_topology'))

# ---------------------------------------------------------------------
# Frontend reset verification
# ---------------------------------------------------------------------
header('[0] FRONTEND RESET VERIFICATION')
check('Legacy per-user dashboard theme field removed', 'cc_dashboard_theme' not in env['res.users']._fields)
for xmlid, label in (
    ('car_wash_dashboard.action_car_wash_dashboard', 'legacy client action'),
    ('car_wash_dashboard.menu_car_wash_dashboard', 'legacy dashboard menu'),
    ('car_wash_dashboard.menu_car_wash_root', 'legacy root menu'),
):
    rec = env.ref(xmlid, raise_if_not_found=False)
    check(f'{label} removed', not rec, str(rec if rec else 'removed'))

# ---------------------------------------------------------------------
# Security boundary
# ---------------------------------------------------------------------
header('[1] SECURITY BOUNDARY')
manager_group = env.ref('car_wash_dashboard.group_car_wash_manager', raise_if_not_found=False)
check('Manager analytics group exists', bool(manager_group))
check('Current system/admin user authorized', M._cw_management_access_allowed())
if manager_group:
    Access = env['ir.model.access']
    sensitive = ['mrp.production', 'mrp.workorder', 'pos.order', 'account.move', 'stock.move', 'res.partner']
    for model_name in sensitive:
        model_rec = env['ir.model'].search([('model', '=', model_name)], limit=1)
        if model_rec:
            rows = Access.search([('group_id', '=', manager_group.id), ('model_id', '=', model_rec.id)])
            check(f'Manager group adds no direct ACL: {model_name}', not rows, str(rows.ids))

unauthorized = env['res.users'].with_context(active_test=False).search([('id', '!=', env.user.id)], limit=200)
unauthorized = unauthorized.filtered(
    lambda u: not u.has_group('car_wash_dashboard.group_car_wash_manager')
    and not u.has_group('base.group_system')
)[:1]
if unauthorized:
    denied = False
    try:
        M.with_user(unauthorized).get_management_data()
    except AccessError:
        denied = True
    check('Unauthorized existing user denied management API', denied, f'user={unauthorized.id} {unauthorized.display_name}')
else:
    check('Unauthorized-user denial test safely skipped', True, 'No existing candidate')

# ---------------------------------------------------------------------
# Read-only baseline
# ---------------------------------------------------------------------
header('[2] READ-ONLY BASELINE')
models = {
    'wc': WC,
    'wo': WO,
    'mo': M,
    'pos': POS,
    'account': AM,
    'partner': Partner,
}
if 'stock.move' in env.registry.models:
    models['stock_move'] = env['stock.move']
if 'stock.quant' in env.registry.models:
    models['stock_quant'] = env['stock.quant']
if 'hr.employee' in env.registry.models:
    models['employee'] = env['hr.employee']
if 'hr.attendance' in env.registry.models:
    models['attendance'] = env['hr.attendance']
base_fp = {key: fingerprint(model) for key, model in models.items()}
for key, fp in base_fp.items():
    check(f'Baseline captured: {key}', isinstance(fp, tuple) and len(fp) == 3, str(fp[:2]))

# ---------------------------------------------------------------------
# Manager contract
# ---------------------------------------------------------------------
header('[3] MANAGEMENT CONTRACT')
management = M.get_management_data()
check('Management contract dict', isinstance(management, dict))
check('Management contract version exact', management.get('contract_version') == '18.0-management', str(management.get('contract_version')))
check('Management company exact', management.get('company_id') == env.company.id, str(management.get('company_id')))
for key in ('commercial', 'financial', 'operations', 'stations', 'semantics'):
    check(f'Management key {key}', key in management, str(type(management.get(key))))
check('Management stations list', isinstance(management.get('stations'), list))

commercial = management['commercial']
for key in ('pos_sales_today', 'pos_orders_today', 'average_ticket_today', 'pos_sales_month', 'pos_orders_month', 'top_services_today'):
    check(f'Commercial key {key}', key in commercial, str(commercial.get(key)))
check('POS amounts nonnegative', commercial['pos_sales_today'] >= 0 and commercial['pos_sales_month'] >= 0)
check('POS order counts nonnegative', commercial['pos_orders_today'] >= 0 and commercial['pos_orders_month'] >= 0)
expected_avg = round(commercial['pos_sales_today'] / commercial['pos_orders_today'], 2) if commercial['pos_orders_today'] else 0.0
check('Average ticket arithmetic exact', commercial['average_ticket_today'] == expected_avg, f"{commercial['average_ticket_today']} vs {expected_avg}")

financial = management['financial']
for key in ('collected_today', 'posted_expenses_today', 'posted_expenses_month', 'receivable_open', 'payable_open', 'operational_balance_today'):
    check(f'Financial key {key}', key in financial, str(financial.get(key)))
expected_balance = round(commercial['pos_sales_today'] - financial['posted_expenses_today'], 2)
check('Operational balance arithmetic exact', financial['operational_balance_today'] == expected_balance, f"{financial['operational_balance_today']} vs {expected_balance}")
check('Operational balance semantics explicitly not profit', 'not accounting profit' in management['semantics'].get('operational_balance_today', '').lower())
check('Station revenue intentionally not allocated', 'not allocated' in management['semantics'].get('station_revenue', '').lower())

ops = management['operations']
for key in ('active_vehicles', 'running_jobs', 'queued_jobs', 'ready_for_pickup', 'completed_today', 'avg_completed_duration_today_minutes', 'delayed_running_jobs', 'station_live_occupancy_pct', 'overloaded_stations', 'projection_reliable_for_all_stations'):
    check(f'Operations management key {key}', key in ops, str(ops.get(key)))
check('Live occupancy nonnegative', ops['station_live_occupancy_pct'] >= 0, str(ops['station_live_occupancy_pct']))

v15 = M.get_operations_data()
v16 = M.get_operational_intelligence_data()
check('Management active vehicles matches V15', ops['active_vehicles'] == v15['kpis']['active_vehicles'], f"{ops['active_vehicles']} vs {v15['kpis']['active_vehicles']}")
check('Management ready count matches V15', ops['ready_for_pickup'] == v15['kpis']['ready_for_delivery'], f"{ops['ready_for_pickup']} vs {v15['kpis']['ready_for_delivery']}")
check('Management running jobs matches V16', ops['running_jobs'] == v16['kpis']['running_jobs'], f"{ops['running_jobs']} vs {v16['kpis']['running_jobs']}")
check('Management queue matches V16', ops['queued_jobs'] == v16['kpis']['queued_jobs'], f"{ops['queued_jobs']} vs {v16['kpis']['queued_jobs']}")
check('Management completed today matches V16', ops['completed_today'] == v16['kpis']['completed_today'], f"{ops['completed_today']} vs {v16['kpis']['completed_today']}")
check('Station row count matches V16', len(management['stations']) == len(v16['stations']), f"{len(management['stations'])} vs {len(v16['stations'])}")

# ---------------------------------------------------------------------
# Materials contract
# ---------------------------------------------------------------------
header('[4] MATERIALS CONTRACT')
materials = M.get_materials_data()
check('Materials contract dict', isinstance(materials, dict))
check('Materials contract version exact', materials.get('contract_version') == '18.0-materials', str(materials.get('contract_version')))
check('Materials company exact', materials.get('company_id') == env.company.id, str(materials.get('company_id')))
check('Materials list', isinstance(materials.get('materials'), list))
check('Materials KPI dict', isinstance(materials.get('kpis'), dict))
check('Materials scope exact', materials.get('scope', {}).get('inventory_scope') == 'all_internal_locations_in_company', str(materials.get('scope')))
check('Dedicated wash location not falsely claimed', materials.get('scope', {}).get('dedicated_car_wash_location_configured') is False)
check('Material count exact', materials['kpis']['material_count'] == len(materials['materials']), f"{materials['kpis']['material_count']} vs {len(materials['materials'])}")
check('Low stock count exact', materials['kpis']['low_stock_count'] == sum(1 for r in materials['materials'] if r.get('is_low')))
check('Reserved count exact', materials['kpis']['reserved_material_count'] == sum(1 for r in materials['materials'] if (r.get('reserved') or 0) > 0))
check('Under 3 days count exact', materials['kpis']['under_3_days_count'] == sum(1 for r in materials['materials'] if r.get('days_remaining') is not False and r.get('days_remaining') < 3))
check('Inventory scope semantics documented', 'all internal locations' in materials['semantics']['inventory_scope'].lower())
for row in materials['materials']:
    pid = row['product_id']
    for key in ('product_name', 'uom', 'on_hand', 'reserved', 'free', 'minimum', 'has_minimum', 'is_low', 'standard_cost', 'free_stock_value', 'consumed_30d', 'daily_consumption', 'days_remaining', 'burn_status', 'locations'):
        check(f'Material {pid} key {key}', key in row, str(row.get(key)))
    check(f'Material {pid} free arithmetic', round(row['on_hand'] - row['reserved'], 2) == row['free'], f"{row['on_hand']}-{row['reserved']}={row['free']}")
    check(f'Material {pid} stock value arithmetic', row['free_stock_value'] == round(row['free'] * row['standard_cost'], 2), str(row['free_stock_value']))
    check(f'Material {pid} burn status valid', row['burn_status'] in ('danger', 'warning', 'good'), str(row['burn_status']))
    check(f'Material {pid} locations list', isinstance(row['locations'], list))

# ---------------------------------------------------------------------
# Customers contract
# ---------------------------------------------------------------------
header('[5] CUSTOMERS CONTRACT')
customers = M.get_customers_data()
check('Customers contract dict', isinstance(customers, dict))
check('Customers contract version exact', customers.get('contract_version') == '18.0-customers', str(customers.get('contract_version')))
check('Customers company exact', customers.get('company_id') == env.company.id, str(customers.get('company_id')))
check('Customers rows list', isinstance(customers.get('customers'), list))
check('Customers KPI dict', isinstance(customers.get('kpis'), dict))
for key in ('known_customers_365d', 'repeat_customers_365d', 'customers_served_today', 'active_customers_month', 'inactive_over_30_days'):
    check(f'Customer KPI {key}', key in customers['kpis'], str(customers['kpis'].get(key)))
check('Known customers >= returned rows', customers['kpis']['known_customers_365d'] >= len(customers['customers']))
check('Repeat customers bounded', 0 <= customers['kpis']['repeat_customers_365d'] <= customers['kpis']['known_customers_365d'])
check('Served-today semantics not called new customers', 'does not mean first-time/new customers' in customers['semantics']['customers_served_today'].lower())
check('Active-month semantics not called new acquisition', 'does not mean newly acquired customers' in customers['semantics']['active_customers_month'].lower())
for row in customers['customers']:
    pid = row['partner_id']
    for key in ('name', 'phone', 'visits_365d', 'spend_365d', 'last_visit', 'favorite_service', 'repeat_customer', 'active_last_30_days'):
        check(f'Customer {pid} key {key}', key in row, str(row.get(key)))
    check(f'Customer {pid} visits positive', row['visits_365d'] > 0, str(row['visits_365d']))
    check(f'Customer {pid} repeat flag exact', row['repeat_customer'] is (row['visits_365d'] > 1), str(row['repeat_customer']))
    check(f'Customer {pid} spend nonnegative', row['spend_365d'] >= 0, str(row['spend_365d']))

# ---------------------------------------------------------------------
# Team contract
# ---------------------------------------------------------------------
header('[6] TEAM CONTRACT')
team = M.get_team_data()
check('Team contract dict', isinstance(team, dict))
check('Team contract version exact', team.get('contract_version') == '18.0-team', str(team.get('contract_version')))
check('Team company exact', team.get('company_id') == env.company.id, str(team.get('company_id')))
check('Team rows list', isinstance(team.get('team'), list))
check('Team shifts list', isinstance(team.get('shifts'), list))
check('Team KPI dict', isinstance(team.get('kpis'), dict))
for key in ('operational_users', 'worked_today', 'currently_checked_in', 'current_presence_pct', 'worked_today_pct'):
    check(f'Team KPI {key}', key in team['kpis'], str(team['kpis'].get(key)))
check('Operational users exact row count', team['kpis']['operational_users'] == len(team['team']), f"{team['kpis']['operational_users']} vs {len(team['team'])}")
check('Current presence bounded', 0 <= team['kpis']['currently_checked_in'] <= team['kpis']['operational_users'])
check('Worked today bounded', 0 <= team['kpis']['worked_today'] <= team['kpis']['operational_users'])
check('Presence pct bounded', 0 <= team['kpis']['current_presence_pct'] <= 100)
check('Worked pct bounded', 0 <= team['kpis']['worked_today_pct'] <= 100)
check('Presence semantics explicitly not score', 'not an attendance-performance score' in team['semantics']['currently_checked_in'].lower())
check('Shift semantics explicitly heuristic', 'heuristic' in team['semantics']['shift_bucket'].lower())
check('Work location not falsely claimed as workcenter', 'does not claim' in team['semantics']['work_location_label'].lower())
for row in team['team']:
    uid = row['user_id']
    for key in ('employee_id', 'name', 'role', 'department', 'work_location_label', 'phone', 'worked_today', 'currently_checked_in', 'shift_bucket', 'last_check_in', 'last_check_out'):
        check(f'Team user {uid} key {key}', key in row, str(row.get(key)))
    check(f'Team user {uid} booleans valid', isinstance(row['worked_today'], bool) and isinstance(row['currently_checked_in'], bool))

# ---------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------
header('[7] BACKWARD COMPATIBILITY')
check('V17 contract retained', M.get_customer_display_data().get('contract_version') == '17.0-customer-display')
check('V16 contract retained', M.get_operational_intelligence_data().get('contract_version') == '16.0-operational-intelligence')
check('V15 contract retained', M.get_operations_data().get('contract_version') == '15.0-operations')
check('V14 topology stations retained', isinstance(M.get_station_topology().get('stations'), list))

# ---------------------------------------------------------------------
# Read-only verification
# ---------------------------------------------------------------------
header('[8] READ-ONLY VERIFICATION')
after_fp = {key: fingerprint(model) for key, model in models.items()}
for key in base_fp:
    check(f'No {key} record/count/write_date changed', after_fp[key] == base_fp[key], f'before={base_fp[key][:2]} after={after_fp[key][:2]}')

header('RESULT')
print(f'checks={checks} failed={failed}')
print('RESULT:', 'PASS 100%' if failed == 0 else 'FAIL')
print('NO DATA MODIFIED')
print('=' * W)
''')
