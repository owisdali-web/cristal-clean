/** @odoo-module **/

import { Component } from "@odoo/owl";
import { CarSvg } from "../car_svg/CarSvg";
import { Brush } from "../effects/Brush";
import { Foam } from "../effects/Foam";
import { Conveyor } from "../effects/Conveyor";
import { clamp } from "../../core/cc_format";

export class WashTunnel extends Component {
    static template = "car_wash_dashboard.WashTunnel";
    static components = { CarSvg, Brush, Foam, Conveyor };
    static props = ["progress?", "car?", "mini?", "state?"];
    static defaultProps = { progress: 45, car: {}, mini: false, state: "in_service" };
    get progress() { return clamp(this.props.progress, 0, 100); }
    get carTransform() {
        const x = 158 - this.progress * 1.15;
        return `translate(${x} 23) scale(.62)`;
    }
    get cls() { return this.props.mini ? "cc_tunnel cc_tunnel--mini" : "cc_tunnel"; }
}
