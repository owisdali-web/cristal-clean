/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
export class StepTracker extends Component {
    static template = "car_wash_dashboard.StepTracker";
    static props = ["currentStage?", "state?"];
    static defaultProps = { currentStage: "", state: "in_service" };
    get steps() {
        if (this.props.state === "waiting") return [{ key:"receive",label:_t("تم الاستلام"),mode:"done"},{key:"wait",label:_t("بانتظار المحطة"),mode:"current"},{key:"finish",label:_t("الخدمة"),mode:"upcoming"}];
        if (this.props.state === "ready_for_pickup") return [{key:"receive",label:_t("تم الاستلام"),mode:"done"},{key:"service",label:_t("اكتملت الخدمة"),mode:"done"},{key:"finish",label:_t("جاهزة للاستلام"),mode:"current"}];
        return [{key:"receive",label:_t("تم الاستلام"),mode:"done"},{key:"current",label:this.props.currentStage||_t("قيد الخدمة"),mode:"current"},{key:"finish",label:_t("التسليم"),mode:"upcoming"}];
    }
}
