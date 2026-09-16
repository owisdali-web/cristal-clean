/** @odoo-module **/
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const REFRESH_TYPE = "crystal_clean_dashboard_refresh";

export class CarWashDashboardV9 extends Component {
    static template = "car_wash_dashboard.DashboardV9";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.bus = useService("bus_service");
        this.state = useState({
            loading: true, page: "dashboard", query: "", lastUpdate: "", realtime: false,
            livePulse: false, liveMessage: "", animationTick: 0, customerFocusIndex: 0, selectedCarId: false, selectedStationId: false, vehicleFilter: "all", reportPeriod: "week", theme: "dark", themeInitialized: false,
            data: this.emptyData(),
        });
        this.refreshTimer = null; this.animationTimer = null; this.customerTimer = null;
        this.busRefreshTimer = null; this.liveTimer = null; this.busChannel = null; this.busSubscribed = false;
        this.onBusNotification = (payload) => this.handleBusNotification(payload);
        onWillStart(async () => { await this.fetchData(); await this.setupRealtime(); });
        onMounted(() => {
            document.body.classList.add("cc12-dashboard-mode");
            this.refreshTimer = setInterval(() => this.fetchData({ silent: true }), 15000);
            this.animationTimer = setInterval(() => { this.state.animationTick += 1; }, 2600);
            this.customerTimer = setInterval(() => this.advanceCustomerFocus(), 6000);
        });
        onWillUnmount(() => {
            document.body.classList.remove("cc12-dashboard-mode");
            for (const timer of [this.refreshTimer, this.animationTimer, this.customerTimer, this.busRefreshTimer, this.liveTimer]) if (timer) clearTimeout(timer);
            if (this.busSubscribed) this.bus.unsubscribe(REFRESH_TYPE, this.onBusNotification);
            if (this.busChannel) this.bus.deleteChannel(this.busChannel);
        });
    }

    emptyData() {
        return {
            dashboard_version: "13.0-preview-station-control", company_id: false, company_name: "كريستال كلين", currency_symbol: "", current_user_name: "", current_user_initial: "U", current_user_role: "", current_user_theme: "dark",
            active_total: 0, in_progress: 0, waiting: 0, ready_delivery: 0, done_today: 0, total_today: 0,
            overdue: 0, avg_turnaround: 0, workcenter_load: [], active_cars: [], materials: [], low_stock: [], upcoming: [],
            pos_page: { orders: [], top_services: [], hourly: [], orders_today: 0, revenue_today: 0, avg_ticket: 0, customers_today: 0, month_revenue: 0, month_orders: 0 },
            finance_page: { recent_moves: [], expense_breakdown: [], week_pos_sales: [], customer_invoices_today: 0, vendor_bills_today: 0, receivable_open: 0, payable_open: 0, pos_revenue_today: 0, pos_month_revenue: 0, collected_today: 0, expense_today: 0, net_today: 0, month_expense: 0 },
            customer_screen: { cars: [], ready_count: 0, washing_count: 0, waiting_count: 0, avg_turnaround: 0 },
            customer_page: { rows: [], total: 0, repeat: 0, new_today: 0, inactive_30: 0 },
            client_hr_page: { customer_rows: [], top_customers: [], total_customers: 0, repeat_customers: 0, new_customers_month: 0, inactive_30: 0, user_rows: [], total_users: 0, present_today: 0, attendance_rate: 0, shift_rows: [], shift_count: 0, station_workers: 0 },
            maintenance_page: { available: false, rows: [], equipment_count: 0, due_soon: 0, open_faults: 0, health_avg: 0 },
            reports_page: { avg_service_minutes: 0, workorder_efficiency: 0, station_utilization: 0, data_quality: 0, trend: [], hourly: [], top_services: [] },
            stock_value: 0, bus_channel: "", realtime_enabled: false, kpi_domains: {}, accounting_domains: {}, pos_domains: {},
            shop_floor_action: "mrp_workorder.action_mrp_display",
        };
    }

    async fetchData({ silent = false } = {}) {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = { ...this.emptyData(), ...result };
            if (!this.state.themeInitialized) {
                this.state.theme = result.current_user_theme === "light" ? "light" : "dark";
                this.state.themeInitialized = true;
            }
            this.state.lastUpdate = new Date().toLocaleTimeString("ar", { hour: "2-digit", minute: "2-digit" });
            if (!this.busChannel && result.bus_channel) await this.setupRealtime();
        } catch (error) {
            console.error("Crystal Clean V9 dashboard fetch failed", error);
            if (!silent) this.notification.add(_t("تعذر تحميل بيانات لوحة المغسلة"), { type: "danger" });
        } finally { this.state.loading = false; }
    }

    async setupRealtime() {
        const channel = this.state.data.bus_channel;
        if (!this.state.data.realtime_enabled || !channel || this.busChannel === channel) return;
        try {
            if (!this.busSubscribed) { this.bus.subscribe(REFRESH_TYPE, this.onBusNotification); this.busSubscribed = true; }
            await this.bus.addChannel(channel); this.busChannel = channel; this.state.realtime = true;
        } catch (error) { console.warn("Realtime unavailable; polling fallback active", error); this.state.realtime = false; }
    }

    handleBusNotification(payload) {
        if (payload?.company_id && payload.company_id !== this.state.data.company_id) return;
        const labels = {
            wash_order_created: "دخلت سيارة جديدة إلى المغسلة", wash_order_updated: "تم تحديث أمر غسيل",
            stage_created: "تم تجهيز مرحلة جديدة", stage_changed: "سيارة انتقلت إلى مرحلة جديدة",
            stage_updated: "تحديث مباشر من إحدى المحطات", pos_order_created: "طلب جديد من نقطة البيع",
            pos_order_updated: "تم تحديث طلب نقطة البيع", accounting_updated: "تم تحديث الحسابات",
        };
        this.state.liveMessage = labels[payload?.reason] || "تحديث مباشر من المغسلة";
        this.state.livePulse = true;
        if (this.liveTimer) clearTimeout(this.liveTimer);
        this.liveTimer = setTimeout(() => { this.state.livePulse = false; this.state.liveMessage = ""; }, 2500);
        if (this.busRefreshTimer) clearTimeout(this.busRefreshTimer);
        this.busRefreshTimer = setTimeout(() => this.fetchData({ silent: true }), 220);
    }

    async manualRefresh() { await this.fetchData(); this.notification.add(_t("تم تحديث البيانات"), { type: "success" }); }
    async toggleTheme() {
        const next = this.state.theme === "dark" ? "light" : "dark";
        this.state.theme = next;
        try {
            await this.orm.call("mrp.production", "set_dashboard_theme", [next]);
            this.state.data.current_user_theme = next;
        } catch (error) {
            console.warn("Could not persist dashboard theme", error);
        }
    }
    setPage(page) {
        this.state.page = page;
        this.state.query = "";
        if (page === "customers") this.state.customerFocusIndex = 0;
        if (page === "vehicles" && !this.state.selectedCarId && this.state.data.active_cars?.length) this.state.selectedCarId = this.state.data.active_cars[0].id;
        if (page === "stations" && !this.state.selectedStationId && this.stationSlots.length) this.state.selectedStationId = this.stationSlots[0].id;
    }
    onSearchInput(ev) { this.state.query = ev.target.value || ""; }
    get dateLabel() { return new Intl.DateTimeFormat("ar", { weekday: "long", year: "numeric", month: "long", day: "numeric" }).format(new Date()); }
    get timeLabel() { return new Date().toLocaleTimeString("ar", { hour: "2-digit", minute: "2-digit" }); }
    get userInitial() { return (this.state.data.current_user_initial || this.state.data.current_user_name || 'U').toString().trim().charAt(0) || 'U'; }
    get userSubLabel() { return this.state.data.current_user_role || this.state.data.company_name || 'المستخدم الحالي'; }
    formatMoney(v) { return `${Number(v || 0).toLocaleString("ar", { maximumFractionDigits: 2 })} ${this.state.data.currency_symbol || ""}`; }
    formatCount(v) { return `${Number(v || 0)}`.padStart(2, "0"); }

    get completionRate() { const total = Number(this.state.data.total_today || 0); return total ? Math.round((Number(this.state.data.done_today || 0) / total) * 100) : 0; }
    completionRingStyle() { return `--cc9-progress:${Math.max(0, Math.min(100, this.completionRate))}%`; }
    get filteredCars() {
        const q = this.state.query.trim().toLowerCase(); const cars = this.state.data.active_cars || [];
        if (!q) return cars;
        return cars.filter(car => [car.public_reference, car.plate, car.customer, car.service_name, car.current_stage, car.workcenter_name].some(v => `${v || ""}`.toLowerCase().includes(q)));
    }
    get readyCars() { return (this.state.data.active_cars || []).filter(c => c.status_code === "ready_delivery"); }

    get stationSlots() {
        const raw = [...(this.state.data.workcenter_load || [])];
        const slots = new Array(10).fill(null);
        const leftovers = [];
        let auto = null;
        let polish = null;

        const slotFromName = (name) => {
            const m = `${name || ""}`.toUpperCase().match(/(?:^|\s)A\s*(10|[1-9])(?:\b|[^0-9])/);
            return m ? Number(m[1]) : 0;
        };

        for (const station of raw) {
            const explicit = slotFromName(station.name);
            const kind = this.stationKind(station);
            if (explicit >= 1 && explicit <= 10 && !slots[explicit - 1]) {
                slots[explicit - 1] = station;
                continue;
            }
            if (kind === "auto" && !auto) auto = station;
            else if (kind === "polish" && !polish) polish = station;
            else leftovers.push(station);
        }

        // Crystal Clean real layout: A1-A8 flexible, A9 automatic wash, A10 polish/shine.
        if (!slots[8] && auto) slots[8] = auto;
        if (!slots[9] && polish) slots[9] = polish;
        for (let i = 0; i < 8; i++) {
            if (!slots[i]) slots[i] = leftovers.shift() || null;
        }
        // Preserve any unmatched real workcenters instead of losing them.
        for (let i = 0; i < 10 && leftovers.length; i++) {
            if (!slots[i]) slots[i] = leftovers.shift();
        }

        return slots.map((station, i) => {
            const slot = i + 1;
            const fixedKind = slot === 9 ? "auto" : (slot === 10 ? "polish" : "general");
            return station
                ? { ...station, slot, station_code: `A${slot}`, kind_override: fixedKind }
                : { id: `placeholder-${slot}`, name: `A${slot}`, station_code: `A${slot}`, slot, kind_override: fixedKind, placeholder: true, load: 0, in_progress: 0, queue: 0, cars: [] };
        });
    }
    stationCode(station) { return station?.station_code || `A${station?.slot || 1}`; }
    stationTypeLabel(station) {
        const kind = this.stationKind(station);
        if (kind === "auto") return "غسيل آلي";
        if (kind === "polish") return "لمعة وتلميع";
        return "محطة مرنة";
    }
    stationKind(station) {
        if (station?.kind_override) return station.kind_override;
        const t = `${station?.name || ""}`.toLowerCase();
        if (t.includes("آلي") || t.includes("الي") || t.includes("auto")) return "auto";
        if (t.includes("لمعة") || t.includes("تلميع") || t.includes("polish")) return "polish";
        return "general";
    }
    stationStatus(station) { if (station.placeholder) return "free"; if (station.in_progress) return "busy"; if (station.queue) return "queue"; return "free"; }
    stationStatusLabel(station) { return { busy: "مشغولة", queue: "قيد الخدمة", free: "متاحة" }[this.stationStatus(station)]; }
    stationCardClass(station) { return `cc9-station is-${this.stationKind(station)} is-${this.stationStatus(station)}`; }
    stationCar(station) { return (station?.cars || [])[0] || null; }
    vehicleSizeLabel(car) { return car?.vehicle_size === "large" ? "سيارة كبيرة" : "سيارة صغيرة"; }
    vehicleImage(car) { return car?.vehicle_size === "large" ? "/car_wash_dashboard/static/src/img/car_pickup.svg" : "/car_wash_dashboard/static/src/img/car_sedan.svg"; }
    stationArtwork(station) {
        const base = "/car_wash_dashboard/static/src/img/v9/main_exact/";
        const car = this.stationCar(station);
        const kind = this.stationKind(station);
        if (kind === "auto") return base + "auto_small.webp";
        if (kind === "polish") return base + "polish_large.webp";
        if (!car) {
            const idle = {
                1: "external_small.webp", 2: "interior_large.webp", 3: "multi_small.webp",
                4: "interior_black_large.webp", 5: "powder_small.webp", 7: "external_large.webp",
                8: "interior_small.webp", 9: "deep_large.webp",
            };
            return base + (idle[station?.slot] || "external_small_2.webp");
        }
        const op = this.focusedOperation(station);
        const size = car?.vehicle_size === "large" ? "large" : "small";
        if (op.kind === "polish") return base + "polish_large.webp";
        if (op.kind === "auto") return base + "auto_small.webp";
        if (op.kind === "interior") return base + (size === "large" ? "interior_black_large.webp" : "interior_small.webp");
        if (op.kind === "deep") return base + (size === "large" ? "deep_large.webp" : "multi_small.webp");
        if (op.kind === "powder") return base + "powder_small.webp";
        if (op.kind === "qc") return base + "external_small_2.webp";
        return base + (size === "large" ? "external_large.webp" : "external_small.webp");
    }
    stationIdleLabel(station) {
        const kind = this.stationKind(station);
        if (kind === "auto") return "غسيل آلي";
        if (kind === "polish") return "تلميع ولمعة";
        return "جاهزة لاستقبال السيارات";
    }
    stationPhoto(station) {
        const base = "/car_wash_dashboard/static/src/img/premium_real_v12/";
        const kind = this.stationKind(station);
        if (kind === "auto") return base + "station_auto.webp";
        if (kind === "polish") return base + "station_worker.webp";
        const photos = [
            "station_toyota.webp",
            "station_nissan.webp",
            "station_mercedes.webp",
            "station_worker.webp",
            "overview_day.webp",
            "hero_storefront.webp",
            "overview_night.webp",
            "night_lineup.webp",
        ];
        const slot = Math.max(1, Number(station?.slot || 1));
        return base + photos[(slot - 1) % photos.length];
    }
    progressWidth(value) {
        const pct = Math.max(0, Math.min(100, Number(value || 0)));
        return `--cc11-progress:${pct}%`;
    }
    stationOperations(station) { const car = this.stationCar(station); return (car?.operations || []).filter(op => op.state !== "done").slice(0, 4); }
    operationKind(name) { const t = `${name || ""}`.toLowerCase(); if (t.includes("آلي") || t.includes("الي") || t.includes("auto")) return "auto"; if (t.includes("لمعة") || t.includes("تلميع") || t.includes("باستا")) return "polish"; if (t.includes("داخلي") || t.includes("صالون") || t.includes("صالة") || t.includes("فرشة") || t.includes("سقف")) return "interior"; if (t.includes("عميق")) return "deep"; if (t.includes("فودرة")) return "powder"; if (t.includes("محرك")) return "engine"; if (t.includes("سفلي")) return "underbody"; if (t.includes("فحص")) return "qc"; return "external"; }
    focusedOperation(station) { const ops = this.stationOperations(station); if (!ops.length) return { name: this.stationCar(station)?.current_stage || station?.name || "جاهزة", kind: this.operationKind(this.stationCar(station)?.current_stage || station?.name) }; const op = ops[this.state.animationTick % ops.length]; return { ...op, kind: op.kind || this.operationKind(op.name) }; }
    operationIcon(name) { return { auto: "fa-cogs", polish: "fa-diamond", interior: "fa-shower", deep: "fa-tint", powder: "fa-cloud", engine: "fa-fire", underbody: "fa-arrow-up", qc: "fa-search", external: "fa-tint" }[this.operationKind(name)] || "fa-wrench"; }
    statusClass(car) { return car?.status_code || "waiting"; }
    statusLabel(car) { return car?.status_label || "في الانتظار"; }
    carDurationLabel(car) { const m = Number(car?.elapsed_minutes || 0); return m < 60 ? `${m} دقيقة` : `${Math.floor(m / 60)}س ${m % 60}د`; }
    remainingLabel(car) { const m = Number(car?.remaining_minutes || 0); return m ? `متبقي ${m} دقيقة` : "الوقت يحدّث حسب المراحل"; }
    stationCrewLabel(station) {
        const car = this.stationCar(station);
        return car?.operator_label || (this.stationKind(station) === "auto" ? "فريق الغسيل الآلي" : this.stationKind(station) === "polish" ? "فريق اللمعة" : "فريق المحطة");
    }
    stationElapsedLabel(station) { const car = this.stationCar(station); return car ? this.carDurationLabel(car) : "--:--"; }
    stationQueueLabel(station) { const q = Number(station?.queue || 0); return q ? `${q} انتظار` : "0 انتظار"; }
    stationDoneLabel(station) { return `${Number(station?.done_today || 0)} منجزة`; }
    stationEfficiencyLabel(station) { const v = Number(station?.efficiency || 0); return v ? `${Math.round(v)}% كفاءة` : "كفاءة قيد القياس"; }
    initialOf(name) { const value = `${name || "U"}`.trim(); return value ? value[0] : "U"; }
    staffProgressStyle(row) { const pct = row?.status === "present" ? 100 : (row?.status === "done" ? 70 : 25); return `--cc10-progress:${pct}%`; }
    selectStation(station) { this.state.selectedStationId = station?.id || station?.station_code || false; }
    closeStation() { this.state.selectedStationId = false; }
    get selectedStation() {
        if (!this.state.selectedStationId) return null;
        return this.stationSlots.find(s => s.id === this.state.selectedStationId || s.station_code === this.state.selectedStationId) || null;
    }
    get selectedStationCar() { return this.stationCar(this.selectedStation); }
    stationTone(station) {
        const kind = this.stationKind(station);
        const status = this.stationStatus(station);
        if (kind === "polish") return "polish";
        if (kind === "auto") return "auto";
        if (status === "busy") return "active";
        if (status === "queue") return "warning";
        return "free";
    }
    get dashboardAlerts() {
        const alerts = [];
        if (Number(this.state.data.overdue || 0)) alerts.push({ tone: "danger", icon: "fa-clock-o", text: `${this.state.data.overdue} سيارة تجاوزت الوقت المتوقع` });
        for (const item of (this.state.data.low_stock || []).slice(0, 2)) alerts.push({ tone: "warning", icon: "fa-cube", text: `${item.product_name}: مخزون منخفض` });
        const queues = this.stationSlots.filter(s => Number(s.queue || 0) > 0).slice(0, 2);
        for (const s of queues) alerts.push({ tone: "info", icon: "fa-hourglass-half", text: `${this.stationCode(s)} لديها ${s.queue} في الانتظار` });
        if (!alerts.length) alerts.push({ tone: "success", icon: "fa-check", text: "جميع المحطات تعمل بصورة طبيعية" });
        return alerts.slice(0, 4);
    }

    get vehiclePageCars() {
        const cars = this.filteredCars;
        const filter = this.state.vehicleFilter;
        if (filter === "service") return cars.filter(c => ["washing", "ready"].includes(c.status_code));
        if (filter === "waiting") return cars.filter(c => c.status_code === "waiting");
        if (filter === "ready") return cars.filter(c => c.status_code === "ready_delivery");
        return cars;
    }
    setVehicleFilter(filter) { this.state.vehicleFilter = filter; this.state.selectedCarId = false; }
    selectCar(id) { this.state.selectedCarId = id; }
    get selectedCar() {
        const rows = this.vehiclePageCars;
        return rows.find(c => c.id === this.state.selectedCarId) || rows[0] || null;
    }
    progressStyle(value) { return `--cc10-progress:${Math.max(0, Math.min(100, Number(value || 0)))}%`; }
    get appointmentRows() { return this.state.data.upcoming || []; }
    appointmentStatus(car) {
        if (car?.status_code === "ready_delivery") return { code: "done", label: "مكتمل" };
        if (car?.elapsed_minutes > 0 && car?.status_code === "waiting") return { code: "late", label: "متأخر" };
        if (car?.status_code === "waiting") return { code: "waiting", label: "في الانتظار" };
        return { code: "scheduled", label: "مجدول" };
    }
    get appointmentCompleted() { return this.appointmentRows.filter(c => this.appointmentStatus(c).code === "done").length; }
    get appointmentLate() { return this.appointmentRows.filter(c => this.appointmentStatus(c).code === "late").length; }
    get appointmentWaiting() { return this.appointmentRows.filter(c => ["waiting", "late"].includes(this.appointmentStatus(c).code)).length; }
    selectStation(id) { this.state.selectedStationId = id; }
    get selectedStation() { return this.stationSlots.find(s => s.id === this.state.selectedStationId) || this.stationSlots[0] || null; }
    get clientRows() {
        const q = this.state.query.trim().toLowerCase();
        const rows = this.state.data.customer_page?.rows || [];
        if (!q) return rows;
        return rows.filter(r => [r.name, r.phone, r.favorite_service].some(v => `${v || ""}`.toLowerCase().includes(q)));
    }
    get clientHrRows() {
        const q = this.state.query.trim().toLowerCase();
        const rows = this.state.data.client_hr_page?.customer_rows || this.state.data.customer_page?.rows || [];
        if (!q) return rows;
        return rows.filter(r => [r.name, r.phone, r.favorite_service].some(v => `${v || ""}`.toLowerCase().includes(q)));
    }
    get hrUserRows() {
        const q = this.state.query.trim().toLowerCase();
        const rows = this.state.data.client_hr_page?.user_rows || [];
        if (!q) return rows;
        return rows.filter(r => [r.name, r.role, r.department, r.station, r.phone].some(v => `${v || ""}`.toLowerCase().includes(q)));
    }
    get topCustomerRows() { return this.state.data.client_hr_page?.top_customers || []; }
    staffStatusClass(row) { return `is-${row?.status || 'present'}`; }
    shiftBarStyle(item) { return `--cc10-progress:${Math.max(0, Math.min(100, Number(item?.pct || 0)))}%`; }
    openPartner(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "res.partner", res_id: id, views: [[false, "form"]], target: "current" }); }
    openCustomerList() { return this._openWindow({ name: _t("العملاء"), res_model: "res.partner", domain: [["customer_rank", ">", 0]] }); }
    openUsersList() { return this._openWindow({ name: _t('المستخدمون'), res_model: 'res.users', domain: [['share', '=', false]] }); }
    materialDaysLabel(item) { return item?.days_remaining === false || item?.days_remaining === undefined ? "لا يوجد معدل كافٍ" : `يكفي ${item.days_remaining} يوم`; }
    get averageMaterialDays() { const rows = (this.state.data.materials || []).filter(x => x.days_remaining !== false && x.days_remaining !== undefined); return rows.length ? Math.round(rows.reduce((a,x) => a + Number(x.days_remaining || 0), 0) / rows.length) : 0; }
    burnStatusLabel(item) { return { danger: "منخفض", warning: "متابعة", good: "جيد" }[item?.burn_status] || "جيد"; }
    get reportTrendMax() { return Math.max(1, ...(this.state.data.reports_page?.trend || []).map(x => Number(x.count || 0))); }
    reportTrendStyle(item) { return `--cc10-column:${Math.max(4, Math.round((Number(item?.count || 0) / this.reportTrendMax) * 100))}%`; }
    get reportHourlyMax() { return Math.max(1, ...(this.state.data.reports_page?.hourly || []).map(x => Number(x.amount || 0))); }
    heatLevel(item) { const p = Math.round((Number(item?.amount || 0) / this.reportHourlyMax) * 4); return `level-${Math.max(0, Math.min(4, p))}`; }
    get serviceMixMax() { return Math.max(1, ...(this.state.data.reports_page?.top_services || []).map(x => Number(x.qty || 0))); }
    serviceMixStyle(item) { return `--cc10-progress:${Math.round((Number(item?.qty || 0) / this.serviceMixMax) * 100)}%`; }
    maintenanceStatusClass(row) { return `is-${row?.status || "good"}`; }
    get maintenanceRows() { return this.state.data.maintenance_page?.rows || []; }
    openMaintenance() {
        if (!this.state.data.maintenance_page?.available) {
            this.notification.add(_t("تطبيق الصيانة غير متوفر في هذه القاعدة"), { type: "warning" });
            return;
        }
        return this._openWindow({ name: _t("المعدات والصيانة"), res_model: "maintenance.equipment", domain: [] });
    }
    get upsellRows() {
        const rows = this.state.data.pos_page?.top_services || [];
        return rows.slice(0, 4).map((item, index) => ({
            name: item.name,
            label: index === 0 ? "خدمة إضافية مقترحة" : "فرصة بيع إضافي",
            pct: Math.max(8, Math.min(45, Math.round((Number(item.orders || item.qty || 0) / Math.max(1, this.state.data.pos_page.orders_today || 1)) * 100))),
        }));
    }

    get customerCars() { return this.state.data.customer_screen?.cars || []; }
    get customerFocusCar() { const cars = this.customerCars; return cars.length ? cars[this.state.customerFocusIndex % cars.length] : null; }
    advanceCustomerFocus() { if (this.state.page !== "customers") return; if (this.customerCars.length) this.state.customerFocusIndex = (this.state.customerFocusIndex + 1) % this.customerCars.length; }
    customerStageIndex(car) {
        if (car?.status_code === "ready_delivery" || car?.status_code === "done") return 6;
        if (car?.status_code === "waiting" || car?.status_code === "ready") return Math.max(1, Math.min(2, car?.progress ? 2 : 1));
        const kind = car?.current_operation_kind || this.operationKind(car?.current_stage);
        if (kind === "polish") return 4; if (kind === "qc") return 5; return 3;
    }
    customerStatusClass(car) { return `is-${this.statusClass(car)} stage-${this.customerStageIndex(car)}`; }
    customerProgressStyle(car) { return `--cc9-car-progress:${Math.max(0, Math.min(100, Number(car?.progress || 0)))}%`; }
    customerStageDots(car) { return [1,2,3,4,5,6].map(n => ({ n, active: n === this.customerStageIndex(car), done: n < this.customerStageIndex(car) })); }
    async toggleCustomerFullscreen() {
        try {
            if (!document.fullscreenElement) {
                const target = document.querySelector(".cc12-customer-page") || document.documentElement;
                await target.requestFullscreen();
            } else {
                await document.exitFullscreen();
            }
        } catch (e) { console.warn(e); }
    }

    get displayMaterials() { return (this.state.data.materials || []).slice(0, 7); }
    materialPct(item) { const free = Math.max(0, Number(item?.free || 0)); const max = Math.max(free, Number(item?.on_hand || 0), Number(item?.min_qty || 0) * 2, 1); return Math.round((free / max) * 100); }
    materialStyle(item) { return `--cc9-material:${this.materialPct(item)}%`; }
    materialTone(index) { return ["blue","pink","gold","violet","cyan","green","navy"][index % 7]; }
    get weekSalesMax() { return Math.max(1, ...(this.state.data.finance_page?.week_pos_sales || []).map(x => Number(x.amount || 0))); }
    financeBarStyle(item) { return `--cc9-bar:${Math.round((Number(item.amount || 0) / this.weekSalesMax) * 100)}%`; }
    get expenseMax() { return Math.max(1, ...(this.state.data.finance_page?.expense_breakdown || []).map(x => Number(x.amount || 0))); }
    expenseStyle(item) { return `--cc9-bar:${Math.round((Number(item.amount || 0) / this.expenseMax) * 100)}%`; }
    expenseTotal() { return (this.state.data.finance_page?.expense_breakdown || []).reduce((a, x) => a + Number(x.amount || 0), 0); }
    expenseShare(item) { const total = this.expenseTotal() || 1; return Math.round((Number(item?.amount || 0) / total) * 100); }

    get posHourlyMax() { return Math.max(1, ...(this.state.data.pos_page?.hourly || []).map(x => Number(x.amount || 0))); }
    posHourStyle(item) { return `--cc9-column:${Math.round((Number(item.amount || 0) / this.posHourlyMax) * 100)}%`; }
    get topServiceMax() { return Math.max(1, ...(this.state.data.pos_page?.top_services || []).map(x => Number(x.amount || 0))); }
    topServiceStyle(item) { return `--cc9-bar:${Math.round((Number(item.amount || 0) / this.topServiceMax) * 100)}%`; }

    _openWindow(options) { return this.action.doAction({ type: "ir.actions.act_window", target: "current", views: [[false, "list"], [false, "form"]], ...options }); }
    openProduction(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "mrp.production", res_id: id, views: [[false, "form"]], target: "current" }); }
    openKpi(key) { return this._openWindow({ name: _t("أوامر الغسيل"), res_model: "mrp.production", domain: this.state.data.kpi_domains?.[key] || [] }); }
    openVehicles() { return this.setPage('vehicles'); }
    openAppointments() { return this.setPage("appointments"); }
    openCustomers() { return this.setPage("clients"); }
    openWorkcenter(station) { if (station?.placeholder) return this.openShopFloor(); return this._openWindow({ name: station.name, res_model: "mrp.workorder", domain: station.domain || [["workcenter_id", "=", station.id]] }); }
    openProduct(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "product.product", res_id: id, views: [[false, "form"]], target: "current" }); }
    openAccountingMove(id) { return this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move", res_id: id, views: [[false, "form"]], target: "current" }); }
    openPosOrder(row) { if (row?.wash_order_id) return this.openProduction(row.wash_order_id); return this.action.doAction({ type: "ir.actions.act_window", res_model: "pos.order", res_id: row.id, views: [[false, "form"]], target: "current" }); }
    openPosOrders() { return this._openWindow({ name: _t("طلبات نقطة البيع"), res_model: "pos.order", domain: [] }); }
    openMaterials() { return this._openWindow({ name: _t("مواد المغسلة"), res_model: "product.product", domain: [["id", "in", (this.state.data.materials || []).map(x => x.product_id)]] }); }
    openAccounting() { return this._openWindow({ name: _t("الفواتير والحسابات"), res_model: "account.move", domain: [["company_id", "=", this.state.data.company_id]] }); }
    async openShopFloor() { try { await this.action.doAction(this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display"); } catch (e) { this.notification.add(_t("تعذر فتح شاشة الغسيل"), { type: "warning" }); } }
    async openPosApp() { try { await this.action.doAction("point_of_sale.action_client_pos_menu"); } catch (e) { return this.openPosOrders(); } }
    async openSettings() { try { await this.action.doAction("base_setup.action_general_configuration"); } catch (e) { this.notification.add(_t("يمكن فتح الإعدادات من تطبيق الإعدادات"), { type: "info" }); } }
}

registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboardV9);
