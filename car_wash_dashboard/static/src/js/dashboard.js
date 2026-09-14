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
            search: "",
            lastUpdate: "",
            data: {
                company_name: "",
                currency_symbol: "",
                active_total: 0,
                in_progress: 0,
                waiting: 0,
                ready_delivery: 0,
                ready: 0,
                total_today: 0,
                done_today: 0,
                overdue: 0,
                station_busy: 0,
                station_free: 0,
                station_queue: 0,
                station_total: 0,
                active_cars: [],
                workcenter_load: [],
                materials: [],
                invoiced_today: 0,
                posted_invoices_today: 0,
                receivable_open: 0,
                pos_orders_today: 0,
                pos_revenue_today: 0,
                pos_avg_ticket: 0,
                data_quality: 100,
                kpi_domains: {},
                accounting_domains: {},
                pos_domains: {},
                shop_floor_action: "mrp_workorder.action_mrp_display",
                journey_car: false,
            },
        });

        this.refreshTimer = null;
        onWillStart(async () => this.fetchData());
        onMounted(() => {
            this.refreshTimer = setInterval(() => this.fetchData({ silent: true }), 30000);
        });
        onWillUnmount(() => {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
        });
    }

    async fetchData({ silent = false } = {}) {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = result;
            this.state.lastUpdate = new Date().toLocaleTimeString("ar-LY", { hour: "2-digit", minute: "2-digit" });
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

    onSearchInput(ev) {
        this.state.search = ev.target.value || "";
    }

    get dateLabel() {
        return new Intl.DateTimeFormat("ar-LY", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
        }).format(new Date());
    }

    get timeLabel() {
        return new Intl.DateTimeFormat("ar-LY", { hour: "2-digit", minute: "2-digit" }).format(new Date());
    }

    get heroCar() {
        return this.state.data.journey_car || (this.state.data.active_cars || [])[0] || false;
    }

    get completionRate() {
        const total = Number(this.state.data.total_today || 0);
        const done = Number(this.state.data.done_today || 0);
        if (!total) return 0;
        return Math.max(0, Math.min(100, Math.round((done / total) * 100)));
    }

    completionRingStyle() {
        const pct = this.completionRate;
        return `--cc7-progress:${pct * 3.6}deg;`;
    }

    get filteredCars() {
        const cars = this.state.data.active_cars || [];
        const term = (this.state.search || "").trim().toLowerCase();
        if (!term) return cars.slice(0, 8);
        return cars.filter((car) => {
            const haystack = [car.plate, car.public_reference, car.customer, car.service_name, car.current_stage, car.name]
                .filter(Boolean)
                .join(" ")
                .toLowerCase();
            return haystack.includes(term);
        }).slice(0, 8);
    }

    get readyCars() {
        const cars = this.state.data.active_cars || [];
        const ready = cars.filter((car) => car.status_code === "ready_delivery" || car.status_code === "done");
        return (ready.length ? ready : cars).slice(0, 3);
    }

    get displayMaterials() {
        return (this.state.data.materials || []).slice(0, 5);
    }

    materialPct(item) {
        const onHand = Number(item.on_hand || 0);
        const free = Number(item.free || 0);
        if (!onHand) return 0;
        return Math.max(0, Math.min(100, Math.round((free / onHand) * 100)));
    }

    materialStyle(item) {
        return `width:${this.materialPct(item)}%;`;
    }

    materialTone(index) {
        const tones = ["pink", "teal", "amber", "violet", "blue"];
        return tones[Number(index || 0) % tones.length];
    }

    get stationSlots() {
        const actual = (this.state.data.workcenter_load || []).slice(0, 10).map((station, index) => ({
            ...station,
            slot: index + 1,
            placeholder: false,
        }));
        while (actual.length < 10) {
            const slot = actual.length + 1;
            actual.push({
                id: `placeholder-${slot}`,
                slot,
                name: `محطة ${slot}`,
                load: 0,
                in_progress: 0,
                queue: 0,
                capacity: 1,
                placeholder: true,
            });
        }
        return actual;
    }

    stationKind(station) {
        const name = String(station && station.name || "");
        if (name.includes("آلي") || name.includes("الي")) return "auto";
        if (name.includes("لمعة") || name.includes("تلميع")) return "polish";
        return "normal";
    }

    stationStatus(station) {
        if (station.placeholder) return "setup";
        if (Number(station.in_progress || 0) > 0) return "busy";
        if (Number(station.queue || 0) > 0) return "service";
        return "ready";
    }

    stationStatusLabel(station) {
        return {
            busy: "مشغولة",
            service: "قيد الخدمة",
            ready: "جاهزة",
            setup: "غير مهيأة",
        }[this.stationStatus(station)];
    }

    stationCardClass(station) {
        return `cc7-station cc7-station-${this.stationKind(station)} is-${this.stationStatus(station)}`;
    }

    journeyStepClass(index) {
        const progress = Number(this.heroCar && this.heroCar.progress || 0);
        const thresholds = [0, 15, 35, 60, 80, 100];
        if (progress >= thresholds[index]) return "is-done";
        const next = thresholds[index + 1];
        if (next !== undefined && progress < next && progress >= thresholds[index]) return "is-current";
        return "";
    }

    statusClass(car) {
        const code = car && car.status_code || "waiting";
        if (code === "washing") return "blue";
        if (code === "ready_delivery" || code === "done") return "green";
        if (code === "ready") return "cyan";
        return "amber";
    }

    statusLabel(car) {
        return car && car.status_label || "في الانتظار";
    }

    carDurationLabel(car) {
        if (car && car.elapsed_minutes !== undefined && car.elapsed_minutes !== false) {
            return `${car.elapsed_minutes} دقيقة`;
        }
        return car && car.started_at ? `منذ ${car.started_at}` : "—";
    }

    formatMoney(value) {
        const number = Number(value || 0).toLocaleString("ar-LY", { maximumFractionDigits: 2 });
        return `${number} ${this.state.data.currency_symbol || ""}`.trim();
    }

    _openWindow(options) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            target: "current",
            views: [[false, "list"], [false, "form"]],
            ...options,
        });
    }

    openProduction(id) {
        if (!id) return;
        return this._openWindow({ name: _t("أمر الغسيل"), res_model: "mrp.production", res_id: id, views: [[false, "form"]] });
    }

    openKpi(key) {
        return this._openWindow({ name: _t("أوامر الغسيل"), res_model: "mrp.production", domain: this.state.data.kpi_domains && this.state.data.kpi_domains[key] || [] });
    }

    openWorkcenter(station) {
        if (!station || station.placeholder) return;
        return this._openWindow({ name: station.name, res_model: "mrp.workorder", domain: station.domain || [["workcenter_id", "=", station.id]] });
    }

    openAccounting(key) {
        const domains = this.state.data.accounting_domains || {};
        if (!domains[key]) return;
        return this._openWindow({ name: _t("المحاسبة"), res_model: "account.move", domain: domains[key] });
    }

    openPosOrders() {
        const domains = this.state.data.pos_domains || {};
        return this._openWindow({ name: _t("طلبات نقطة البيع اليوم"), res_model: "pos.order", domain: domains.orders_today || [] });
    }

    openProduct(id) {
        if (!id) return;
        return this._openWindow({ name: _t("المادة"), res_model: "product.product", res_id: id, views: [[false, "form"]] });
    }

    openCustomers() {
        return this._openWindow({ name: _t("العملاء"), res_model: "res.partner", domain: [["customer_rank", ">", 0]] });
    }

    openMaterials() {
        const ids = (this.state.data.materials || []).map((item) => item.product_id).filter(Boolean);
        return this._openWindow({ name: _t("مواد المغسلة"), res_model: "product.product", domain: [["id", "in", ids]] });
    }

    async openShopFloor() {
        try {
            return await this.action.doAction(this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display");
        } catch (error) {
            console.error(error);
            this.notification.add(_t("تعذر فتح شاشة الغسيل"), { type: "danger" });
        }
    }

    openSidebar(section) {
        if (section === "home") {
            const el = document.querySelector(".cc7-dashboard-scroll");
            if (el) el.scrollTo({ top: 0, behavior: "smooth" });
            return;
        }
        if (section === "cars") return this.openKpi("active_total");
        if (section === "appointments") return this.openKpi("waiting");
        if (section === "stations") return this.openShopFloor();
        if (section === "customers") return this.openCustomers();
        if (section === "inventory") return this.openMaterials();
        if (section === "sales") return this.openPosOrders();
        if (section === "reports") return this.openAccounting("invoiced_today");
        if (section === "settings") {
            this.notification.add(_t("إعدادات الداشبورد ستتم إضافتها في مرحلة التهيئة التالية"), { type: "info" });
        }
    }

    quickAction(action) {
        if (action === "start") return this.openShopFloor();
        if (action === "finish") return this.openKpi("in_progress");
        if (action === "receipt") return this.openPosOrders();
        if (action === "deliver") return this.openKpi("ready_delivery");
    }
}

CarWashDashboard.template = "car_wash_dashboard.CarWashDashboard";
CarWashDashboard.props = {};
registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
