/** @odoo-module **/
import { Component } from "@odoo/owl";
export class Brush extends Component {
    static template = "car_wash_dashboard.Brush";
    static props = ["x?", "y?", "scale?"];
    static defaultProps = { x: 0, y: 0, scale: 1 };
    get transform() { return `translate(${this.props.x} ${this.props.y}) scale(${this.props.scale})`; }
}
