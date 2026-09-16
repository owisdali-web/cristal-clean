/** @odoo-module **/
import { Component } from "@odoo/owl";
export class Conveyor extends Component {
    static template = "car_wash_dashboard.Conveyor";
    static props = ["y?"];
    static defaultProps = { y: 116 };
}
