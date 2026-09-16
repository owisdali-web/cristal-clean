/** @odoo-module **/
import { Component, onPatched, onWillPatch, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Plate } from "../../core/Plate";
import { formatMinutes } from "../../core/cc_format";
export class QueuePanel extends Component {
    static template = "car_wash_dashboard.QueuePanel";
    static components = { Plate };
    static props = ["rows"];
    setup() {
        this.root = useRef("root");
        this.before = new Map();
        onWillPatch(() => {
            this.before.clear();
            this.root.el?.querySelectorAll("[data-flip]").forEach((el) => this.before.set(el.dataset.flip, el.getBoundingClientRect()));
        });
        onPatched(() => {
            this.root.el?.querySelectorAll("[data-flip]").forEach((el) => {
                const old = this.before.get(el.dataset.flip);
                if (!old) return;
                const now = el.getBoundingClientRect();
                const dx = old.left - now.left, dy = old.top - now.top;
                if (dx || dy) el.animate([{ transform: `translate(${dx}px,${dy}px)` }, { transform: "translate(0,0)" }], { duration: 320, easing: "cubic-bezier(.2,.8,.2,1)" });
            });
        });
    }
    get title() { return _t("طابور السيارات"); }
    get eyebrow() { return _t("الانتظار"); }
    get empty() { return _t("لا توجد سيارات في الانتظار الآن"); }
    wait(row) { return formatMinutes(row.queue_age_minutes || 0); }
    eta(row) { return row.eta_reliable === false || row.estimated_start_in_minutes === false || row.estimated_start_in_minutes === undefined ? _t("قيد التقدير") : _t("يبدأ خلال %s", formatMinutes(row.estimated_start_in_minutes)); }
    isLong(row) { return Number(row.queue_age_minutes || 0) > 15; }
    plate(row) { return row.vehicle?.plate || row.vehicle?.public_reference || row.production_name || "—"; }
    service(row) { return row.vehicle?.service_name || row.operation_name || _t("خدمة غسيل"); }
}
