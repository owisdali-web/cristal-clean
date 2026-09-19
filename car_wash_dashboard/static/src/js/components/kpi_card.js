/** @odoo-module **/

import { Component } from "@odoo/owl";

export class KpiCard extends Component {}

KpiCard.template = "car_wash_dashboard.KpiCard";
KpiCard.props = {
    label: String,
    value: { type: [String, Number] },
    note: { type: String, optional: true },
    icon: { type: String, optional: true },
    tone: { type: String, optional: true },
    active: { type: Boolean, optional: true },
    onClick: Function,
};
