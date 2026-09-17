# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.car_wash_dashboard.dashboard_logic import (
    build_station_slots,
    group_progress_rows,
    infer_station_type,
    normalize_vehicle_size,
)


@tagged('post_install', '-at_install')
class TestCarWashDashboard(TransactionCase):
    def test_station_fields_are_available(self):
        Workcenter = self.env['mrp.workcenter']
        for field_name in ('car_wash_enabled', 'car_wash_station_type', 'car_wash_sequence'):
            self.assertIn(field_name, Workcenter._fields)
        self.assertIn('car_wash_vehicle_size', self.env['sale.order']._fields)
        self.assertIn('car_wash_vehicle_size', self.env['mrp.production']._fields)

    def test_payload_has_ten_visual_slots(self):
        Workcenter = self.env['mrp.workcenter']
        auto = Workcenter.create({
            'name': 'Automatic Wash Test Station',
            'company_id': self.env.company.id,
            'car_wash_enabled': True,
            'car_wash_station_type': 'automatic',
            'car_wash_sequence': 1,
        })
        polish = Workcenter.create({
            'name': 'Polishing Test Station',
            'company_id': self.env.company.id,
            'car_wash_enabled': True,
            'car_wash_station_type': 'polishing',
            'car_wash_sequence': 2,
        })

        payload = self.env['mrp.production'].get_dashboard_data()

        self.assertEqual(payload['dashboard_version'], '6.3-vehicle-visuals')
        self.assertEqual(len(payload['stations']), 10)
        real_ids = [station['id'] for station in payload['stations'] if station['id']]
        self.assertIn(auto.id, real_ids)
        self.assertIn(polish.id, real_ids)
        self.assertEqual(payload['station_configuration']['automatic_count'], 1)
        self.assertEqual(payload['station_configuration']['polishing_count'], 1)

    def test_pure_station_helpers(self):
        self.assertEqual(normalize_vehicle_size('car'), '')
        self.assertEqual(normalize_vehicle_size('truck'), '')
        self.assertEqual(normalize_vehicle_size('small'), 'small')
        self.assertEqual(normalize_vehicle_size('large'), 'large')
        self.assertEqual(infer_station_type('محطة الغسيل الآلي', ''), 'automatic')
        self.assertEqual(infer_station_type('Polishing Bay', ''), 'polishing')

        grouped = group_progress_rows([
            {'station_id': 1, 'production_id': 10},
            {'station_id': 1, 'production_id': 20},
        ])
        self.assertEqual(grouped[1]['conflict_count'], 2)

        slots = build_station_slots([{'id': 1, 'name': 'A1'}], target=3)
        self.assertEqual(len(slots), 3)
        self.assertTrue(slots[1]['is_placeholder'])
