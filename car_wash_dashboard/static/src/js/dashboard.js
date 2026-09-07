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
                total_today: 0,
                in_progress: 0,
                done_today: 0,
                waiting: 0,
                phases: [],
                workcenter_dist: [],
                workcenter_load: [],
                timeline: [],
                low_stock: [],
                kpi_domains: {},
            },
            loading: true,
            lastUpdate: "",
        });

        this.phaseChart = null;
        this.workcenterChart = null;
        this.refreshTimer = null;

        onWillStart(async () => {
            await this.fetchData();
        });

        onMounted(() => {
            this.renderCharts();
            this.refreshTimer = setInterval(() => this.fetchData(), 30000);
        });

        onWillUnmount(() => {
            if (this.phaseChart) this.phaseChart.destroy();
            if (this.workcenterChart) this.workcenterChart.destroy();
            if (this.refreshTimer) clearInterval(this.refreshTimer);
        });
    }

    // ==================================================================
    // Data
    // ==================================================================
    async fetchData() {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = result;
            this.state.lastUpdate = new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
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

    // ==================================================================
    // Navigation (drill-down to the real records)
    // ==================================================================
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
            total_today: _t("Work Orders Today"),
            in_progress: _t("In Progress"),
            done_today: _t("Completed Today"),
            waiting: _t("Waiting"),
        };
        this._openWindow({
            name: labels[key] || _t("Manufacturing Orders"),
            res_model: "mrp.production",
            domain: this.state.data.kpi_domains?.[key] || [],
        });
    }

    openProduction(orderId) {
        if (!orderId) return;
        this._openWindow({
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
            domain: [
                ["workcenter_id", "=", wc.id],
                ["state", "in", ["pending", "progress"]],
                ["production_id.state", "not in", ["done", "cancel"]],
            ],
        });
    }

    openOperationOrders(phase) {
        if (!phase) return;
        const domain = [
            ["state", "in", ["pending", "progress"]],
            ["production_id.state", "not in", ["done", "cancel"]],
            ["operation_id", "=", phase.operation_id || false],
        ];
        this._openWindow({
            name: phase.name,
            res_model: "mrp.workorder",
            domain,
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

    createSaleOrder() {
        // The flow starts from a sale order that later triggers manufacturing.
        this._openWindow({
            name: _t("New Sales Order"),
            res_model: "sale.order",
            views: [[false, "form"]],
        });
    }

    // ==================================================================
    // Charts
    // ==================================================================
    renderCharts() {
        const Chart = window.Chart;
        if (!Chart) {
            console.warn("Chart.js not found. Please ensure it is loaded in manifest.");
            return;
        }

        const phaseCtx = document.getElementById("phaseChart")?.getContext("2d");
        const wcCtx = document.getElementById("workcenterChart")?.getContext("2d");

        if (this.phaseChart) { this.phaseChart.destroy(); this.phaseChart = null; }
        if (this.workcenterChart) { this.workcenterChart.destroy(); this.workcenterChart = null; }

        const phases = this.state.data.phases || [];
        const phaseLabels = phases.map((p) => p.name);
        const phaseValues = phases.map((p) => p.count);

        const wcDist = this.state.data.workcenter_dist || [];
        const wcLabels = wcDist.map((w) => w.name);
        const wcValues = wcDist.map((w) => w.count);

        const palette = ["#06b6d4", "#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#ec4899"];
        const pointer = (evt, els) => {
            evt.native.target.style.cursor = els.length ? "pointer" : "default";
        };

        if (phaseCtx) {
            this.phaseChart = new Chart(phaseCtx, {
                type: "bar",
                data: {
                    labels: phaseLabels.length ? phaseLabels : [_t("No data")],
                    datasets: [{
                        label: _t("Cars in Phase"),
                        data: phaseLabels.length ? phaseValues : [0],
                        backgroundColor: palette.slice(0, Math.max(phaseLabels.length, 1)),
                        borderRadius: 8,
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
                        y: { beginAtZero: true, grid: { color: "#f1f5f9" }, ticks: { precision: 0 } },
                        x: { grid: { display: false } },
                    },
                },
            });
        }

        if (wcCtx) {
            this.workcenterChart = new Chart(wcCtx, {
                type: "doughnut",
                data: {
                    labels: wcLabels.length ? wcLabels : [_t("No data")],
                    datasets: [{
                        data: wcLabels.length ? wcValues : [1],
                        backgroundColor: palette.slice(0, Math.max(wcLabels.length, 1)),
                        borderWidth: 0,
                        hoverOffset: 6,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "68%",
                    onHover: pointer,
                    onClick: (evt, els) => {
                        if (els.length) this.openWorkcenterOrders(wcDist[els[0].index]);
                    },
                    plugins: { legend: { position: "bottom", labels: { padding: 14, usePointStyle: true } } },
                },
            });
        }
    }
}

CarWashDashboard.template = xml`
    <div class="o_car_wash_dashboard">
        <t t-if="state.loading">
            <div class="cw-loading">
                <i class="fa fa-spinner fa-spin"/>
                <span>Loading dashboard...</span>
            </div>
        </t>
        <t t-else="">

            <!-- ===== Header ===== -->
            <div class="cw-header">
                <div class="cw-title">
                    <div class="cw-logo"><i class="fa fa-car"/></div>
                    <div>
                        <h1>غسيل السيارات – لوحة التحكم</h1>
                        <p>Car Wash Operations Dashboard</p>
                    </div>
                </div>
                <div class="cw-actions">
                    <span class="cw-live"><span class="dot"/> Live</span>
                    <span t-if="state.lastUpdate" class="cw-updated">
                        <i class="fa fa-clock-o me-1"/> <t t-esc="state.lastUpdate"/>
                    </span>
                    <button class="btn btn-refresh" t-on-click="manualRefresh">
                        <i class="fa fa-refresh me-1"/> Update
                    </button>
                    <button class="btn btn-create" t-on-click="createSaleOrder">
                        <i class="fa fa-plus me-1"/> طلب جديد
                    </button>
                </div>
            </div>

            <!-- ===== KPI Row ===== -->
            <div class="row g-3 mb-4">
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi blue cw-clickable" title="عرض أوامر اليوم"
                         t-on-click="() => this.openKpi('total_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-file-text-o"/></div>
                        <div>
                            <p class="cw-kpi-label">أوامر العمل اليوم</p>
                            <div class="cw-kpi-value" t-esc="state.data.total_today"/>
                        </div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi amber cw-clickable" title="عرض قيد التنفيذ"
                         t-on-click="() => this.openKpi('in_progress')">
                        <div class="cw-kpi-icon"><i class="fa fa-cog fa-spin"/></div>
                        <div>
                            <p class="cw-kpi-label">In Progress</p>
                            <div class="cw-kpi-value" t-esc="state.data.in_progress"/>
                        </div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi green cw-clickable" title="عرض المنفذة اليوم"
                         t-on-click="() => this.openKpi('done_today')">
                        <div class="cw-kpi-icon"><i class="fa fa-check-circle"/></div>
                        <div>
                            <p class="cw-kpi-label">تم التنفيذ اليوم</p>
                            <div class="cw-kpi-value" t-esc="state.data.done_today"/>
                        </div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi violet cw-clickable" title="عرض قائمة الانتظار"
                         t-on-click="() => this.openKpi('waiting')">
                        <div class="cw-kpi-icon"><i class="fa fa-clock-o"/></div>
                        <div>
                            <p class="cw-kpi-label">Waiting</p>
                            <div class="cw-kpi-value" t-esc="state.data.waiting"/>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ===== Work Center Load - Premium Grid ===== -->
            <div class="cw-card mb-4" t-if="state.data.workcenter_load and state.data.workcenter_load.length">
                <div class="cw-card-head">
                    <div class="cw-card-title">
                        <i class="fa fa-tachometer"/> مراكز العمل
                    </div>
                    <div class="cw-card-actions">
                        <span class="cw-live"><span class="dot"/> Live</span>
                    </div>
                </div>
                <div class="cw-wc-grid">
                    <t t-foreach="state.data.workcenter_load" t-as="wc" t-key="wc_index">
                        <div class="cw-wc-card cw-clickable"
                             title="عرض أوامر عمل هذا المركز"
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
                                    <div class="cw-stat">
                                        <span class="cw-stat-value" t-esc="wc.load or 0"/>
                                        <span class="cw-stat-label">Current</span>
                                    </div>
                                    <div class="cw-stat">
                                        <span class="cw-stat-value" t-esc="wc.capacity or 0"/>
                                        <span class="cw-stat-label">Capacity</span>
                                    </div>
                                    <div class="cw-stat">
                                        <span class="cw-stat-value" t-esc="(wc.utilization or 0) + '%'"/>
                                        <span class="cw-stat-label">Utilization</span>
                                    </div>
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
                                    <span class="cw-detail">
                                        <i class="fa fa-check-circle"/>
                                        <span t-esc="((wc.capacity or 0) - (wc.load or 0)) + ' spots free'"/>
                                    </span>
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

            <!-- ===== Charts ===== -->
            <div class="row g-3 mb-4">
                <div class="col-lg-6">
                    <div class="cw-card h-100">
                        <div class="cw-card-head">
                            <div class="cw-card-title"><i class="fa fa-bar-chart"/>مراحل العمل</div>
                            <span class="cw-hint">انقر للتفاصيل</span>
                        </div>
                        <div class="cw-chart-body">
                            <canvas id="phaseChart"/>
                        </div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="cw-card h-100">
                        <div class="cw-card-head">
                            <div class="cw-card-title"><i class="fa fa-pie-chart"/> أستخدام مراكز العمل</div>
                            <span class="cw-hint">انقر للتفاصيل</span>
                        </div>
                        <div class="cw-chart-body">
                            <canvas id="workcenterChart"/>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ===== Timeline & Stock ===== -->
            <div class="row g-3">
                <div class="col-lg-7">
                    <div class="cw-card h-100">
                        <div class="cw-card-head">
                            <div class="cw-card-title"><i class="fa fa-history"/> تم التنفيذ اليوم</div>
                        </div>
                        <ul class="cw-timeline">
                            <t t-if="state.data.timeline and state.data.timeline.length">
                                <li t-foreach="state.data.timeline" t-as="order" t-key="order_index"
                                    class="cw-clickable" title="فتح أمر التصنيع"
                                    t-on-click="() => this.openProduction(order.id)">
                                    <span class="cw-time"><t t-esc="order.completed_at"/></span>
                                    <div>
                                        <div class="cw-order-name"><t t-esc="order.name"/></div>
                                        <div class="cw-order-plate"><t t-esc="order.license_plate"/></div>
                                    </div>
                                    <span t-att-class="'cw-wash-badge ' + (order.wash_type or 'basic')"
                                          t-esc="order.wash_type"/>
                                </li>
                            </t>
                            <t t-else="">
                                <li class="cw-empty">لم يتم التنفيذ اليوم</li>
                            </t>
                        </ul>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="cw-card h-100">
                        <div class="cw-card-head">
                            <div class="cw-card-title"><i class="fa fa-exclamation-triangle"/> تنبيه أنخفاض المخزون</div>
                        </div>
                        <ul class="cw-stock">
                            <t t-if="state.data.low_stock and state.data.low_stock.length">
                                <li t-foreach="state.data.low_stock" t-as="item" t-key="item_index"
                                    class="cw-clickable" title="فتح المنتج"
                                    t-on-click="() => this.openProduct(item.product_id)">
                                    <div class="cw-stock-icon"><i class="fa fa-box"/></div>
                                    <div>
                                        <div class="cw-stock-name"><t t-esc="item.product_name"/></div>
                                        <div class="cw-stock-meta">Min Qty: <t t-esc="item.min_qty"/></div>
                                    </div>
                                    <span class="cw-stock-chip"><t t-esc="item.available"/> Available</span>
                                </li>
                            </t>
                            <t t-else="">
                                <li class="cw-ok"><i class="fa fa-check-circle"/> All stock levels are OK</li>
                            </t>
                        </ul>
                    </div>
                </div>
            </div>

        </t>
    </div>
`;

CarWashDashboard.props = {};
registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
