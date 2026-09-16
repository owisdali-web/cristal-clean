# -*- coding: utf-8 -*-


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID

    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_names = [
        'menu_car_wash_dashboard',
        'menu_car_wash_root',
        'action_car_wash_dashboard',
    ]

    # Unlink the old visible records first, child menu before parent.
    for name in xml_names:
        rec = env.ref('car_wash_dashboard.%s' % name, raise_if_not_found=False)
        if rec and rec.exists():
            rec.unlink()

    # Remove stale XML IDs as well so Astra can recreate fresh actions/menus
    # with any desired identifiers without inheriting old frontend records.
    env['ir.model.data'].sudo().search([
        ('module', '=', 'car_wash_dashboard'),
        ('name', 'in', xml_names),
    ]).unlink()
