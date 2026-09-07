/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            data: {
                total_today: 0, in_progress: 0, done_today: 0, waiting: 0, active_total: 0,
                overdue: 0, ready: 0, wo_efficiency: 0, scrap_qty: 0, scrap_count: 0,
                revenue_today: 0, pending_quotations: 0, avg_turnaround: 0, currency_symbol: "",
                phases: [], workcenter_dist: [], workcenter_load: [], wash_dist: [],
                trend: [], pipeline: [], upcoming: [], timeline: [], low_stock: [],
                kpi_domains: {}, mfg_domains: {}, sale_domains: {}, scrap_domain: [],
            },
            loading: true,
            lastUpdate: "",
        });

        this.washMeta = {
            basic: { label: _t("Basic"), icon: "fa-car", cls: "basic" },
            premium: { label: _t("Premium"), icon: "fa-star", cls: "premium" },
            deluxe: { label: _t("Deluxe"), icon: "fa-diamond", cls: "deluxe" },
        };
        this.pipelineIcons = {
            draft: "fa-pencil",
            confirmed: "fa-check",
            progress: "fa-cog",
            to_close: "fa-flag-checkered",
        };

        this.vehicleTypes = [
            {
                code: "car",
                label: _t("إضافة سيارة"),
                subtitle: _t("Add Car"),
                icon: "fa-car",
                cls: "car",
            },
            {
                code: "truck",
                label: _t("إضافة شاحنة"),
                subtitle: _t("Add Truck"),
                icon: "fa-truck",
                cls: "truck",
            },
            {
                code: "van",
                label: _t("إضافة فان"),
                subtitle: _t("Add Van"),
                icon: "fa-bus",
                cls: "van",
            },
            {
                code: "pickup",
                label: _t("إضافة بيك أب"),
                subtitle: _t("Add Pickup"),
                icon: "fa-truck",
                cls: "pickup",
            },
        ];

        this.phaseChart = null;
        this.workcenterChart = null;
        this.trendChart = null;
        this.refreshTimer = null;

        onWillStart(async () => { await this.fetchData(); });
        onMounted(() => {
            this.renderCharts();
            this.refreshTimer = setInterval(() => this.fetchData(), 30000);
        });
        onWillUnmount(() => {
            this._destroyCharts();
            if (this.refreshTimer) clearInterval(this.refreshTimer);
        });
    }

    // ================= Data =================
    async fetchData() {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = result;
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (error) {
            console.error("Dashboard fetch error:", error);
            this.notification.add(_t("Failed to load dashboard data"), { type: "danger" });
        } finally {
            this.state.loading = false;
            setTimeout(() => this.renderCharts(), 50);
        }
    }

    async manualRefresh() {
        await this.fetchData();
        this.notification.add(_t("Dashboard updated"), { type: "success" });
    }

    // ================= Formatting =================
    formatMoney(value) {
        const symbol = this.state.data.currency_symbol || "";
        return `${symbol} ${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    }
    formatDuration(mins) {
        mins = Math.round(mins || 0);
        if (mins <= 0) return "—";
        if (mins < 60) return `${mins}m`;
        const h = Math.floor(mins / 60), m = mins % 60;
        return m ? `${h}h ${m}m` : `${h}h`;
    }
    washMetaFor(code) {
        return this.washMeta[code] || { label: code, icon: "fa-car", cls: "basic" };
    }
    pillIcon(code) {
        return this.pipelineIcons[code] || "fa-circle-o";
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
            total_today: _t("Work Orders Today"), in_progress: _t("In Progress"),
            done_today: _t("Completed Today"), waiting: _t("Waiting"), active_total: _t("Active Orders"),
        };
        this._openWindow({
            name: labels[key] || _t("Manufacturing Orders"),
            res_model: "mrp.production",
            domain: this.state.data.kpi_domains?.[key] || [],
        });
    }

    openMfg(key) {
        const domain = this.state.data.mfg_domains?.[key];
        if (!domain) return;
        const labels = {
            overdue: _t("Overdue Orders"), ready: _t("Ready to Start"),
            state_draft: _t("Draft"), state_confirmed: _t("Confirmed"),
            state_progress: _t("In Progress"), state_to_close: _t("To Close"),
        };
        this._openWindow({
            name: labels[key] || _t("Manufacturing Orders"),
            res_model: "mrp.production",
            domain,
        });
    }

    openScrap() {
        const domain = this.state.data.scrap_domain;
        if (!domain || !domain.length) return;
        this._openWindow({ name: _t("Scrap Today"), res_model: "stock.scrap", domain });
    }

    openSales(key) {
        const labels = { revenue_today: _t("Confirmed Sales Today"), pending_quotations: _t("Pending Quotations") };
        this._openWindow({
            name: labels[key] || _t("Sales Orders"),
            res_model: "sale.order",
            domain: this.state.data.sale_domains?.[key] || [],
        });
    }

    openWashType(code) {
        const base = this.state.data.kpi_domains?.done_today || [];
        this._openWindow({
            name: this.washMetaFor(code).label,
            res_model: "mrp.production",
            domain: [...base, ["wash_type", "=", code]],
        });
    }

    openProduction(orderId) {
        if (!orderId) return;
        this._openWindow({ res_model: "mrp.production", res_id: orderId, views: [[false, "form"]] });
    }

    openWorkcenterOrders(wc) {
        if (!wc?.id) return;
        this._openWindow({
            name: wc.name,
            res_model: "mrp.workorder",
            domain: [
                ["workcenter_id", "=", wc.id],
                ["state", "in", ["pending", "progress"]],
                ["production_id.state", "not in", ["done", "cancel"]],
            ],
        });
    }

    openOperationOrders(phase) {
        if (!phase) return;
        this._openWindow({
            name: phase.name,
            res_model: "mrp.workorder",
            domain: [
                ["state", "in", ["pending", "progress"]],
                ["production_id.state", "not in", ["done", "cancel"]],
                ["operation_id", "=", phase.operation_id || false],
            ],
        });
    }

    openProduct(productId) {
        if (!productId) return;
        this._openWindow({ res_model: "product.product", res_id: productId, views: [[false, "form"]] });
    }

    createSaleOrder() {
        this._openWindow({ name: _t("New Sales Order"), res_model: "sale.order", views: [[false, "form"]] });
    }

    createVehicleOrder(vehicleType) {
        if (!vehicleType) {
            return;
        }

        this._openWindow({
            name: vehicleType.label,
            res_model: "sale.order",
            views: [[false, "form"]],
            context: {
                default_vehicle_type: vehicleType.code,
            },
        });
    }

    // ================= Charts =================
    _destroyCharts() {
        for (const key of ["phaseChart", "workcenterChart", "trendChart"]) {
            if (this[key]) { this[key].destroy(); this[key] = null; }
        }
    }

    renderCharts() {
        const Chart = window.Chart;
        if (!Chart) {
            console.warn("Chart.js not found. Please ensure it is loaded in manifest.");
            return;
        }
        this._destroyCharts();

        const palette = ["#06b6d4", "#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#ec4899"];
        const pointer = (evt, els) => { evt.native.target.style.cursor = els.length ? "pointer" : "default"; };

        const phaseCtx = document.getElementById("phaseChart")?.getContext("2d");
        const phases = this.state.data.phases || [];
        if (phaseCtx) {
            this.phaseChart = new Chart(phaseCtx, {
                type: "bar",
                data: {
                    labels: phases.length ? phases.map((p) => p.name) : [_t("No data")],
                    datasets: [{
                        label: _t("Cars in Phase"),
                        data: phases.length ? phases.map((p) => p.count) : [0],
                        backgroundColor: palette.slice(0, Math.max(phases.length, 1)),
                        borderRadius: 8, borderSkipped: false,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, onHover: pointer,
                    onClick: (evt, els) => { if (els.length) this.openOperationOrders(phases[els[0].index]); },
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: "#f1f5f9" }, ticks: { precision: 0 } },
                        x: { grid: { display: false } },
                    },
                },
            });
        }

        const wcCtx = document.getElementById("workcenterChart")?.getContext("2d");
        const wcDist = this.state.data.workcenter_dist || [];
        if (wcCtx) {
            this.workcenterChart = new Chart(wcCtx, {
                type: "doughnut",
                data: {
                    labels: wcDist.length ? wcDist.map((w) => w.name) : [_t("No data")],
                    datasets: [{
                        data: wcDist.length ? wcDist.map((w) => w.count) : [1],
                        backgroundColor: palette.slice(0, Math.max(wcDist.length, 1)),
                        borderWidth: 0, hoverOffset: 6,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: "68%", onHover: pointer,
                    onClick: (evt, els) => { if (els.length) this.openWorkcenterOrders(wcDist[els[0].index]); },
                    plugins: { legend: { position: "bottom", labels: { padding: 14, usePointStyle: true } } },
                },
            });
        }

        const trendCtx = document.getElementById("trendChart")?.getContext("2d");
        const trend = this.state.data.trend || [];
        if (trendCtx) {
            const grad = trendCtx.createLinearGradient(0, 0, 0, 240);
            grad.addColorStop(0, "rgba(6, 182, 212, 0.35)");
            grad.addColorStop(1, "rgba(6, 182, 212, 0.02)");
            this.trendChart = new Chart(trendCtx, {
                type: "line",
                data: {
                    labels: trend.map((d) => d.label),
                    datasets: [{
                        label: _t("Cars Washed"), data: trend.map((d) => d.count),
                        borderColor: "#0891b2", backgroundColor: grad, borderWidth: 3, fill: true,
                        tension: 0.4, pointBackgroundColor: "#0891b2", pointRadius: 4, pointHoverRadius: 6,
                    }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: "#f1f5f9" }, ticks: { precision: 0 } },
                        x: { grid: { display: false } },
                    },
                },
            });
        }
    }
}

CarWashDashboard.template = xml`
    <div class="o_car_wash_dashboard">
        <div class="cw-bubbles" aria-hidden="true">
            <span/><span/><span/><span/><span/><span/><span/><span/>
        </div>

        <t t-if="state.loading">
            <div class="cw-loading"><i class="fa fa-spinner fa-spin"/><span>Loading dashboard...</span></div>
        </t>
        <t t-else=""><div class="cw-content">

        <!-- ===== QUICK VEHICLE ORDER GRID ===== -->
        <div class="cw-quick-orders">

            <div class="cw-quick-orders-head">
                <div>
                    <div class="cw-quick-orders-title">
                        <i class="fa fa-plus-circle"/>
                        <span>إنشاء طلب جديد</span>
                    </div>

                    <div class="cw-quick-orders-subtitle">
                        اختر نوع المركبة لإضافة طلب بسرعة
                    </div>
                </div>

                <div class="cw-quick-orders-badge">
                    <i class="fa fa-bolt"/>
                    Quick Order
                </div>
            </div>

            <div class="cw-vehicle-grid">

                <t t-foreach="vehicleTypes" t-as="vehicle" t-key="vehicle.code">

                    <div
                        t-att-class="'cw-vehicle-card ' + vehicle.cls + ' cw-clickable'"
                        t-on-click="() => this.createVehicleOrder(vehicle)"
                        t-att-title="vehicle.label"
                    >

                        <div class="cw-vehicle-icon">
                            <i t-att-class="'fa ' + vehicle.icon"/>
                        </div>

                        <div class="cw-vehicle-info">
                            <div class="cw-vehicle-name">
                                <t t-esc="vehicle.label"/>
                            </div>

                            <div class="cw-vehicle-subtitle">
                                <t t-esc="vehicle.subtitle"/>
                            </div>
                        </div>

                        <div class="cw-vehicle-arrow">
                            <i class="fa fa-arrow-left"/>
                        </div>

                    </div>

                </t>

            </div>
        </div>


            <!-- ===== Header ===== -->
            <div class="cw-header">
                <div class="cw-title">
                    <div class="cw-logo"><i class="fa fa-car"/><span class="cw-drop"><i class="fa fa-tint"/></span></div>
                    <div>
                        <h1>غسيل السيارات – لوحة التحكم</h1>
                        <p>Car Wash Operations Dashboard</p>
                    </div>
                </div>
                <div class="cw-actions">
                    <span class="cw-live"><span class="dot"/> Live</span>
                    <span t-if="state.lastUpdate" class="cw-updated"><i class="fa fa-clock-o me-1"/> <t t-esc="state.lastUpdate"/></span>
                    <button class="btn btn-refresh" t-on-click="manualRefresh"><i class="fa fa-refresh me-1"/> Update</button>
                    <button class="btn btn-create" t-on-click="createSaleOrder"><i class="fa fa-plus me-1"/> طلب جديد</button>
                </div>
            </div>

            <!-- ===== KPI Row 1 : Operations ===== -->
            <div class="row g-3 mb-3">
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi blue cw-clickable" title="عرض أوامر اليوم" t-on-click="() => this.openKpi('total_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-clipboard"/></div>
                        <div><p class="cw-kpi-label">أوامر العمل اليوم</p><div class="cw-kpi-value" t-esc="state.data.total_today"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi amber cw-clickable" title="عرض قيد التنفيذ" t-on-click="() => this.openKpi('in_progress')">
                        <div class="cw-kpi-icon"><i class="fa fa-cog fa-spin"/></div>
                        <div><p class="cw-kpi-label">قيد التنفيذ</p><div class="cw-kpi-value" t-esc="state.data.in_progress"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi green cw-clickable" title="عرض المنفذة اليوم" t-on-click="() => this.openKpi('done_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-check-circle"/></div>
                        <div><p class="cw-kpi-label">تم التنفيذ اليوم</p><div class="cw-kpi-value" t-esc="state.data.done_today"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi violet cw-clickable" title="عرض قائمة الانتظار" t-on-click="() => this.openKpi('waiting')">
                        <div class="cw-kpi-icon"><i class="fa fa-hourglass-half"/></div>
                        <div><p class="cw-kpi-label">في الانتظار</p><div class="cw-kpi-value" t-esc="state.data.waiting"/></div>
                    </div>
                </div>
            </div>

            <!-- ===== KPI Row 2 : Manufacturing ===== -->
            <div class="row g-3 mb-3">
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi rose cw-clickable" title="أوامر تجاوزت الموعد النهائي" t-on-click="() => this.openMfg('overdue')">
                        <div class="cw-kpi-icon"><i class="fa fa-exclamation-circle"/></div>
                        <div><p class="cw-kpi-label">متأخرة عن الموعد</p><div class="cw-kpi-value" t-esc="state.data.overdue"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi green cw-clickable" title="جاهزة للبدء (المكونات متوفرة)" t-on-click="() => this.openMfg('ready')">
                        <div class="cw-kpi-icon"><i class="fa fa-play-circle"/></div>
                        <div><p class="cw-kpi-label">جاهزة للتنفيذ</p><div class="cw-kpi-value" t-esc="state.data.ready"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi teal cw-clickable" title="الفعلي مقابل المتوقع لأوامر العمل المنجزة اليوم" t-on-click="() => this.openKpi('done_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-bolt"/></div>
                        <div><p class="cw-kpi-label">كفاءة أوامر العمل</p>
                            <div class="cw-kpi-value" t-esc="state.data.wo_efficiency ? state.data.wo_efficiency + '%' : '—'"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi orange cw-clickable" title="كمية الهالك اليوم" t-on-click="() => this.openScrap()">
                        <div class="cw-kpi-icon"><i class="fa fa-recycle"/></div>
                        <div><p class="cw-kpi-label">هالك اليوم</p>
                            <div class="cw-kpi-value" t-esc="state.data.scrap_qty"/>
                            <div class="cw-kpi-sub"><t t-esc="state.data.scrap_count"/> عملية</div></div>
                    </div>
                </div>
            </div>

            <!-- ===== KPI Row 3 : Business ===== -->
            <div class="row g-3 mb-4">
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi teal cw-clickable" title="مبيعات مؤكدة اليوم" t-on-click="() => this.openSales('revenue_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-money"/></div>
                        <div><p class="cw-kpi-label">مبيعات اليوم</p><div class="cw-kpi-value cw-kpi-money" t-esc="formatMoney(state.data.revenue_today)"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi indigo cw-clickable" title="عروض أسعار بانتظار التأكيد" t-on-click="() => this.openSales('pending_quotations')">
                        <div class="cw-kpi-icon"><i class="fa fa-file-text-o"/></div>
                        <div><p class="cw-kpi-label">عروض معلقة</p><div class="cw-kpi-value" t-esc="state.data.pending_quotations"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi rose cw-clickable" title="متوسط زمن الإنجاز اليوم" t-on-click="() => this.openKpi('done_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-clock-o"/></div>
                        <div><p class="cw-kpi-label">متوسط زمن الغسيل</p><div class="cw-kpi-value" t-esc="formatDuration(state.data.avg_turnaround)"/></div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi slate cw-clickable" title="كل الأوامر النشطة" t-on-click="() => this.openKpi('active_total')">
                        <div class="cw-kpi-icon"><i class="fa fa-car"/></div>
                        <div><p class="cw-kpi-label">إجمالي النشطة</p><div class="cw-kpi-value" t-esc="state.data.active_total"/></div>
                    </div>
                </div>
            </div>

            <!-- ===== MO status pipeline ===== -->
            <div class="cw-card mb-4" t-if="state.data.pipeline and state.data.pipeline.length">
                <div class="cw-card-head">
                    <div class="cw-card-title"><i class="fa fa-random"/> حالة أوامر التصنيع</div>
                    <span class="cw-hint">انقر لعرض القائمة</span>
                </div>
                <div class="cw-pipeline">
                    <t t-foreach="state.data.pipeline" t-as="p" t-key="p_index">
                        <div t-att-class="'cw-pill cw-clickable pill-' + p.code" t-on-click="() => this.openMfg('state_' + p.code)">
                            <i t-att-class="'fa ' + pillIcon(p.code)"/>
                            <span t-esc="p.label"/>
                            <b t-esc="p.count"/>
                        </div>
                    </t>
                </div>
            </div>

            <!-- ===== Wash-type tiers ===== -->
            <div class="cw-card mb-4" t-if="state.data.wash_dist and state.data.wash_dist.length">
                <div class="cw-card-head">
                    <div class="cw-card-title"><i class="fa fa-car"/> أنواع الغسيل اليوم</div>
                    <span class="cw-hint">انقر للتفاصيل</span>
                </div>
                <div class="cw-wash-grid">
                    <t t-foreach="state.data.wash_dist" t-as="w" t-key="w_index">
                        <div t-att-class="'cw-wash-tile ' + washMetaFor(w.code).cls + ' cw-clickable'"
                             t-att-title="'عرض ' + washMetaFor(w.code).label" t-on-click="() => this.openWashType(w.code)">
                            <div class="cw-wash-ico"><i t-att-class="'fa ' + washMetaFor(w.code).icon"/></div>
                            <div class="cw-wash-body">
                                <div class="cw-wash-count" t-esc="w.count"/>
                                <div class="cw-wash-label" t-esc="washMetaFor(w.code).label"/>
                            </div>
                            <i class="fa fa-arrow-left cw-wash-go"/>
                        </div>
                    </t>
                </div>
            </div>

            <!-- ===== Work Center Load ===== -->
            <div class="cw-card mb-4" t-if="state.data.workcenter_load and state.data.workcenter_load.length">
                <div class="cw-card-head">
                    <div class="cw-card-title"><i class="fa fa-tachometer"/> مراكز العمل</div>
                    <div class="cw-card-actions"><span class="cw-live"><span class="dot"/> Live</span></div>
                </div>
                <div class="cw-wc-grid">
                    <t t-foreach="state.data.workcenter_load" t-as="wc" t-key="wc_index">
                        <div class="cw-wc-card cw-clickable" title="عرض أوامر عمل هذا المركز"
                             t-on-click="() => this.openWorkcenterOrders(wc)"
                             t-att-data-wc-color="wc.utilization >= 90 ? '#ef4444' : (wc.utilization >= 70 ? '#f59e0b' : '#10b981')"
                             t-att-data-wc-icon="wc.icon or 'fa-wrench'">
                            <div class="cw-wc-header">
                                <div class="cw-wc-icon">
                                    <i t-if="wc.icon" t-att-class="'fa ' + wc.icon"/>
                                    <i t-else="" class="fa fa-wrench"/>
                                </div>
                                <h4 class="cw-wc-title" t-esc="wc.name or 'Unknown Workcenter'"/>
                                <span t-att-class="'cw-wc-status ' + (wc.utilization >= 90 ? 'critical' : (wc.utilization >= 70 ? 'warning' : 'normal'))">
                                    <t t-if="wc.utilization >= 90">CRITICAL</t>
                                    <t t-elif="wc.utilization >= 70">WARNING</t>
                                    <t t-else="">NORMAL</t>
                                </span>
                            </div>
                            <div class="cw-wc-body">
                                <div class="cw-wc-stats">
                                    <div class="cw-stat"><span class="cw-stat-value" t-esc="wc.load or 0"/><span class="cw-stat-label">Current</span></div>
                                    <div class="cw-stat"><span class="cw-stat-value" t-esc="wc.capacity or 0"/><span class="cw-stat-label">Capacity</span></div>
                                    <div class="cw-stat"><span class="cw-stat-value" t-esc="(wc.utilization or 0) + '%'"/><span class="cw-stat-label">Utilization</span></div>
                                </div>
                                <div class="cw-wc-progress">
                                    <div class="cw-progress-label">
                                        <span>Utilization</span>
                                        <span t-att-class="'cw-utilization ' + (wc.utilization >= 90 ? 'critical' : (wc.utilization >= 70 ? 'warning' : 'normal'))"
                                              t-esc="(wc.utilization or 0) + '%'"/>
                                    </div>
                                    <div class="cw-progress-track">
                                        <div class="cw-progress-fill"
                                             t-att-class="(wc.utilization >= 90 ? 'critical' : (wc.utilization >= 70 ? 'warning' : 'normal'))"
                                             t-att-style="'width: ' + Math.min((wc.utilization or 0), 100) + '%;'"/>
                                    </div>
                                </div>
                                <div class="cw-wc-details">
                                    <span class="cw-detail"><i class="fa fa-check-circle"/>
                                        <span t-esc="((wc.capacity or 0) - (wc.load or 0)) + ' spots free'"/></span>
                                    <span class="cw-detail">
                                        <i t-att-class="'fa fa-' + (wc.utilization >= 90 ? 'exclamation-triangle' : (wc.utilization >= 70 ? 'clock-o' : 'check'))"/>
                                        <t t-esc="wc.utilization >= 90 ? 'Overloaded' : (wc.utilization >= 70 ? 'Busy' : 'Available')"/>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </t>
                </div>
            </div>

            <!-- ===== Trend (full width) ===== -->
            <div class="cw-card mb-4">
                <div class="cw-card-head">
                    <div class="cw-card-title"><i class="fa fa-line-chart"/> حركة الأسبوع</div>
                    <span class="cw-hint">آخر 7 أيام</span>
                </div>
                <div class="cw-chart-body cw-chart-trend"><canvas id="trendChart"/></div>
            </div>

            <!-- ===== Phase & Workcenter charts ===== -->
            <div class="row g-3 mb-4">
                <div class="col-lg-6">
                    <div class="cw-card h-100">
                        <div class="cw-card-head"><div class="cw-card-title"><i class="fa fa-bar-chart"/> مراحل العمل</div><span class="cw-hint">انقر للتفاصيل</span></div>
                        <div class="cw-chart-body"><canvas id="phaseChart"/></div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="cw-card h-100">
                        <div class="cw-card-head"><div class="cw-card-title"><i class="fa fa-pie-chart"/> أستخدام مراكز العمل</div><span class="cw-hint">انقر للتفاصيل</span></div>
                        <div class="cw-chart-body"><canvas id="workcenterChart"/></div>
                    </div>
                </div>
            </div>

            <!-- ===== Upcoming schedule ===== -->
            <div class="cw-card mb-4">
                <div class="cw-card-head">
                    <div class="cw-card-title"><i class="fa fa-calendar"/> قادم للتنفيذ</div>
                    <span class="cw-hint">مجدولة ولم تبدأ</span>
                </div>
                <ul class="cw-timeline cw-upcoming">
                    <t t-if="state.data.upcoming and state.data.upcoming.length">
                        <li t-foreach="state.data.upcoming" t-as="u" t-key="u_index"
                            class="cw-clickable" title="فتح أمر التصنيع" t-on-click="() => this.openProduction(u.id)">
                            <span class="cw-time"><t t-esc="u.scheduled_at"/><small t-esc="u.scheduled_date"/></span>
                            <div>
                                <div class="cw-order-name"><t t-esc="u.name"/></div>
                                <div class="cw-order-plate"><i class="fa fa-car me-1"/><t t-esc="u.license_plate"/></div>
                            </div>
                            <span t-if="u.ready" class="cw-ready-chip"><i class="fa fa-check me-1"/>جاهزة</span>
                            <span t-att-class="'cw-wash-badge ' + (u.wash_type or 'basic')">
                                <i t-att-class="'fa ' + washMetaFor(u.wash_type).icon + ' me-1'"/>
                                <t t-esc="washMetaFor(u.wash_type).label"/>
                            </span>
                        </li>
                    </t>
                    <t t-else="">
                        <li class="cw-empty">لا يوجد أوامر مجدولة قادمة</li>
                    </t>
                </ul>
            </div>

            <!-- ===== Timeline & Stock ===== -->
            <div class="row g-3">
                <div class="col-lg-7">
                    <div class="cw-card h-100">
                        <div class="cw-card-head"><div class="cw-card-title"><i class="fa fa-history"/> تم التنفيذ اليوم</div></div>
                        <ul class="cw-timeline">
                            <t t-if="state.data.timeline and state.data.timeline.length">
                                <li t-foreach="state.data.timeline" t-as="order" t-key="order_index"
                                    class="cw-clickable" title="فتح أمر التصنيع" t-on-click="() => this.openProduction(order.id)">
                                    <span class="cw-time"><t t-esc="order.completed_at"/></span>
                                    <div>
                                        <div class="cw-order-name"><t t-esc="order.name"/></div>
                                        <div class="cw-order-plate"><i class="fa fa-car me-1"/><t t-esc="order.license_plate"/></div>
                                    </div>
                                    <span t-att-class="'cw-wash-badge ' + (order.wash_type or 'basic')">
                                        <i t-att-class="'fa ' + washMetaFor(order.wash_type).icon + ' me-1'"/>
                                        <t t-esc="washMetaFor(order.wash_type).label"/>
                                    </span>
                                </li>
                            </t>
                            <t t-else=""><li class="cw-empty">لم يتم التنفيذ اليوم</li></t>
                        </ul>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="cw-card h-100">
                        <div class="cw-card-head"><div class="cw-card-title"><i class="fa fa-exclamation-triangle"/> تنبيه أنخفاض المخزون</div></div>
                        <ul class="cw-stock">
                            <t t-if="state.data.low_stock and state.data.low_stock.length">
                                <li t-foreach="state.data.low_stock" t-as="item" t-key="item_index"
                                    class="cw-clickable" title="فتح المنتج" t-on-click="() => this.openProduct(item.product_id)">
                                    <div class="cw-stock-icon"><i class="fa fa-cube"/></div>
                                    <div>
                                        <div class="cw-stock-name"><t t-esc="item.product_name"/></div>
                                        <div class="cw-stock-meta">Min Qty: <t t-esc="item.min_qty"/></div>
                                    </div>
                                    <span class="cw-stock-chip"><t t-esc="item.available"/> Available</span>
                                </li>
                            </t>
                            <t t-else=""><li class="cw-ok"><i class="fa fa-check-circle"/> All stock levels are OK</li></t>
                        </ul>
                    </div>
                </div>
            </div>

        </div>
        </t>
    </div>
`;

CarWashDashboard.props = {};
registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
