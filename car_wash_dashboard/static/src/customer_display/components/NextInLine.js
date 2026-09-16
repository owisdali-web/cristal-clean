/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatMinutes } from "../../core/cc_format";
export class NextInLine extends Component {
    static template = "car_wash_dashboard.NextInLine";
    static props = ["car?"];
    get visible() { return Boolean(this.props.car && this.props.car.display_state === "waiting"); }
    get title() { return _t("دورك في الانتظار"); }
    get position() { return this.props.car?.queue_position ? _t("الترتيب رقم %s", this.props.car.queue_position) : _t("في قائمة الانتظار"); }
    get eta() { return this.props.car?.eta_reliable === false || this.props.car?.eta_minutes === false ? _t("قيد التقدير") : _t("خلال ~%s", formatMinutes(this.props.car?.eta_minutes || 0)); }
}
