# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

from odoo.addons.car_wash_dashboard.hooks import bootstrap_station_topology


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    bootstrap_station_topology(env)
