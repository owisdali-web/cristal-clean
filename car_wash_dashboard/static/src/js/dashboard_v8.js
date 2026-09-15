/** @odoo-module **/
import { Component, onMounted, onWillStart, onWillUnmount, reactive, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const REFRESH_TYPE = "crystal_clean_dashboard_refresh";

export class CarWashDashboardV8 extends Component {
    static template = "car_wash_dashboard.DashboardV8";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.bus = useService("bus_service");

        this.state = useState({
            loading: true,
            page: "dashboard",
            query: "",
            lastUpdate: "",
            realtime: false,
            livePulse: false,
            liveMessage: "",
            animationTick: 0,
            customerFocusIndex: 0,
            customerFullscreen: false,
            data: this.emptyData(),
        });

        this.refreshTimer = null;
        this.animationTimer = null;
        this.customerTimer = null;
        this.busRefreshTimer = null;
        this.liveTimer = null;
        this.busChannel = null;
        this.busSubscribed = false;
        this.onBusNotification = (payload) => this.handleBusNotification(payload);

        onWillStart(async () => {
            await this.fetchData();
            await this.setupRealtime();
        });
        onMounted(() => {
            this.refreshTimer = setInterval(() => this.fetchData({ silent: true }), 15000);
            this.animationTimer = setInterval(() => { this.state.animationTick += 1; }, 2800);
            this.customerTimer = setInterval(() => this.advanceCustomerFocus(), 6500);
        });
        onWillUnmount(() => {
            for (const timer of [this.refreshTimer, this.animationTimer, this.customerTimer, this.busRefreshTimer, this.liveTimer]) {
                if (timer) clearInterval(timer);
            }
            if (this.busSubscribed) {
                this.bus.unsubscribe(REFRESH_TYPE, this.onBusNotification);
            }
            if (this.busChannel) {
                this.bus.deleteChannel(this.busChannel);
            }
        });
    }

    emptyData() {
        return {
            dashboard_version: "8.0-live-show", company_id: false, company_name: "كريستال كلين",
            currency_symbol: "", active_total: 0, in_progress: 0, waiting: 0, ready_delivery: 0,
            done_today: 0, total_today: 0, overdue: 0, avg_turnaround: 0,
            workcenter_load: [], active_cars: [], materials: [], low_stock: [],
            pos_page: { orders: [], top_services: [], hourly: [], orders_today: 0, revenue_today: 0, avg_ticket: 0, customers_today: 0, month_revenue: 0 },
            finance_page: { recent_moves: [], expense_breakdown: [], week_pos_sales: [], customer_invoices_today: 0, vendor_bills_today: 0, receivable_open: 0, payable_open: 0, pos_revenue_today: 0, pos_month_revenue: 0 },
            customer_screen: { cars: [], ready_count: 0, washing_count: 0, waiting_count: 0, avg_turnaround: 0 },
            stock_value: 0, bus_channel: "", realtime_enabled: false,
            kpi_domains: {}, mfg_domains: {}, accounting_domains: {}, pos_domains: {},
        };
    }

    async fetchData({ silent = false } = {}) {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = { ...this.emptyData(), ...result };
            this.state.lastUpdate = new Date().toLocaleTimeString("ar", { hour: "2-digit", minute: "2-digit" });
            if (!this.busChannel && result.bus_channel) await this.setupRealtime();
        } catch (error) {
            console.error("Crystal Clean V8 dashboard fetch failed", error);
            if (!silent) this.notification.add(_t("تعذر تحميل بيانات لوحة المغسلة"), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async setupRealtime() {
        const channel = this.state.data.bus_channel;
        if (!this.state.data.realtime_enabled || !channel || this.busChannel === channel) return;
        try {
            if (!this.busSubscribed) {
                this.bus.subscribe(REFRESH_TYPE, this.onBusNotification);
                this.busSubscribed = true;
            }
            await this.bus.addChannel(channel);
            this.busChannel = channel;
            this.state.realtime = true;
        } catch (error) {
            console.warn("Crystal Clean realtime unavailable; polling fallback active", error);
            this.state.realtime = false;
        }
    }

    handleBusNotification(payload) {
        if (payload?.company_id && payload.company_id !== this.state.data.company_id) return;
        const labels = {
            wash_order_created: "دخلت سيارة جديدة إلى التشغيل",
            wash_order_updated: "تم تحديث أمر غسيل",
            stage_created: "تم تجهيز مرحلة جديدة",
            stage_changed: "سيارة انتقلت إلى مرحلة جديدة",
            stage_updated: "تحديث مباشر من إحدى المحطات",
            pos_order_created: "طلب جديد من نقطة البيع",
            pos_order_updated: "تم تحديث طلب نقطة البيع",
            accounting_updated: "تم تحديث الحسابات",
        };
        this.state.liveMessage = labels[payload?.reason] || "تحديث مباشر من المغسلة";
        this.state.livePulse = true;
        if (this.liveTimer) clearTimeout(this.liveTimer);
        this.liveTimer = setTimeout(() => { this.state.livePulse = false; this.state.liveMessage = ""; }, 2600);
        if (this.busRefreshTimer) clearTimeout(this.busRefreshTimer);
        this.busRefreshTimer = setTimeout(() => this.fetchData({ silent: true }), 260);
    }

    async manualRefresh() {
        await this.fetchData();
        this.notification.add(_t("تم تحديث لوحة المغسلة"), { type: "success" });
    }

    setPage(page) {
        this.state.page = page;
        this.state.query = "";
        if (page === "customers") this.state.customerFocusIndex = 0;
    }

    onSearchInput(ev) { this.state.query = ev.target.value || ""; }

    get dateLabel() {
        return new Intl.DateTimeFormat("ar", { weekday: "long", year: "numeric", month: "long", day: "numeric" }).format(new Date());
    }
    get timeLabel() { return new Date().toLocaleTimeString("ar", { hour: "2-digit", minute: "2-digit" }); }

    // ---------------- Dashboard / stations ----------------
    get completionRate() {
        const total = Number(this.state.data.total_today || 0);
        return total ? Math.round((Number(this.state.data.done_today || 0) / total) * 100) : 0;
    }
    completionRingStyle() { return `--cc-progress:${Math.max(0, Math.min(100, this.completionRate))}%`; }

    get filteredCars() {
        const q = this.state.query.trim().toLowerCase();
        const cars = this.state.data.active_cars || [];
        if (!q) return cars;
        return cars.filter((car) => [car.public_reference, car.plate, car.customer, car.service_name, car.current_stage, car.workcenter_name].some(v => String(v || "").toLowerCase().includes(q)));
    }

    get readyCars() { return (this.state.data.active_cars || []).filter(c => c.status_code === "ready_delivery"); }

    get stationSlots() {
        const raw = [...(this.state.data.workcenter_load || [])];
        const special = { auto: null, polish: null };
        const general = [];
        for (const station of raw) {
            const kind = this.stationKind(station);
            if (kind === "auto" && !special.auto) special.auto = station;
            else if (kind === "polish" && !special.polish) special.polish = station;
            else general.push(station);
        }
        const ordered = [];
        if (special.auto) ordered.push(special.auto);
        if (special.polish) ordered.push(special.polish);
        ordered.push(...general);
        while (ordered.length < 10) ordered.push({ id: `placeholder-${ordered.length + 1}`, name: `المحطة ${ordered.length + 1}`, placeholder: true, load: 0, in_progress: 0, queue: 0, cars: [] });
        return ordered.slice(0, 10).map((s, index) => ({ ...s, slot: index + 1 }));
    }

    stationKind(station) {
        const text = String(station?.name || "").toLowerCase();
        if (text.includes("آلي") || text.includes("الي") || text.includes("auto")) return "auto";
        if (text.includes("لمعة") || text.includes("تلميع") || text.includes("polish")) return "polish";
        return "general";
    }
    stationStatus(station) {
        if (station.placeholder) return "unconfigured";
        if (station.in_progress) return "busy";
        if (station.queue) return "queue";
        return "free";
    }
    stationStatusLabel(station) {
        return { busy: "مشغولة", queue: "بانتظار الخدمة", free: "متاحة", unconfigured: "غير مهيأة" }[this.stationStatus(station)];
    }
    stationCardClass(station) { return `cc8-station is-${this.stationKind(station)} is-${this.stationStatus(station)}`; }
    stationCar(station) { return (station?.cars || [])[0] || null; }
    vehicleSizeLabel(car) { return car?.vehicle_size === "large" ? "سيارة كبيرة" : "سيارة صغيرة"; }
    vehicleImage(car) { return car?.vehicle_size === "large" ? "/car_wash_dashboard/static/src/img/car_pickup.svg" : "/car_wash_dashboard/static/src/img/car_sedan.svg"; }

    stationOperations(station) {
        const car = this.stationCar(station);
        return (car?.operations || []).filter(op => op.state !== "done").slice(0, 4);
    }
    operationKind(name) {
        const text = String(name || "").toLowerCase();
        if (text.includes("آلي") || text.includes("الي") || text.includes("auto")) return "auto";
        if (text.includes("لمعة") || text.includes("تلميع") || text.includes("باستا")) return "polish";
        if (text.includes("داخلي") || text.includes("صالون") || text.includes("صالة") || text.includes("فرشة") || text.includes("سقف")) return "interior";
        if (text.includes("عميق")) return "deep";
        if (text.includes("فودرة")) return "powder";
        if (text.includes("محرك")) return "engine";
        if (text.includes("سفلي")) return "underbody";
        if (text.includes("فحص")) return "qc";
        return "external";
    }
    focusedOperation(station) {
        const ops = this.stationOperations(station);
        if (!ops.length) return { name: this.stationCar(station)?.current_stage || station?.name || "جاهزة", kind: this.operationKind(this.stationCar(station)?.current_stage || station?.name) };
        const op = ops[this.state.animationTick % ops.length];
        return { ...op, kind: op.kind || this.operationKind(op.name) };
    }
    operationIcon(name) {
        return { auto: "fa-cogs", polish: "fa-diamond", interior: "fa-shower", deep: "fa-tint", powder: "fa-cloud", engine: "fa-fire", underbody: "fa-arrow-up", qc: "fa-search", external: "fa-tint" }[this.operationKind(name)] || "fa-wrench";
    }

    statusClass(car) { return car?.status_code || "waiting"; }
    statusLabel(car) { return car?.status_label || "في الانتظار"; }
    carDurationLabel(car) { const min = Number(car?.elapsed_minutes || 0); return min < 60 ? `${min} دقيقة` : `${Math.floor(min / 60)}س ${min % 60}د`; }
    remainingLabel(car) { const min = Number(car?.remaining_minutes || 0); return min ? `متبقي تقريبي ${min} د` : "الوقت يحدّث حسب المراحل"; }

    // ---------------- Customer screen ----------------
    get customerCars() { return this.state.data.customer_screen?.cars || []; }
    get customerFocusCar() {
        const cars = this.customerCars;
        return cars.length ? cars[this.state.customerFocusIndex % cars.length] : null;
    }
    advanceCustomerFocus() {
        if (this.state.page !== "customers") return;
        const count = this.customerCars.length;
        if (count) this.state.customerFocusIndex = (this.state.customerFocusIndex + 1) % count;
    }
    customerCardClass(car, index) {
        const focus = this.customerFocusCar?.id === car.id;
        return `cc8-customer-car is-${this.statusClass(car)} ${focus ? "is-focus" : ""}`;
    }
    async toggleCustomerFullscreen() {
        try {
            if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
            else await document.exitFullscreen();
            this.state.customerFullscreen = Boolean(document.fullscreenElement);
        } catch (e) { console.warn("Fullscreen unavailable", e); }
    }

    // ---------------- Materials / accounting ----------------
    get displayMaterials() { return (this.state.data.materials || []).slice(0, 12); }
    materialPct(item) {
        const qty = Math.max(0, Number(item?.free || 0));
        const max = Math.max(qty, Number(item?.on_hand || 0), Number(item?.min_qty || 0) * 2, 1);
        return Math.round((qty / max) * 100);
    }
    materialStyle(item) { return `--cc-material:${this.materialPct(item)}%`; }
    get weekSalesMax() { return Math.max(1, ...(this.state.data.finance_page?.week_pos_sales || []).map(x => Number(x.amount || 0))); }
    financeBarStyle(item) { return `--cc-bar:${Math.round((Number(item.amount || 0) / this.weekSalesMax) * 100)}%`; }
    get expenseMax() { return Math.max(1, ...(this.state.data.finance_page?.expense_breakdown || []).map(x => Number(x.amount || 0))); }
    expenseStyle(item) { return `--cc-bar:${Math.round((Number(item.amount || 0) / this.expenseMax) * 100)}%`; }

    // ---------------- POS ----------------
    get posHourlyMax() { return Math.max(1, ...(this.state.data.pos_page?.hourly || []).map(x => Number(x.amount || 0))); }
    posHourStyle(item) { return `--cc-column:${Math.round((Number(item.amount || 0) / this.posHourlyMax) * 100)}%`; }
    get topServiceMax() { return Math.max(1, ...(this.state.data.pos_page?.top_services || []).map(x => Number(x.amount || 0))); }
    topServiceStyle(item) { return `--cc-bar:${Math.round((Number(item.amount || 0) / this.topServiceMax) * 100)}%`; }

    formatMoney(value) { return `${Number(value || 0).toLocaleString("ar", { maximumFractionDigits: 2 })} ${this.state.data.currency_symbol || ""}`; }
    formatCount(value) { return String(Number(value || 0)).padStart(2, "0"); }

    // ---------------- Odoo navigation ----------------
    _openWindow(options) { return this.action.doAction({ type: "ir.actions.act_window", target: "current", views: [[false, "list"], [false, "form"]], ...options }); }
    openProduction(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "mrp.production", res_id: id, views: [[false, "form"]], target: "current" }); }
    openKpi(key) { return this._openWindow({ name: _t("أوامر الغسيل"), res_model: "mrp.production", domain: this.state.data.kpi_domains?.[key] || [] }); }
    openWorkcenter(station) { if (station?.placeholder) return this.openShopFloor(); return this._openWindow({ name: station.name, res_model: "mrp.workorder", domain: station.domain || [["workcenter_id", "=", station.id]] }); }
    openProduct(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "product.product", res_id: id, views: [[false, "form"]], target: "current" }); }
    openAccountingMove(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move", res_id: id, views: [[false, "form"]], target: "current" }); }
    openPosOrder(row) { if (row?.wash_order_id) return this.openProduction(row.wash_order_id); return this.action.doAction({ type: "ir.actions.act_window", res_model: "pos.order", res_id: row.id, views: [[false, "form"]], target: "current" }); }
    openPosOrders() { return this._openWindow({ name: _t("طلبات نقطة البيع"), res_model: "pos.order", domain: [] }); }
    openMaterials() { return this._openWindow({ name: _t("مواد المغسلة"), res_model: "product.product", domain: [["id", "in", (this.state.data.materials || []).map(x => x.product_id)]] }); }
    openAccounting() { return this._openWindow({ name: _t("الفواتير والحسابات"), res_model: "account.move", domain: [["company_id", "=", this.state.data.company_id]] }); }
    async openShopFloor() { try { await this.action.doAction(this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display"); } catch (e) { this.notification.add(_t("تعذر فتح شاشة الغسيل"), { type: "warning" }); } }
    async openPosApp() { try { await this.action.doAction("point_of_sale.action_client_pos_menu"); } catch (e) { return this.openPosOrders(); } }

    quickAction(action) {
        const map = {
            start: ["Shop Floor", () => this.openShopFloor()],
            pos: ["نقطة البيع", () => this.openPosApp()],
            customer: ["شاشة الزبائن", () => this.setPage("customers")],
            materials: ["المواد والحسابات", () => this.setPage("finance")],
        };
        if (map[action]) return map[action][1]();
    }
}

registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboardV8);
