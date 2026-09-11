/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            activeTab: "ops",
            sceneEffect: "wash",
            replaying: false,
            expandedCarId: false,
            selectedStationId: false,
            stationDemo: "snapshot",
            selectedMaterialId: false,
            lastUpdate: "",
            data: {
                company_name: "",
                currency_symbol: "",
                active_total: 0,
                in_progress: 0,
                waiting: 0,
                ready: 0,
                station_busy: 0,
                station_queue: 0,
                station_total: 0,
                active_cars: [],
                workcenter_load: [],
                materials: [],
                invoiced_today: 0,
                posted_invoices_today: 0,
                receivable_open: 0,
                data_quality: 100,
                kpi_domains: {},
                accounting_domains: {},
                shop_floor_action: "mrp_workorder.action_mrp_display",
                journey_car: false,
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

    async fetchData({ silent = false } = {}) {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = result;
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            if (!this.state.selectedStationId && result.workcenter_load?.length) {
                this.state.selectedStationId = result.workcenter_load[0].id;
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

    setTab(tab) {
        this.state.activeTab = tab;
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
            wait: { title: "في الانتظار", desc: "السيارة بانتظار بدء مرحلة العناية.", progress: 0, pos: 0 },
            wash: { title: "الغسيل قيد التشغيل", desc: "مؤثر الماء يرتبط بتشغيل مرحلة الغسيل.", progress: 33, pos: 0.33333 },
            inspect: { title: "الفحص قيد التنفيذ", desc: "المسح البصري يمثل مرحلة الفحص النهائي.", progress: 67, pos: 0.66667 },
            ready: { title: "السيارة جاهزة", desc: "اكتملت رحلة العناية وأصبحت السيارة جاهزة للتسليم.", progress: 100, pos: 1 },
            delay: { title: "تأخير تشغيلي", desc: "تنبيه بصري لحالة تستحق المتابعة التشغيلية.", progress: 33, pos: 0.33333 },
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
        return this.state.data.journey_car || this.state.data.active_cars?.[0] || false;
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

    stationCode(index) {
        return `A${index}`;
    }

    stationKind(station) {
        const name = String(station?.name || "");
        if (name.includes("آلي") || name.includes("الي")) return "auto";
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

    formatMoney(value) {
        const number = Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
        return `${number} ${this.state.data.currency_symbol || ""}`.trim();
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

    openKpi(key) {
        this._openWindow({ name: _t("أوامر الغسيل"), res_model: "mrp.production", domain: this.state.data.kpi_domains?.[key] || [] });
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
CarWashDashboard.props = {};
registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
