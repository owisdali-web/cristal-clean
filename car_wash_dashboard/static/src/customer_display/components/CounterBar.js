/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatNumber } from "../../core/cc_format";
export class CounterBar extends Component {
    static template = "car_wash_dashboard.CounterBar";
    static props = ["counts"];
    get items() { const c=this.props.counts||{}; return [
        { key:"service", label:_t("قيد الخدمة"), value:formatNumber(c.in_service||0), icon:"≋" },
        { key:"waiting", label:_t("في الانتظار"), value:formatNumber(c.waiting||0), icon:"⌛" },
        { key:"ready", label:_t("جاهزة للاستلام"), value:formatNumber(c.ready_for_pickup||0), icon:"✓" },
    ]; }
}
