/** @odoo-module **/
import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useCcData } from "../../core/cc_hooks";
import { Plate } from "../../core/Plate";
import { formatMinutes, stationStateLabel } from "../../core/cc_format";
export class StationDrawer extends Component {
    static template = "car_wash_dashboard.StationDrawer";
    static components = { Plate };
    static props = ["stationId?", "open", "onClose"];
    setup() {
        this.data = useCcData();
        this.state = useState({ loading: false, details: null, error: "" });
        onWillUpdateProps((next) => { if (next.open && next.stationId && next.stationId !== this.props.stationId) this.load(next.stationId); });
        if (this.props.open && this.props.stationId) this.load(this.props.stationId);
    }
    async load(id) {
        this.state.loading = true; this.state.error = "";
        try { this.state.details = await this.data.stationDetails(id); }
        catch (error) { this.state.error = _t("تعذر تحميل تفاصيل المحطة"); }
        finally { this.state.loading = false; }
    }
    get title() { return this.state.details?.station?.station_code || _t("تفاصيل المحطة"); }
    get station() { return this.state.details?.station || {}; }
    get running() { return this.state.details?.running_jobs || []; }
    get queue() { return this.state.details?.queue?.rows || []; }
    get closeLabel() { return _t("إغلاق"); }
    get currentLabel() { return _t("قيد التنفيذ"); }
    get queueLabel() { return _t("في الانتظار"); }
    get doneLabel() { return _t("منتهية اليوم"); }
    stateLabel() { return stationStateLabel(this.station.runtime_state); }
    minutes(v) { return formatMinutes(v); }
    plate(job) { return job.vehicle?.plate || job.vehicle?.public_reference || job.production_name || "—"; }
    service(job) { return job.vehicle?.service_name || ""; }
}
