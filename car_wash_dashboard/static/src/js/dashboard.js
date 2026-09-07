/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            data: {
                total_today: 0,
                in_progress: 0,
                done_today: 0,
                waiting: 0,
                phase_counts: {},
                workcenter_load: [],
                timeline: [],
                low_stock: [],
            },
            loading: true,
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

    async fetchData() {
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_dashboard_data",
                []
            );
            this.state.data = result;
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

    renderCharts() {
        const Chart = window.Chart;
        if (!Chart) {
            console.warn("Chart.js not found. Please ensure it is loaded in manifest.");
            return;
        }

        const phaseCtx = document.getElementById("phaseChart")?.getContext("2d");
        const wcCtx = document.getElementById("workcenterChart")?.getContext("2d");

        if (this.phaseChart) { 
            this.phaseChart.destroy(); 
            this.phaseChart = null; 
        }
        if (this.workcenterChart) { 
            this.workcenterChart.destroy(); 
            this.workcenterChart = null; 
        }

        const phaseLabels = Object.keys(this.state.data.phase_counts);
        const phaseValues = Object.values(this.state.data.phase_counts);
        const wcLabels = Object.keys(this.state.data.workcenter_counts);
        const wcValues = Object.values(this.state.data.workcenter_counts);

        const palette = ["#06b6d4", "#3b82f6", "#8b5cf6", "#f59e0b", "#10b981", "#ef4444", "#ec4899"];

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
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
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
                    plugins: { legend: { position: "bottom", labels: { padding: 14, usePointStyle: true } } },
                },
            });
        }
    }

    getBarClass(wc) {
        const u = wc.utilization || 0;
        if (u >= 90) return "critical";
        if (u >= 70) return "warning";
        return "normal";
    }

    getBarStyle(wc) {
        const pct = Math.min((wc.utilization || 0), 100);
        return `width: ${pct}%;`;
    }
}

// Fixed: Replaced && with 'and' in t-if attributes
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
                    <button class="btn btn-refresh" t-on-click="manualRefresh">
                        <i class="fa fa-refresh me-1"/> Update
                    </button>
                </div>
            </div>

            <!-- ===== KPI Row ===== -->
            <div class="row g-3 mb-4">
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi blue">
                        <div class="cw-kpi-icon"><i class="fa fa-file-text-o"/></div>
                        <div>
                            <p class="cw-kpi-label">Total Orders Today</p>
                            <div class="cw-kpi-value" t-esc="state.data.total_today"/>
                        </div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi amber">
                        <div class="cw-kpi-icon"><i class="fa fa-cog fa-spin"/></div>
                        <div>
                            <p class="cw-kpi-label">In Progress</p>
                            <div class="cw-kpi-value" t-esc="state.data.in_progress"/>
                        </div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi green">
                        <div class="cw-kpi-icon"><i class="fa fa-check-circle"/></div>
                        <div>
                            <p class="cw-kpi-label">Done Today</p>
                            <div class="cw-kpi-value" t-esc="state.data.done_today"/>
                        </div>
                    </div>
                </div>
                <div class="col-xl-3 col-md-6">
                    <div class="cw-card cw-kpi violet">
                        <div class="cw-kpi-icon"><i class="fa fa-clock-o"/></div>
                        <div>
                            <p class="cw-kpi-label">Waiting</p>
                            <div class="cw-kpi-value" t-esc="state.data.waiting"/>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ===== Work Center Load - Premium Grid ===== -->
            <!-- FIXED: Changed && to 'and' -->
            <div class="cw-card mb-4" t-if="state.data.workcenter_load and state.data.workcenter_load.length">
                <div class="cw-card-head">
                    <div class="cw-card-title">
                        <i class="fa fa-tachometer"/> Manufacturing Centers Load
                    </div>
                    <div class="cw-card-actions">
                        <span class="cw-live"><span class="dot"/> Live</span>
                    </div>
                </div>
                <div class="cw-wc-grid">
                    <t t-foreach="state.data.workcenter_load" t-as="wc" t-key="wc_index">
                        <div class="cw-wc-card" 
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
                            <div class="cw-card-title"><i class="fa fa-bar-chart"/> Phase Breakdown</div>
                        </div>
                        <div class="cw-chart-body">
                            <canvas id="phaseChart"/>
                        </div>
                    </div>
                </div>
                <div class="col-lg-6">
                    <div class="cw-card h-100">
                        <div class="cw-card-head">
                            <div class="cw-card-title"><i class="fa fa-pie-chart"/> Workstation Utilisation</div>
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
                            <div class="cw-card-title"><i class="fa fa-history"/> Completed Orders Today</div>
                        </div>
                        <ul class="cw-timeline">
                            <t t-if="state.data.timeline and state.data.timeline.length">
                                <li t-foreach="state.data.timeline" t-as="order" t-key="order_index">
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
                                <li class="cw-empty">No completed orders today</li>
                            </t>
                        </ul>
                    </div>
                </div>
                <div class="col-lg-5">
                    <div class="cw-card h-100">
                        <div class="cw-card-head">
                            <div class="cw-card-title"><i class="fa fa-exclamation-triangle"/> Low Stock Alerts</div>
                        </div>
                        <ul class="cw-stock">
                            <t t-if="state.data.low_stock and state.data.low_stock.length">
                                <li t-foreach="state.data.low_stock" t-as="item" t-key="item_index">
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