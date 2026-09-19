# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    car_wash_enabled = fields.Boolean(
        string='Show on Car Wash Dashboard',
        default=False,
        help='Include this work center as a physical car-wash station on the dashboard.',
    )
    car_wash_station_type = fields.Selection(
        [
            ('automatic', 'Automatic'),
            ('polishing', 'Polishing'),
            ('general', 'General'),
        ],
        string='Car Wash Station Type',
        default='general',
        required=True,
    )
    car_wash_sequence = fields.Integer(
        string='Dashboard Sequence',
        default=10,
        help='Lower numbers appear first on the car-wash dashboard.',
    )

    @api.model
    def get_car_wash_routing_diagnostics(self):
        """Return a non-destructive audit of the current MRP routing.

        V6.1 never deletes BoM operations. The upgrade migration archives
        superseded operations only for the confirmed CC-OPS service BoMs. This
        method remains a read-only audit so staging can verify the resulting
        one-Work-Order / one-station routing contract.
        """
        company = self.env.company
        stations = self.with_context(active_test=False).search([
            ('company_id', '=', company.id),
            ('car_wash_enabled', '=', True),
        ])
        station_by_id = {station.id: station for station in stations}

        Operation = self.env['mrp.routing.workcenter']
        operations = Operation.search([
            ('workcenter_id.company_id', '=', company.id),
        ], order='bom_id, sequence, id')

        automatic_terms = ('automatic', 'auto', 'آلي', 'الي')
        polishing_terms = ('polish', 'polishing', 'تلميع', 'لمعة', 'باستا')
        issues = []
        by_bom = defaultdict(list)

        for operation in operations:
            workcenter = station_by_id.get(operation.workcenter_id.id)
            if not workcenter:
                continue
            text = ' '.join(filter(None, [
                operation.name,
                operation.bom_id.display_name if operation.bom_id else '',
            ])).lower()
            by_bom[operation.bom_id.id if operation.bom_id else 0].append(operation)

            if workcenter.car_wash_station_type == 'automatic' and not any(term in text for term in automatic_terms):
                issues.append({
                    'kind': 'non_automatic_on_automatic_station',
                    'operation_id': operation.id,
                    'operation_name': operation.name,
                    'workcenter_id': workcenter.id,
                    'workcenter_name': workcenter.name,
                    'bom_id': operation.bom_id.id if operation.bom_id else False,
                    'bom_name': operation.bom_id.display_name if operation.bom_id else '',
                })
            if workcenter.car_wash_station_type == 'polishing' and not any(term in text for term in polishing_terms):
                issues.append({
                    'kind': 'non_polishing_on_polishing_station',
                    'operation_id': operation.id,
                    'operation_name': operation.name,
                    'workcenter_id': workcenter.id,
                    'workcenter_name': workcenter.name,
                    'bom_id': operation.bom_id.id if operation.bom_id else False,
                    'bom_name': operation.bom_id.display_name if operation.bom_id else '',
                })
            if any(term in text for term in automatic_terms) and workcenter.car_wash_station_type != 'automatic':
                issues.append({
                    'kind': 'automatic_operation_outside_automatic_station',
                    'operation_id': operation.id,
                    'operation_name': operation.name,
                    'workcenter_id': workcenter.id,
                    'workcenter_name': workcenter.name,
                    'bom_id': operation.bom_id.id if operation.bom_id else False,
                    'bom_name': operation.bom_id.display_name if operation.bom_id else '',
                })
            if any(term in text for term in polishing_terms) and workcenter.car_wash_station_type != 'polishing':
                issues.append({
                    'kind': 'polishing_operation_outside_polishing_station',
                    'operation_id': operation.id,
                    'operation_name': operation.name,
                    'workcenter_id': workcenter.id,
                    'workcenter_name': workcenter.name,
                    'bom_id': operation.bom_id.id if operation.bom_id else False,
                    'bom_name': operation.bom_id.display_name if operation.bom_id else '',
                })

        multi_operation_boms = []
        for bom_id, bom_operations in by_bom.items():
            if bom_id and len(bom_operations) > 1:
                multi_operation_boms.append({
                    'bom_id': bom_id,
                    'bom_name': bom_operations[0].bom_id.display_name,
                    'operation_count': len(bom_operations),
                    'operation_ids': [operation.id for operation in bom_operations],
                    'workcenter_ids': list(dict.fromkeys(
                        operation.workcenter_id.id for operation in bom_operations if operation.workcenter_id
                    )),
                })

        return {
            'company_id': company.id,
            'target_model': 'one Work Order / one station per service',
            'station_count': len(stations),
            'operation_count': len(operations),
            'issue_count': len(issues),
            'issues': issues,
            'multi_operation_boms': multi_operation_boms,
            'read_only': True,
        }
