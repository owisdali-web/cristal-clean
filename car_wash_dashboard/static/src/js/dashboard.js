/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";


// ============================================================================
// Visual vehicle component
// ============================================================================
class CarVisual extends Component {
    carStyle() {
        const raw = String(this.props.color || "").trim().toLowerCase();
        const map = {
            "أبيض": "#f8fafc", white: "#f8fafc",
            "أسود": "#111827", black: "#111827",
            "أحمر": "#ef4444", red: "#ef4444",
            "أزرق": "#2563eb", blue: "#2563eb",
            "سماوي": "#06b6d4", cyan: "#06b6d4",
            "أخضر": "#16a34a", green: "#16a34a",
            "فضي": "#94a3b8", silver: "#94a3b8",
            "رمادي": "#64748b", gray: "#64748b", grey: "#64748b",
            "ذهبي": "#d4a017", gold: "#d4a017",
            "بني": "#92400e", brown: "#92400e",
        };
        let color = map[raw] || "#2563eb";
        if (/^#[0-9a-f]{3,8}$/i.test(raw)) {
            color = raw;
        }
        return `--cw-car-paint:${color}`;
    }
}

CarVisual.template = "car_wash_dashboard.CarVisual";


// ============================================================================
// Main dashboard
// ============================================================================
class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            data: {
                dashboard_version: "3.0.1-visual-pro",
                company_name: "",
                station_busy: 0,
                station_free: 0,
                station_queue: 0,
                station_total: 0,
                material_reserved_count: 0,
                data_quality: 100,
                total_today: 0,
                in_progress: 0,
                done_today: 0,
                waiting: 0,
                active_total: 0,
                overdue: 0,
                ready: 0,
                wo_efficiency: 0,
                scrap_qty: 0,
                scrap_count: 0,
                revenue_today: 0,
                wash_sales_orders_today: 0,
                avg_ticket: 0,
                pending_quotations: 0,
                invoiced_today: 0,
                posted_invoices_today: 0,
                receivable_open: 0,
                avg_turnaround: 0,
                currency_symbol: "",
                phases: [],
                workcenter_dist: [],
                workcenter_load: [],
                service_dist: [],
                active_cars: [],
                trend: [],
                pipeline: [],
                upcoming: [],
                timeline: [],
                materials: [],
                low_stock: [],
                kpi_domains: {},
                mfg_domains: {},
                sale_domains: {},
                accounting_domains: {},
                scrap_domain: [],
                shop_floor_action: "mrp_workorder.action_mrp_display",
            },
            loading: true,
            lastUpdate: "",
        });

        this.pipelineIcons = {
            draft: "fa-pencil",
            confirmed: "fa-clock-o",
            progress: "fa-shower",
            to_close: "fa-flag-checkered",
        };

        this.vehicleTypes = [
            { code: "car", label: _t("إضافة سيارة"), subtitle: _t("سيارة"), icon: "fa-car", cls: "car" },
            { code: "pickup", label: _t("إضافة بيك أب"), subtitle: _t("بيك أب"), icon: "fa-truck", cls: "pickup" },
            { code: "van", label: _t("إضافة فان"), subtitle: _t("فان"), icon: "fa-bus", cls: "van" },
            { code: "truck", label: _t("إضافة شاحنة"), subtitle: _t("شاحنة"), icon: "fa-truck", cls: "truck" },
        ];

        this.phaseChart = null;
        this.workcenterChart = null;
        this.trendChart = null;
        this.refreshTimer = null;

        onWillStart(async () => {
            await this.fetchData();
        });
        onMounted(() => {
            this.renderCharts();
            this.refreshTimer = setInterval(() => this.fetchData(), 30000);
        });
        onWillUnmount(() => {
            this._destroyCharts();
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
            }
        });
    }

    // ================= Data =================
    async fetchData() {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = result;
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (error) {
            console.error("Car Wash Dashboard V2 fetch error:", error);
            this.notification.add(_t("تعذر تحميل بيانات لوحة المغسلة"), { type: "danger" });
        } finally {
            this.state.loading = false;
            setTimeout(() => this.renderCharts(), 60);
        }
    }

    async manualRefresh() {
        await this.fetchData();
        this.notification.add(_t("تم تحديث لوحة المغسلة"), { type: "success" });
    }

    // ================= Formatting =================
    formatMoney(value) {
        const symbol = this.state.data.currency_symbol || "";
        const number = Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
        return `${number} ${symbol}`.trim();
    }

    formatDuration(mins) {
        mins = Math.round(mins || 0);
        if (mins <= 0) return "—";
        if (mins < 60) return `${mins} د`;
        const h = Math.floor(mins / 60);
        const m = mins % 60;
        return m ? `${h} س ${m} د` : `${h} س`;
    }

    pillIcon(code) {
        return this.pipelineIcons[code] || "fa-circle-o";
    }

    woStateLabel(code) {
        const labels = {
            pending: "بانتظار المرحلة السابقة",
            waiting: "بانتظار المواد",
            ready: "جاهزة",
            progress: "قيد التنفيذ",
            done: "مكتملة",
        };
        return labels[code] || code || "";
    }

    statusClass(code) {
        const allowed = ["washing", "ready", "waiting", "ready_delivery", "done"];
        return allowed.includes(code) ? code : "waiting";
    }

    materialClass(item) {
        if (item?.is_low) return "critical";
        if ((item?.reserved || 0) > 0) return "reserved";
        return "normal";
    }

    // ================= Navigation =================
    _openWindow(options) {
        this.action.doAction({
            type: "ir.actions.act_window",
            target: "current",
            views: [[false, "list"], [false, "form"]],
            ...options,
        });
    }

    openKpi(key) {
        const labels = {
            total_today: _t("أوامر الغسيل اليوم"),
            in_progress: _t("قيد الغسيل"),
            done_today: _t("مكتملة اليوم"),
            waiting: _t("بانتظار البدء"),
            active_total: _t("أوامر الغسيل النشطة"),
        };
        this._openWindow({
            name: labels[key] || _t("أوامر الغسيل"),
            res_model: "mrp.production",
            domain: this.state.data.kpi_domains?.[key] || [],
        });
    }

    openMfg(key) {
        const domain = this.state.data.mfg_domains?.[key];
        if (!domain) return;
        const labels = {
            overdue: _t("أوامر غسيل متأخرة"),
            ready: _t("جاهزة للبدء"),
            state_draft: _t("مسودة"),
            state_confirmed: _t("بانتظار البدء"),
            state_progress: _t("قيد الغسيل"),
            state_to_close: _t("جاهزة للإغلاق"),
        };
        this._openWindow({
            name: labels[key] || _t("أوامر الغسيل"),
            res_model: "mrp.production",
            domain,
        });
    }

    openSales(key) {
        const labels = {
            revenue_today: _t("مبيعات خدمات الغسيل اليوم"),
            pending_quotations: _t("عروض أسعار الغسيل المعلقة"),
        };
        this._openWindow({
            name: labels[key] || _t("المبيعات"),
            res_model: "sale.order",
            domain: this.state.data.sale_domains?.[key] || [],
        });
    }

    openAccounting(key) {
        const domain = this.state.data.accounting_domains?.[key];
        if (!domain) return;
        const labels = {
            invoiced_today: _t("الفواتير المرحلة اليوم"),
            receivable_open: _t("مستحقات العملاء"),
        };
        this._openWindow({
            name: labels[key] || _t("المحاسبة"),
            res_model: "account.move",
            domain,
        });
    }

    openScrap() {
        const domain = this.state.data.scrap_domain || [];
        if (!domain.length) return;
        this._openWindow({ name: _t("هالك الغسيل اليوم"), res_model: "stock.scrap", domain });
    }

    openService(service) {
        if (!service?.domain) return;
        this._openWindow({
            name: service.name,
            res_model: "mrp.production",
            domain: service.domain,
        });
    }

    openProduction(orderId) {
        if (!orderId) return;
        this._openWindow({
            name: _t("أمر الغسيل"),
            res_model: "mrp.production",
            res_id: orderId,
            views: [[false, "form"]],
        });
    }

    openWorkcenterOrders(wc) {
        if (!wc?.id) return;
        this._openWindow({
            name: wc.name,
            res_model: "mrp.workorder",
            domain: wc.domain || [["workcenter_id", "=", wc.id]],
        });
    }

    openOperationOrders(phase) {
        if (!phase) return;
        this._openWindow({
            name: phase.name,
            res_model: "mrp.workorder",
            domain: phase.domain || [["operation_id", "=", phase.operation_id || false]],
        });
    }

    openProduct(productId) {
        if (!productId) return;
        this._openWindow({
            res_model: "product.product",
            res_id: productId,
            views: [[false, "form"]],
        });
    }

    async openShopFloor() {
        try {
            await this.action.doAction(this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display");
        } catch (error) {
            console.error("Shop Floor navigation failed:", error);
            this.notification.add(_t("تعذر فتح شاشة الغسيل"), { type: "danger" });
        }
    }

    createSaleOrder() {
        this._openWindow({
            name: _t("طلب غسيل جديد"),
            res_model: "sale.order",
            views: [[false, "form"]],
        });
    }

    createVehicleOrder(vehicleType) {
        if (!vehicleType) return;
        this._openWindow({
            name: vehicleType.label,
            res_model: "sale.order",
            views: [[false, "form"]],
            context: { default_vehicle_type: vehicleType.code },
        });
    }

    // ================= Charts =================
    _destroyCharts() {
        for (const key of ["phaseChart", "workcenterChart", "trendChart"]) {
            if (this[key]) {
                this[key].destroy();
                this[key] = null;
            }
        }
    }

    renderCharts() {
        const Chart = window.Chart;
        if (!Chart) {
            console.warn("Chart.js not found for Car Wash Dashboard V2.");
            return;
        }

        this._destroyCharts();
        const palette = ["#0ea5e9", "#06b6d4", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#ec4899", "#64748b"];
        const pointer = (evt, els) => {
            if (evt?.native?.target) evt.native.target.style.cursor = els.length ? "pointer" : "default";
        };

        const phaseCtx = document.getElementById("phaseChart")?.getContext("2d");
        const phases = this.state.data.phases || [];
        if (phaseCtx) {
            this.phaseChart = new Chart(phaseCtx, {
                type: "bar",
                data: {
                    labels: phases.length ? phases.map((p) => p.name) : [_t("لا توجد بيانات")],
                    datasets: [{
                        label: _t("السيارات في المرحلة"),
                        data: phases.length ? phases.map((p) => p.count) : [0],
                        backgroundColor: palette.slice(0, Math.max(phases.length, 1)),
                        borderRadius: 9,
                        borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onHover: pointer,
                    onClick: (evt, els) => {
                        if (els.length) this.openOperationOrders(phases[els[0].index]);
                    },
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eef2f7" } },
                        x: { grid: { display: false } },
                    },
                },
            });
        }

        const wcCtx = document.getElementById("workcenterChart")?.getContext("2d");
        const workcenters = this.state.data.workcenter_dist || [];
        if (wcCtx) {
            this.workcenterChart = new Chart(wcCtx, {
                type: "doughnut",
                data: {
                    labels: workcenters.length ? workcenters.map((w) => w.name) : [_t("لا توجد بيانات")],
                    datasets: [{
                        data: workcenters.length ? workcenters.map((w) => w.count) : [1],
                        backgroundColor: palette,
                        borderWidth: 0,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "67%",
                    onHover: pointer,
                    onClick: (evt, els) => {
                        if (els.length && workcenters.length) {
                            const wc = this.state.data.workcenter_load.find((item) => item.id === workcenters[els[0].index].id);
                            this.openWorkcenterOrders(wc);
                        }
                    },
                    plugins: { legend: { position: "bottom", labels: { usePointStyle: true } } },
                },
            });
        }

        const trendCtx = document.getElementById("trendChart")?.getContext("2d");
        const trend = this.state.data.trend || [];
        if (trendCtx) {
            this.trendChart = new Chart(trendCtx, {
                type: "line",
                data: {
                    labels: trend.map((d) => `${d.label} ${d.date}`),
                    datasets: [{
                        label: _t("السيارات المكتملة"),
                        data: trend.map((d) => d.count),
                        borderColor: "#0ea5e9",
                        backgroundColor: "rgba(14,165,233,.12)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: "#eef2f7" } },
                        x: { grid: { display: false } },
                    },
                },
            });
        }
    }
}

CarWashDashboard.components = { CarVisual };

CarWashDashboard.template = "car_wash_dashboard.CarWashDashboard";

CarWashDashboard.props = {};
registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
