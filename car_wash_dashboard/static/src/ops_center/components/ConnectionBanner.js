/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatClock } from "../../core/cc_format";
export class ConnectionBanner extends Component {
    static template = "car_wash_dashboard.ConnectionBanner";
    static props = ["online", "lastUpdated?"];
    get text() {
        const time = this.props.lastUpdated ? formatClock(new Date(this.props.lastUpdated)) : "—";
        return _t("الاتصال منقطع — آخر تحديث %s", time);
    }
}
