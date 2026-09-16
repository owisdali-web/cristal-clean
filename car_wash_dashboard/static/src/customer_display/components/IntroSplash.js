/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
export class IntroSplash extends Component {
    static template = "car_wash_dashboard.IntroSplash";
    static props = ["company"];
    get welcome() { return _t("أهلاً بكم"); }
}
