/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency, formatNumber } from "../../core/cc_format";
export class ManagementStrip extends Component {
    static template = "car_wash_dashboard.ManagementStrip";
    static props = ["management", "team?"];
    get items() {
        const m = this.props.management || {}, f = m.financial || {}, c = m.commercial || {}, t = this.props.team?.kpis || {};
        const symbol = m.currency_symbol || "د.ل";
        return [
            { key: "collected", label: _t("المحصّل اليوم"), value: formatCurrency(f.collected_today || 0, symbol), note: "" },
            { key: "expenses", label: _t("المصروفات"), value: formatCurrency(f.posted_expenses_today || 0, symbol), note: "" },
            { key: "balance", label: _t("الرصيد التشغيلي"), value: formatCurrency(f.operational_balance_today || 0, symbol), note: _t("مؤشر تشغيلي وليس ربحاً محاسبياً") },
            { key: "team", label: _t("الفريق"), value: `${formatNumber(t.currently_checked_in || 0)}/${formatNumber(t.operational_users || 0)}`, note: _t("متواجدون الآن") },
            { key: "customers", label: _t("زبائن اليوم"), value: formatNumber(c.customers_served_today || 0), note: "" },
        ];
    }
    get title() { return _t("مؤشرات الإدارة"); }
    get eyebrow() { return _t("الإدارة"); }
}
