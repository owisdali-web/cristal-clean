/** @odoo-module **/
import { Component, onMounted } from "@odoo/owl";
import { formatNumber } from "../../core/cc_format";
import { useCountUp } from "../../core/cc_hooks";

export class KpiCard extends Component {
    static template = "car_wash_dashboard.KpiCard";
    static props = ["label", "value", "caption?", "tone?", "icon?", "suffix?", "decimals?"];
    static defaultProps = { caption: "", tone: "neutral", icon: "•", suffix: "", decimals: 0 };
    setup() {
        this.counter = useCountUp(Number(this.props.value || 0));
        onMounted(() => this.counter.setTarget(Number(this.props.value || 0)));
    }
    get displayValue() { return `${formatNumber(this.counter.state.value, this.props.decimals)}${this.props.suffix || ""}`; }
}
