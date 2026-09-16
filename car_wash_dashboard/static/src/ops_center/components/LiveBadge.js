/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
export class LiveBadge extends Component {
    static template = "car_wash_dashboard.LiveBadge";
    static props = ["online", "loading?"];
    static defaultProps = { loading: false };
    get label() { return this.props.loading ? _t("جارٍ التحديث") : this.props.online ? _t("مباشر") : _t("إعادة الاتصال"); }
}
