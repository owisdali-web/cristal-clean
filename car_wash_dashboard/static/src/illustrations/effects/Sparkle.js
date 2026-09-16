/** @odoo-module **/
import { Component } from "@odoo/owl";
export class Sparkle extends Component {
    static template = "car_wash_dashboard.Sparkle";
    static props = ["count?"];
    static defaultProps = { count: 5 };
    get items() { return Array.from({ length: Math.min(8, Math.max(0, Number(this.props.count || 0))) }, (_, i) => ({ i, x: 28 + i * 31, y: 22 + (i % 3) * 24 })); }
}
