/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class WhatsappDashboard extends Component {
    static template = "TAG_whats_18_v2.WhatsappDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            total_sent: 0,
            total_pending: 0,
            total_failed: 0,
            total_received: 0,
            total_contacts: 0,
            series: [],
            top_contacts: [],
        });
        onWillStart(async () => {
            await this.loadStats();
        });
    }

    async loadStats() {
        const data = await this.orm.call("adv.whatsapp.out", "get_dashboard_stats", []);
        Object.assign(this.state, data, { loading: false });
    }

    get maxSeriesValue() {
        let max = 1;
        for (const day of this.state.series) {
            max = Math.max(max, day.sent + day.received);
        }
        return max;
    }

    barHeight(value) {
        return Math.max(2, Math.round((value / this.maxSeriesValue) * 100));
    }

    openMessages() {
        this.action.doAction("TAG_whats_18_v2.adv_whatsapp_out_action");
    }

    openChat() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "whatsapp_chat",
            target: "current",
        });
    }
}

registry.category("actions").add("whatsapp_dashboard", WhatsappDashboard);
