/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { KpiCard } from "./components/kpi_card";
import { QueuePanel } from "./components/queue_panel";
import { StationCard } from "./components/station_card";
import { StationDetail } from "./components/station_detail";
import { vehicleImagePath } from "./vehicle_visuals";

const BUS_NOTIFICATION_TYPE = "car_wash_dashboard_refresh";
const POLLING_FALLBACK_MS = 30000;
const FEEDBACK_HIDE_MS = 1600;

export class CarWashDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.busService = useService("bus_service");

        this.state = useState({
            loading: true,
            selectedStationId: false,
            searchQuery: "",
            focusMode: "overview",
            viewMode: "grid",
            audioEnabled: true,
            feedbackText: "",
            feedbackTone: "info",
            lastUpdate: "",
            nowLabel: "",
            dateLabel: "",
            data: {
                company_id: false,
                company_name: "",
                user_name: "",
                user_role: "",
                user_initials: "",
                kpis: {
                    active_cars: 0,
                    waiting_queue: 0,
                    available_stations: 0,
                    finished_today: 0,
                },
                queue: [],
                stations: [],
                finished_today_items: [],
                queue_domain: [],
                finished_today_domain: [],
                wash_order_domain: [],
                station_configuration: { warnings: [] },
                shop_floor_action: "mrp_workorder.action_mrp_display",
            },
        });

        this.refreshTimer = null;
        this.clockTimer = null;
        this.realtimeDebounceTimer = null;
        this.feedbackTimer = null;
        this.busChannel = null;

        // OWL event handlers and callbacks are passed around as function references.
        // Bind every interactive handler once so `this` always points to the dashboard
        // instance, whether the handler is called from this template or a child component.
        this.onBusNotification = this.onBusNotification.bind(this);
        this.onSearchInput = this.onSearchInput.bind(this);
        this.activateFocus = this.activateFocus.bind(this);
        this.clearFocus = this.clearFocus.bind(this);
        this.showStationDirectory = this.showStationDirectory.bind(this);
        this.toggleViewMode = this.toggleViewMode.bind(this);
        this.toggleAudio = this.toggleAudio.bind(this);
        this.showLiveStatus = this.showLiveStatus.bind(this);
        this.selectStation = this.selectStation.bind(this);
        this.closeStation = this.closeStation.bind(this);
        this.manualRefresh = this.manualRefresh.bind(this);
        this.openQueue = this.openQueue.bind(this);
        this.openCars = this.openCars.bind(this);
        this.openServices = this.openServices.bind(this);
        this.openCustomers = this.openCustomers.bind(this);
        this.openReports = this.openReports.bind(this);
        this.openProduction = this.openProduction.bind(this);
        this.openWorkorder = this.openWorkorder.bind(this);
        this.openShopFloor = this.openShopFloor.bind(this);
        this.openStationSettings = this.openStationSettings.bind(this);

        onWillStart(async () => {
            this.updateClock();
            await this.fetchData();
        });

        onMounted(() => {
            this.busService.addEventListener("notification", this.onBusNotification);
            this.ensureBusChannel();
            this.refreshTimer = setInterval(
                () => this.fetchData({ silent: true }),
                POLLING_FALLBACK_MS
            );
            this.clockTimer = setInterval(() => this.updateClock(), 30000);
        });

        onWillUnmount(() => {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
            if (this.clockTimer) clearInterval(this.clockTimer);
            if (this.realtimeDebounceTimer) clearTimeout(this.realtimeDebounceTimer);
            if (this.feedbackTimer) clearTimeout(this.feedbackTimer);
            this.busService.removeEventListener("notification", this.onBusNotification);
            if (this.busChannel && this.busService.deleteChannel) {
                this.busService.deleteChannel(this.busChannel);
            }
        });
    }

    ensureBusChannel() {
        const companyId = Number(this.state.data.company_id || 0);
        if (!companyId) return;
        const channel = `car_wash_dashboard_company_${companyId}`;
        if (channel === this.busChannel) return;
        if (this.busChannel && this.busService.deleteChannel) {
            this.busService.deleteChannel(this.busChannel);
        }
        this.busChannel = channel;
        this.busService.addChannel(channel);
    }

    onBusNotification(event) {
        const notifications = event?.detail || [];
        const matches = notifications.some((notification) => {
            const type = notification?.type || notification?.[0];
            return type === BUS_NOTIFICATION_TYPE;
        });
        if (!matches) return;

        if (this.realtimeDebounceTimer) clearTimeout(this.realtimeDebounceTimer);
        this.realtimeDebounceTimer = setTimeout(
            () => this.fetchData({ silent: true }),
            180
        );
    }

    async fetchData({ silent = false } = {}) {
        try {
            const result = await this.orm.call("mrp.production", "get_dashboard_data", []);
            this.state.data = {
                ...this.state.data,
                ...result,
                stations: result.stations || [],
                queue: result.queue || [],
                finished_today_items: result.finished_today_items || [],
                kpis: result.kpis || this.state.data.kpis,
                station_configuration: result.station_configuration || { warnings: [] },
            };
            this.ensureBusChannel();
            this.state.lastUpdate = new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });

            const selectedStillExists = this.state.data.stations.some(
                (station) => station.id && station.id === this.state.selectedStationId
            );
            if (!selectedStillExists) {
                this.state.selectedStationId = false;
            }
        } catch (error) {
            console.error("Car wash dashboard fetch failed", error);
            if (!silent) {
                this.notification.add(_t("Could not load car wash dashboard data."), {
                    type: "danger",
                });
            }
        } finally {
            this.state.loading = false;
        }
    }

    updateClock() {
        const now = new Date();
        this.state.nowLabel = now.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
        this.state.dateLabel = now.toLocaleDateString([], {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric",
        });
    }

    get selectedStation() {
        return (
            this.state.data.stations.find(
                (station) => station.id && station.id === this.state.selectedStationId
            ) || false
        );
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

    get activeStations() {
        return this.filteredStations.filter((station) => Boolean(station.current_car));
    }

    get availableStations() {
        return this.filteredStations.filter(
            (station) => !station.is_placeholder && station.status === "available"
        );
    }

    get finishedTodayItems() {
        const query = this.state.searchQuery.trim().toLowerCase();
        const items = this.state.data.finished_today_items || [];
        if (!query) return items;
        return items.filter((item) => this.matchesQuery(item, query));
    }

    get focusTitle() {
        return {
            active: _t("Cars In Stations"),
            waiting: _t("General Waiting Queue"),
            available: _t("Available Stations"),
            finished: _t("Finished Today"),
            stations: _t("Station Details"),
        }[this.state.focusMode] || _t("Dashboard Overview");
    }

    get focusSubtitle() {
        return {
            active: _t("Only cars currently running inside a wash station."),
            waiting: _t("Only cars waiting for the next available station."),
            available: _t("Only stations ready to receive the next car."),
            finished: _t("Only wash orders completed today."),
            stations: _t("Live status and current car for every wash station."),
        }[this.state.focusMode] || "";
    }

    get focusCount() {
        return {
            active: this.activeStations.length,
            waiting: this.filteredQueue.length,
            available: this.availableStations.length,
            finished: this.finishedTodayItems.length,
            stations: this.filteredStations.length,
        }[this.state.focusMode] || 0;
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

    vehicleImage(item) {
        return vehicleImagePath(item);
    }

    sizeLabel(value) {
        return value === "large" ? _t("Large") : value === "small" ? _t("Small") : "—";
    }

    stationTypeLabel(value) {
        return {
            automatic: _t("Automatic"),
            polishing: _t("Polishing"),
            general: _t("General"),
        }[value] || _t("General");
    }

    stationStatusLabel(value) {
        return {
            available: _t("Available"),
            busy: _t("Busy"),
            finishing: _t("Finishing"),
            conflict: _t("Check Station"),
            not_configured: _t("Not Configured"),
        }[value] || _t("Available");
    }

    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} min`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}h ${rest}m` : `${hours}h`;
    }

    formatFinishedAt(value) {
        if (!value) return "—";
        const normalized = String(value).includes("T") ? value : String(value).replace(" ", "T") + "Z";
        const parsed = new Date(normalized);
        if (Number.isNaN(parsed.getTime())) return value;
        return parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    onSearchInput(event) {
        this.state.searchQuery = event.target.value || "";
    }

    playUiTone(kind = "tap") {
        if (!this.state.audioEnabled || typeof window === "undefined") return;
        try {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (!AudioContextClass) return;
            const context = new AudioContextClass();
            const oscillator = context.createOscillator();
            const gain = context.createGain();
            const frequencies = { tap: 520, nav: 610, success: 760, close: 410 };
            oscillator.type = "sine";
            oscillator.frequency.value = frequencies[kind] || frequencies.tap;
            gain.gain.setValueAtTime(0.0001, context.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.025, context.currentTime + 0.008);
            gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.065);
            oscillator.connect(gain);
            gain.connect(context.destination);
            oscillator.start();
            oscillator.stop(context.currentTime + 0.07);
            oscillator.addEventListener("ended", () => context.close());
        } catch (error) {
            console.debug("Dashboard sound feedback unavailable", error);
        }
    }

    showFeedback(text, tone = "info") {
        this.state.feedbackText = text;
        this.state.feedbackTone = tone;
        if (this.feedbackTimer) clearTimeout(this.feedbackTimer);
        this.feedbackTimer = setTimeout(() => {
            this.state.feedbackText = "";
        }, FEEDBACK_HIDE_MS);
    }

    activateFocus(mode) {
        this.state.focusMode = mode;
        this.state.selectedStationId = false;
        this.playUiTone("tap");
        this.showFeedback(this.focusTitle);
    }

    clearFocus() {
        this.state.focusMode = "overview";
        this.state.selectedStationId = false;
        this.playUiTone("close");
        this.showFeedback(_t("Dashboard overview"));
    }

    showStationDirectory() {
        this.activateFocus("stations");
    }

    toggleViewMode() {
        this.state.viewMode = this.state.viewMode === "grid" ? "list" : "grid";
        this.playUiTone("tap");
        this.showFeedback(
            this.state.viewMode === "grid" ? _t("Grid view") : _t("List view")
        );
    }

    toggleAudio() {
        this.state.audioEnabled = !this.state.audioEnabled;
        if (this.state.audioEnabled) {
            this.playUiTone("success");
        }
        this.showFeedback(
            this.state.audioEnabled ? _t("Sound feedback on") : _t("Sound feedback off")
        );
    }

    showLiveStatus() {
        this.playUiTone("tap");
        this.showFeedback(_t("Live station updates are connected."), "success");
    }

    selectStation(id) {
        if (!id) return;
        this.state.focusMode = "overview";
        this.state.selectedStationId = id;
        this.playUiTone("nav");
        const station = this.state.data.stations.find((item) => item.id === id);
        this.showFeedback(
            station ? `${_t("Station details")}: ${station.name}` : _t("Station details")
        );
    }

    closeStation() {
        this.state.selectedStationId = false;
        this.playUiTone("close");
    }

    async manualRefresh() {
        await this.fetchData();
        this.playUiTone("success");
        this.showFeedback(_t("Dashboard updated."), "success");
    }

    openQueue() {
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Waiting Queue"),
            res_model: "mrp.production",
            views: [[false, "list"], [false, "form"]],
            domain: this.state.data.queue_domain || [],
            target: "current",
        });
    }

    openCars() {
        this.playUiTone("nav");
        const domain = this.state.data.wash_order_domain || [["company_id", "=", this.state.data.company_id]];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Car Wash Orders"),
            res_model: "mrp.production",
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }

    openServices() {
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Services"),
            res_model: "product.product",
            views: [[false, "list"], [false, "form"]],
            domain: [["sale_ok", "=", true]],
            target: "current",
        });
    }

    openCustomers() {
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Customers"),
            res_model: "res.partner",
            views: [[false, "list"], [false, "form"]],
            domain: [["customer_rank", ">", 0]],
            target: "current",
        });
    }

    openReports() {
        this.playUiTone("nav");
        const domain = [
            ...(this.state.data.wash_order_domain || [["company_id", "=", this.state.data.company_id]]),
            ["state", "=", "done"],
        ];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Completed Car Wash Orders"),
            res_model: "mrp.production",
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }

    openProduction(id) {
        if (!id) return;
        this.playUiTone("nav");
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
        this.playUiTone("nav");
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
        this.playUiTone("nav");
        await this.action.doAction(
            this.state.data.shop_floor_action || "mrp_workorder.action_mrp_display"
        );
    }

    async openStationSettings() {
        this.playUiTone("nav");
        await this.action.doAction("car_wash_dashboard.action_car_wash_workcenters");
    }
}

CarWashDashboard.template = "car_wash_dashboard.CarWashDashboard";
CarWashDashboard.components = { KpiCard, QueuePanel, StationCard, StationDetail };
CarWashDashboard.props = {};

registry.category("actions").add("car_wash_dashboard.client_action", CarWashDashboard);
