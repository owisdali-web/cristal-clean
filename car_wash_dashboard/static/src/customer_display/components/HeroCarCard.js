/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Plate } from "../../core/Plate";
import { WashTunnel } from "../../illustrations/wash_tunnel/WashTunnel";
import { StepTracker } from "./StepTracker";
import { clamp, formatMinutes } from "../../core/cc_format";
export class HeroCarCard extends Component {
    static template = "car_wash_dashboard.HeroCarCard";
    static components = { Plate, WashTunnel, StepTracker };
    static props = ["car", "policy"];
    get progress() { return clamp(this.props.car.progress_percent || 0, 0, 100); }
    get etaLabel() {
        if (!this.props.policy.show_eta) return "";
        if (this.props.car.eta_reliable === false || this.props.car.eta_minutes === false || this.props.car.eta_minutes === undefined) return _t("قيد التقدير");
        return formatMinutes(this.props.car.eta_minutes);
    }
    get etaTitle() { return this.props.car.eta_scope === "service" ? _t("الوقت المتوقع للانتهاء") : _t("الوقت المتوقع للمرحلة"); }
    get progressText() { return `${Math.round(this.progress)}%`; }
    get stationText() { return this.props.car.station_code ? _t("المحطة %s", this.props.car.station_code) : _t("بانتظار المحطة"); }
    get currentStageLabel() { return _t("المرحلة الحالية"); }
}
