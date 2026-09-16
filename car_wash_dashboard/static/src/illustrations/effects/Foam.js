/** @odoo-module **/
import { Component } from "@odoo/owl";
export class Foam extends Component {
    static template = "car_wash_dashboard.Foam";
    static props = ["count?"];
    static defaultProps = { count: 10 };
    get items() { return Array.from({ length: Math.min(16, Math.max(0, Number(this.props.count || 0))) }, (_, i) => ({ i, x: 18 + (i * 19) % 180, y: 42 + (i * 13) % 34, r: 4 + (i % 4) })); }
}
