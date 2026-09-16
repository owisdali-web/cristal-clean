/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Droplets } from "../effects/Droplets";
import { Sparkle } from "../effects/Sparkle";
import { vehicleBodyType, vehicleColorHex } from "../../core/cc_format";

export class CarSvg extends Component {
    static template = "car_wash_dashboard.CarSvg";
    static components = { Droplets, Sparkle };
    static props = ["bodyType?", "color?", "state?", "size?", "model?"];
    static defaultProps = { bodyType: "", color: "", state: "waiting", size: "md", model: "" };
    get bodyType() { return this.props.bodyType || vehicleBodyType(this.props.model || ""); }
    get fill() { return vehicleColorHex(this.props.color); }
    get bodyPath() {
        const paths = {
            sedan: "M35 77 L55 53 Q63 43 82 40 L158 40 Q177 42 190 58 L207 77 Q222 79 228 91 L224 103 L28 103 L24 91 Q27 80 35 77Z",
            suv: "M31 77 L45 45 Q50 34 67 31 L163 31 Q181 33 192 50 L207 77 Q223 79 230 92 L225 103 L27 103 L22 91 Q25 81 31 77Z",
            pickup: "M29 77 L45 49 Q52 36 68 34 L126 34 Q143 37 154 53 L163 75 L218 75 Q229 79 232 91 L226 103 L26 103 L22 91 Q24 82 29 77Z",
            hatchback: "M33 77 L48 49 Q55 38 72 35 L147 35 Q163 38 178 55 L204 77 Q220 80 226 91 L222 103 L29 103 L24 92 Q25 82 33 77Z",
        };
        return paths[this.bodyType] || paths.sedan;
    }
    get moving() { return this.props.state === "in_service"; }
    get ready() { return this.props.state === "ready_for_pickup"; }
    get waiting() { return this.props.state === "waiting"; }
    get svgClass() { return `cc_car cc_car--${this.bodyType} cc_car--${this.props.state} cc_car--${this.props.size}`; }
}
