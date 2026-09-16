/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { StationTile } from "./StationTile";
import { formatMinutes } from "../../core/cc_format";
export class StationGrid extends Component {
    static template = "car_wash_dashboard.StationGrid";
    static components = { StationTile };
    static props = ["stations", "projectedClear?", "onSelect"];
    get title() { return _t("المحطات الآن"); }
    get eyebrow() { return _t("تشغيل مباشر"); }
    get clearLabel() { return _t("إخلاء النظام المتوقع: %s", this.props.projectedClear === false ? _t("قيد التقدير") : formatMinutes(this.props.projectedClear || 0)); }
    get empty() { return _t("لا توجد محطات معرفة للمغسلة"); }
    get legend() { return [
        ["available", _t("متاحة")], ["busy", _t("مشغولة")], ["queued", _t("انتظار")],
        ["overloaded", _t("تجاوز السعة")], ["maintenance", _t("صيانة")], ["closed", _t("مغلقة")],
    ]; }
}
