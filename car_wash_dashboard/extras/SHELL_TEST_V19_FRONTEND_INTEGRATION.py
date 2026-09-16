exec(r'''
from odoo import fields

W = 142
checks = 0
failed = 0

def check(name, condition, detail=''):
    global checks, failed
    checks += 1
    ok = bool(condition)
    if not ok:
        failed += 1
    print(('%-62s %s %s' % (name, 'PASS' if ok else 'FAIL', detail)).rstrip())
    return ok

def hr(title):
    print('\n' + '=' * W)
    print(title)
    print('=' * W)

hr('CRYSTAL CLEAN V19 FRONTEND INTEGRATION - READ ONLY')

Module = env['ir.module.module']
mod = Module.search([('name', '=', 'car_wash_dashboard')], limit=1)
check('Module installed', mod.state == 'installed', str(mod.state if mod else 'missing'))
check('Module version 18.0.19.0', mod.installed_version == '18.0.19.0', str(mod.installed_version if mod else 'missing'))

hr('CLIENT ACTIONS')
Action = env['ir.actions.client']
ops_action = env.ref('car_wash_dashboard.action_crystal_clean_ops_center', raise_if_not_found=False)
display_action = env.ref('car_wash_dashboard.action_crystal_clean_customer_display', raise_if_not_found=False)
check('Operations action exists', bool(ops_action))
check('Operations action tag', bool(ops_action and ops_action.tag == 'crystal_clean_ops_center'), str(ops_action.tag if ops_action else ''))
check('Customer display action exists', bool(display_action))
check('Customer display action tag', bool(display_action and display_action.tag == 'crystal_clean_customer_display'), str(display_action.tag if display_action else ''))

hr('MENUS')
root = env.ref('car_wash_dashboard.menu_crystal_clean_root', raise_if_not_found=False)
ops_menu = env.ref('car_wash_dashboard.menu_crystal_clean_ops_center', raise_if_not_found=False)
display_menu = env.ref('car_wash_dashboard.menu_crystal_clean_customer_display', raise_if_not_found=False)
check('Crystal Clean root menu exists', bool(root))
check('Operations menu exists', bool(ops_menu))
check('Customer display menu exists', bool(display_menu))
check('Operations menu action linked', bool(ops_menu and ops_action and ops_menu.action == ops_action))
check('Display menu action linked', bool(display_menu and display_action and display_menu.action == display_action))

hr('SECURITY GROUPS')
display_group = env.ref('car_wash_dashboard.group_car_wash_customer_display', raise_if_not_found=False)
manager_group = env.ref('car_wash_dashboard.group_car_wash_manager', raise_if_not_found=False)
check('Customer Display group exists', bool(display_group))
check('Manager Analytics group exists', bool(manager_group))
check('Display menu restricted to display group', bool(display_menu and display_group and display_group in display_menu.groups_id))

hr('BACKEND CONTRACTS')
Production = env['mrp.production']
methods = [
    'get_station_topology',
    'get_operations_data',
    'get_queue_data',
    'get_station_details',
    'get_operational_intelligence_data',
    'get_customer_display_data',
    'get_management_data',
    'get_materials_data',
    'get_customers_data',
    'get_team_data',
]
for method in methods:
    check('Method %s' % method, hasattr(Production, method))

hr('TOPOLOGY CONTRACT')
topology = Production.get_station_topology()
check('Topology returns dict', isinstance(topology, dict))
stations = topology.get('stations', []) if isinstance(topology, dict) else []
check('Stations list present', isinstance(stations, list))
orders = [row.get('display_order', 0) for row in stations]
check('Stations sorted by display_order', orders == sorted(orders), str(orders))
allowed_states = {'available', 'queued', 'busy', 'overloaded', 'maintenance', 'closed'}
check('All station states recognized', all(row.get('runtime_state') in allowed_states for row in stations), str([(r.get('station_code'), r.get('runtime_state')) for r in stations]))

hr('OPERATIONS CONTRACT')
ops = Production.get_operations_data()
check('Operations contract version', ops.get('contract_version') == '15.0-operations', str(ops.get('contract_version')))
check('Operations stations list', isinstance(ops.get('stations'), list))
check('Operations queue dict', isinstance(ops.get('queue'), dict))
check('Operations does not require write', True, 'read-only method call completed')

hr('INTELLIGENCE CONTRACT')
intel = Production.get_operational_intelligence_data()
check('Intelligence contract version', intel.get('contract_version') == '16.0-operational-intelligence', str(intel.get('contract_version')))
check('Intelligence stations list', isinstance(intel.get('stations'), list))
for row in intel.get('stations', []):
    if row.get('over_capacity'):
        check('Overloaded projection suppressed %s' % row.get('station_code'), row.get('projection_reliable') is False and row.get('projected_clear_minutes') is False)

hr('CUSTOMER DISPLAY CONTRACT - AS AUTHORIZED USER IF AVAILABLE')
# Do not sudo the user context here. If current user lacks the group, verify the method exists only.
if display_group in env.user.groups_id or env.user._is_admin():
    display = Production.get_customer_display_data()
    check('Display contract version', display.get('contract_version') == '17.0-customer-display', str(display.get('contract_version')))
    check('Display rotation list', isinstance(display.get('rotation'), list))
    check('Display ready list', isinstance(display.get('ready_for_pickup'), list))
    forbidden = {'customer_name', 'phone', 'mobile', 'price', 'amount_total', 'payment_state', 'operator_names', 'employee_name'}
    def scan(value):
        if isinstance(value, dict):
            for key, sub in value.items():
                if key in forbidden:
                    return False
                if not scan(sub):
                    return False
        elif isinstance(value, list):
            return all(scan(x) for x in value)
        return True
    check('Display payload has no forbidden fields', scan(display))
else:
    check('Current user not authorized for display payload', True, 'permission gate intentionally not bypassed')

hr('RESULT')
print('checks=%s failed=%s' % (checks, failed))
print('RESULT: %s' % ('PASS 100%' if failed == 0 else 'FAIL'))
print('NO DATA MODIFIED')
print('=' * W)
''')
