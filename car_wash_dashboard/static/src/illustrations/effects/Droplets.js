/** @odoo-module **/
import { Component } from "@odoo/owl";
export class Droplets extends Component {
    static template = "car_wash_dashboard.Droplets";
    static props = ["count?", "className?"];
    static defaultProps = { count: 8, className: "" };
    get items() { return Array.from({ length: Math.min(12, Math.max(0, Number(this.props.count || 0))) }, (_, i) => i); }
}
