/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { KpiCard } from "./components/kpi_card";
import { QueuePanel } from "./components/queue_panel";
import { StationCard } from "./components/station_card";
import { StationDetail } from "./components/station_detail";

export class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            selectedStationId: false,
            searchQuery: "",
            lastUpdate: "",
            nowLabel: "",
            dateLabel: "",
            data: {
                company_name: "",
                kpis: {
                    active_cars: 0,
                    waiting_queue: 0,
                    available_stations: 0,
                    finished_today: 0,
                },
                queue: [],
                stations: [],
                queue_domain: [],
                station_configuration: { warnings: [] },
                shop_floor_action: "mrp_workorder.action_mrp_display",
            },
        });

        this.refreshTimer = null;
        this.clockTimer = null;

        onWillStart(async () => {
            this.updateClock();
            await this.fetchData();
        });
        onMounted(() => {
            this.refreshTimer = setInterval(() => this.fetchData({ silent: true }), 30000);
            this.clockTimer = setInterval(() => this.updateClock(), 30000);
        });
        onWillUnmount(() => {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
            if (this.clockTimer) clearInterval(this.clockTimer);
        });
    }

    async fetchData({ silent = false } = {}) {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = result;
            // Explicitly touch the compact payload contract so cached/partial payloads degrade safely.
            this.state.data.stations = result.stations || [];
            this.state.data.queue = result.queue || [];
            this.state.data.kpis = result.kpis || this.state.data.kpis;
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

            const selectedStillExists = this.state.data.stations.some(
                (station) => station.id && station.id === this.state.selectedStationId
            );
            if (!selectedStillExists) {
                const firstBusy = this.state.data.stations.find((station) => station.status === "busy");
                this.state.selectedStationId = firstBusy?.id || false;
            }
        } catch (error) {
            console.error("Car wash dashboard fetch failed", error);
            if (!silent) {
                this.notification.add(_t("Could not load car wash dashboard data."), { type: "danger" });
            }
        } finally {
            this.state.loading = false;
        }
    }

    updateClock() {
        const now = new Date();
        this.state.nowLabel = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        this.state.dateLabel = now.toLocaleDateString([], {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }

    get selectedStation() {
        return this.state.data.stations.find(
            (station) => station.id && station.id === this.state.selectedStationId
        ) || false;
    }

    get filteredQueue() {
        const query = this.state.searchQuery.trim().toLowerCase();
        if (!query) return this.state.data.queue;
        return this.state.data.queue.filter((item) => this.matchesQuery(item, query));
    }

    get filteredStations() {
        const query = this.state.searchQuery.trim().toLowerCase();
        if (!query) return this.state.data.stations;
        return this.state.data.stations.filter((station) => {
            const car = station.current_car || {};
            return this.matchesQuery(station, query) || this.matchesQuery(car, query);
        });
    }

    matchesQuery(item, query) {
        const values = [
            item?.name,
            item?.plate,
            item?.vehicle_model,
            item?.service_name,
            item?.customer_name,
            item?.station_type,
        ];
        return values.some((value) => String(value || "").toLowerCase().includes(query));
    }

    onSearchInput(event) {
        this.state.searchQuery = event.target.value || "";
    }

    selectStation(id) {
        this.state.selectedStationId = id;
    }

    closeStation() {
        this.state.selectedStationId = false;
    }

    async manualRefresh() {
        await this.fetchData();
        this.notification.add(_t("Dashboard updated."), { type: "success" });
    }

    openQueue() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Waiting Queue"),
            res_model: "mrp.production",
            views: [[false, "list"], [false, "form"]],
            domain: this.state.data.queue_domain || [],
            target: "current",
        });
    }

    openProduction(id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Car Wash Order"),
            res_model: "mrp.production",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openWorkorder(id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Wash Operation"),
            res_model: "mrp.workorder",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openShopFloor() {
        await this.action.doAction(this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display");
    }

    async openStationSettings() {
        await this.action.doAction("car_wash_dashboard.action_car_wash_workcenters");
    }
}

CarWashDashboard.template = "car_wash_dashboard.CarWashDashboard";
CarWashDashboard.components = { KpiCard, QueuePanel, StationCard, StationDetail };
CarWashDashboard.props = {};

registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
