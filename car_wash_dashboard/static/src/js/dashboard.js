/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const EMPTY_DATA = {
    company_name: "",
    currency_symbol: "",
    wash_method: false,
    method_counts: { automatic: 0, manual: 0, unclassified: 0 },
    total_today: 0,
    active_total: 0,
    in_progress: 0,
    waiting: 0,
    done_today: 0,
    ready: 0,
    station_busy: 0,
    station_queue: 0,
    station_total: 0,
    active_cars: [],
    workcenter_load: [],
    trend: [],
    materials: [],
    revenue_today: 0,
    avg_ticket: 0,
    avg_turnaround: 0,
    invoiced_today: 0,
    posted_invoices_today: 0,
    receivable_open: 0,
    data_quality: 100,
    kpi_domains: {},
    sale_domains: {},
    accounting_domains: {},
    shop_floor_action: "mrp_workorder.action_mrp_display",
};

class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            activeSection: this.constructor.defaultSection || "overview",
            sceneEffect: "wash",
            replaying: false,
            expandedCarId: false,
            selectedStationId: false,
            stationDemo: "snapshot",
            selectedMaterialId: false,
            lastUpdate: "",
            data: { ...EMPTY_DATA },
            reportData: {
                automatic: null,
                manual: null,
            },
        });

        this.refreshTimer = null;
        this.replayTimer = null;

        onWillStart(async () => {
            await this.fetchData();
        });
        onMounted(() => {
            this.refreshTimer = setInterval(() => this.fetchData({ silent: true }), 30000);
        });
        onWillUnmount(() => {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
            if (this.replayTimer) clearTimeout(this.replayTimer);
        });
    }

    sectionWashMethod(section = this.state.activeSection) {
        if (section === "automatic") return "automatic";
        if (section === "manual") return "manual";
        return false;
    }

    async _fetchDashboard(washMethod = false) {
        return this.orm.call("mrp.production", "get_dashboard_data", [washMethod]);
    }

    async fetchData({ silent = false } = {}) {
        try {
            if (this.state.activeSection === "reports") {
                const [overview, automatic, manual] = await Promise.all([
                    this._fetchDashboard(false),
                    this._fetchDashboard("automatic"),
                    this._fetchDashboard("manual"),
                ]);
                this.state.data = overview;
                this.state.reportData.automatic = automatic;
                this.state.reportData.manual = manual;
            } else {
                const washMethod = this.sectionWashMethod();
                const result = await this.orm.call("mrp.production", "get_dashboard_data", [washMethod]);
                this.state.data = result;
            }
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            const stations = this.state.data.workcenter_load || [];
            if (!stations.some((station) => station.id === this.state.selectedStationId)) {
                this.state.selectedStationId = stations[0]?.id || false;
            }
        } catch (error) {
            console.error("Crystal Clean dashboard fetch failed", error);
            if (!silent) this.notification.add(_t("تعذر تحميل بيانات لوحة المغسلة"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async manualRefresh() {
        await this.fetchData();
        this.notification.add(_t("تم تحديث لوحة المغسلة"), { type: "success" });
    }

    async setSection(section) {
        if (this.state.activeSection === section) return;
        this.state.activeSection = section;
        this.state.loading = true;
        this.state.selectedStationId = false;
        this.state.stationDemo = "snapshot";
        await this.fetchData();
    }

    setScene(effect) {
        this.state.sceneEffect = effect;
        this.replayCar();
    }

    replayCar() {
        this.state.replaying = false;
        requestAnimationFrame(() => {
            this.state.replaying = true;
            if (this.replayTimer) clearTimeout(this.replayTimer);
            this.replayTimer = setTimeout(() => { this.state.replaying = false; }, 950);
        });
    }

    toggleCar(id) {
        this.state.expandedCarId = this.state.expandedCarId === id ? false : id;
    }

    selectStation(id) {
        this.state.selectedStationId = id;
        this.state.stationDemo = "snapshot";
    }

    setStationDemo(mode) {
        this.state.stationDemo = mode;
    }

    selectMaterial(id) {
        this.state.selectedMaterialId = this.state.selectedMaterialId === id ? false : id;
    }

    get sceneInfo() {
        const map = {
            wait: { title: "في الانتظار", desc: "السيارة بانتظار بدء رحلة الغسيل.", progress: 0, pos: 0 },
            wash: { title: "الغسيل قيد التشغيل", desc: "السيارة داخل مرحلة الغسيل الحالية.", progress: 40, pos: 0.4 },
            dry: { title: "التجفيف قيد التنفيذ", desc: "مرحلة التجفيف وتجهيز السيارة للتسليم.", progress: 75, pos: 0.75 },
            ready: { title: "السيارة جاهزة", desc: "اكتملت رحلة العناية وأصبحت السيارة جاهزة للتسليم.", progress: 100, pos: 1 },
            delay: { title: "تأخير تشغيلي", desc: "تنبيه بصري لحالة تستحق المتابعة التشغيلية.", progress: 45, pos: 0.45 },
        };
        return map[this.state.sceneEffect] || map.wash;
    }

    sceneJourneyStyle() {
        return `--cc-position:${this.sceneInfo.pos};`;
    }

    sceneTrackStyle() {
        return `width:${this.sceneInfo.progress}%;`;
    }

    get heroCar() {
        return this.state.data.active_cars?.[0] || false;
    }

    get readyCar() {
        return this.state.data.active_cars?.find((car) => car.status_code === "ready_delivery" || car.status_code === "done") || false;
    }

    get knownPlateCount() {
        return (this.state.data.active_cars || []).filter((car) => car.plate && car.plate !== "بدون لوحة").length;
    }

    get selectedStation() {
        return (this.state.data.workcenter_load || []).find((station) => station.id === this.state.selectedStationId)
            || this.state.data.workcenter_load?.[0] || false;
    }

    get currentModeLabel() {
        return this.state.activeSection === "automatic" ? "الغسيل الآلي" : "الغسيل اليدوي";
    }

    modeData(method) {
        return this.state.reportData?.[method] || EMPTY_DATA;
    }

    washMethodLabel(method) {
        return { automatic: "غسيل آلي", manual: "غسيل يدوي" }[method] || "غير محدد";
    }

    vehicleImage(car) {
        const type = String(car?.vehicle_type || "car");
        const large = ["truck", "van", "pickup"].includes(type);
        return large
            ? "/car_wash_dashboard/static/src/img/car_modern_large.svg"
            : "/car_wash_dashboard/static/src/img/car_modern_small.svg";
    }

    stationCode(index) {
        const prefix = this.state.activeSection === "automatic" ? "A" : (this.state.activeSection === "manual" ? "M" : "S");
        return `${prefix}${String(index + 1).padStart(2, "0")}`;
    }

    stationKind(station) {
        if (this.state.activeSection === "automatic") return "auto";
        if (this.state.activeSection === "manual") return "manual";
        const name = String(station?.name || "");
        if (name.includes("آلي") || name.includes("الي")) return "auto";
        if (name.includes("يدوي")) return "manual";
        if (name.includes("لمعة") || name.includes("تلميع")) return "polish";
        return "unspecified";
    }

    stationSnapshotState(station) {
        if ((station?.in_progress || 0) > 0) return "working";
        if ((station?.queue || 0) > 0) return "queue";
        return "idle";
    }

    stationVisualState(station) {
        if (station?.id === this.state.selectedStationId && this.state.stationDemo !== "snapshot") {
            return this.state.stationDemo;
        }
        return this.stationSnapshotState(station);
    }

    stationStateLabel(station) {
        const state = this.stationVisualState(station);
        return { idle: "متاحة", queue: "انتظار", working: "قيد العمل" }[state] || "متاحة";
    }

    stationBarStyle(station) {
        const total = Math.max(1, Number(this.state.data.station_queue || 0));
        return `width:${Math.min(100, Math.round(((station?.queue || 0) / total) * 100))}%;`;
    }

    progressStyle(value) {
        return `width:${Math.max(0, Math.min(100, Number(value || 0)))}%;`;
    }

    trendBarStyle(data, value) {
        const max = Math.max(1, ...(data?.trend || []).map((item) => Number(item.count || 0)));
        return `height:${Math.max(8, Math.round((Number(value || 0) / max) * 100))}%;`;
    }

    formatMoney(value, data = this.state.data) {
        const number = Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
        return `${number} ${data?.currency_symbol || ""}`.trim();
    }

    formatCount(value) {
        return String(value ?? 0).padStart(2, "0");
    }

    materialPreviewCount() {
        return Math.min(6, (this.state.data.materials || []).length);
    }

    _openWindow(options) {
        this.action.doAction({
            type: "ir.actions.act_window",
            target: "current",
            views: [[false, "list"], [false, "form"]],
            ...options,
        });
    }

    openProduction(id) {
        if (!id) return;
        this._openWindow({ name: _t("أمر الغسيل"), res_model: "mrp.production", res_id: id, views: [[false, "form"]] });
    }

    openKpi(key, data = this.state.data) {
        this._openWindow({ name: _t("أوامر الغسيل"), res_model: "mrp.production", domain: data?.kpi_domains?.[key] || [] });
    }

    openReportKpi(method, key) {
        this.openKpi(key, this.modeData(method));
    }

    openSales(data = this.state.data) {
        const domain = data?.sale_domains?.revenue_today || [];
        this._openWindow({ name: _t("مبيعات الغسيل"), res_model: "sale.order", domain });
    }

    openReportSales(method) {
        this.openSales(this.modeData(method));
    }

    openWorkcenter(station) {
        if (!station) return;
        this._openWindow({ name: station.name, res_model: "mrp.workorder", domain: station.domain || [["workcenter_id", "=", station.id]] });
    }

    openAccounting(key) {
        const domain = this.state.data.accounting_domains?.[key];
        if (!domain) return;
        this._openWindow({ name: _t("المحاسبة"), res_model: "account.move", domain });
    }

    openProduct(id) {
        if (!id) return;
        this._openWindow({ res_model: "product.product", res_id: id, views: [[false, "form"]] });
    }

    async openShopFloor() {
        try {
            await this.action.doAction(this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display");
        } catch (error) {
            console.error(error);
            this.notification.add(_t("تعذر فتح شاشة الغسيل"), { type: "danger" });
        }
    }
}

CarWashDashboard.template = "car_wash_dashboard.CarWashDashboard";
CarWashDashboard.props = ["*"];

class OverviewDashboard extends CarWashDashboard {}
OverviewDashboard.defaultSection = "overview";

class AutomaticDashboard extends CarWashDashboard {}
AutomaticDashboard.defaultSection = "automatic";

class ManualDashboard extends CarWashDashboard {}
ManualDashboard.defaultSection = "manual";

class ReportsDashboard extends CarWashDashboard {}
ReportsDashboard.defaultSection = "reports";

const actions = registry.category("actions");
actions.add("car_wash_dashboard.overview_action", OverviewDashboard);
actions.add("car_wash_dashboard.automatic_action", AutomaticDashboard);
actions.add("car_wash_dashboard.manual_action", ManualDashboard);
actions.add("car_wash_dashboard.reports_action", ReportsDashboard);
// Backward-compatible alias for browser bookmarks or old action references.
actions.add("car_wash_dashboard.client_action", OverviewDashboard);
