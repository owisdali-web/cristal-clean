/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatPlate, isOpaqueReference } from "./cc_format";

export class Plate extends Component {
    static template = "car_wash_dashboard.Plate";
    static props = ["value", "variant?", "tv?"];
    static defaultProps = { variant: "normal", tv: false };

    get text() { return formatPlate(this.props.value); }
    get opaque() { return isOpaqueReference(this.props.value); }
    get classes() {
        const classes = ["cc_plate", `cc_plate--${this.opaque ? "opaque" : this.props.variant}`];
        if (this.props.tv) classes.push("cc_plate--tv");
        return classes.join(" ");
    }
    get libyaLabel() { return _t("ليبيا"); }
}
