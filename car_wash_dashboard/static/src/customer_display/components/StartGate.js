/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
export class StartGate extends Component {
    static template = "car_wash_dashboard.StartGate";
    static props = ["company", "onStart", "theme", "onTheme"];
    get t() { return { start: _t("بدء العرض"), subtitle: _t("شاشة صالة الانتظار"), theme: _t("تبديل المظهر") }; }
}
