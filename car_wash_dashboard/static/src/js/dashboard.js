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
const THEME_STORAGE_KEY = "car_wash_dashboard_theme";

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
            page: "operations",
            focusMode: "overview",
            viewMode: "grid",
            theme: this.loadThemePreference(),
            isRtl: this.detectRtl(),
            analyticsPeriod: "today",
            analyticsLoading: false,
            analyticsLoaded: false,
            analyticsDetailLoading: false,
            analyticsDetail: false,
            analytics: {
                period: "today",
                period_label: "",
                currency_code: "LYD",
                currency_symbol: "",
                kpis: {
                    today_revenue: 0,
                    today_revenue_growth: false,
                    monthly_revenue: 0,
                    monthly_revenue_growth: false,
                    total_washes_today: 0,
                    active_customers: 0,
                    average_ticket: 0,
                },
                daily_washes: [],
                popular_services: [],
                station_utilization: { overall: 0, stations: [] },
                top_customers: [],
                low_supplies: [],
                revenue_trend: [],
                customer_mix: { returning: 0, new: 0, returning_percent: 0, new_percent: 0 },
                revenue_by_category: [],
                recent_activity: [],
            },
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
        this.showAnalytics = this.showAnalytics.bind(this);
        this.showOperations = this.showOperations.bind(this);
        this.fetchAnalytics = this.fetchAnalytics.bind(this);
        this.setAnalyticsPeriod = this.setAnalyticsPeriod.bind(this);
        this.onAnalyticsPeriodChange = this.onAnalyticsPeriodChange.bind(this);
        this.openAnalyticsDetail = this.openAnalyticsDetail.bind(this);
        this.closeAnalyticsDetail = this.closeAnalyticsDetail.bind(this);
        this.openAnalyticsRecord = this.openAnalyticsRecord.bind(this);
        this.activateFocus = this.activateFocus.bind(this);
        this.clearFocus = this.clearFocus.bind(this);
        this.showStationDirectory = this.showStationDirectory.bind(this);
        this.toggleViewMode = this.toggleViewMode.bind(this);
        this.toggleAudio = this.toggleAudio.bind(this);
        this.toggleTheme = this.toggleTheme.bind(this);
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
            this.state.isRtl = this.detectRtl();
            this.busService.addEventListener("notification", this.onBusNotification);
            this.ensureBusChannel();
            this.refreshTimer = setInterval(() => {
                if (this.state.page === "analytics") {
                    this.fetchAnalytics({ silent: true });
                } else {
                    this.fetchData({ silent: true });
                }
            }, POLLING_FALLBACK_MS);
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


    loadThemePreference() {
        try {
            if (typeof window === "undefined" || !window.localStorage) return "light";
            const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
            return stored === "dark" ? "dark" : "light";
        } catch {
            return "light";
        }
    }

    saveThemePreference(theme) {
        try {
            if (typeof window === "undefined" || !window.localStorage) return;
            window.localStorage.setItem(THEME_STORAGE_KEY, theme === "dark" ? "dark" : "light");
        } catch {
            // Browser privacy settings may block storage; theme still works for this session.
        }
    }

    detectRtl() {
        if (typeof document === "undefined") return false;
        const rootDirection = document.documentElement?.getAttribute("dir");
        const bodyDirection = document.body?.getAttribute("dir");
        if (rootDirection === "rtl" || bodyDirection === "rtl") return true;
        if (document.body?.classList?.contains("o_rtl")) return true;
        try {
            const rootComputed = window.getComputedStyle(document.documentElement).direction;
            const bodyComputed = document.body ? window.getComputedStyle(document.body).direction : "";
            return rootComputed === "rtl" || bodyComputed === "rtl";
        } catch {
            return false;
        }
    }

    toggleTheme() {
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        this.saveThemePreference(this.state.theme);
        this.playUiTone("tap");
        this.showFeedback(
            this.state.theme === "dark" ? _t("Dark mode") : _t("Light mode")
        );
    }

    get pageTitle() {
        return this.state.page === "analytics" ? _t("Business Analytics") : _t("Car Wash Dashboard");
    }

    get pageSubtitle() {
        return this.state.page === "analytics"
            ? _t("Insights for a cleaner, more profitable tomorrow.")
            : _t("Live overview of stations, queue and today’s activity.");
    }

    get viewModeLabel() {
        return this.state.viewMode === "grid" ? _t("Grid View") : _t("List View");
    }

    get analyticsPeriodLabel() {
        return this.state.analyticsPeriod === "month" ? _t("This Month") : _t("Today");
    }

    get themeToggleTitle() {
        return this.state.theme === "dark" ? _t("Switch to light mode") : _t("Switch to dark mode");
    }

    get audioToggleTitle() {
        return this.state.audioEnabled ? _t("Mute sound feedback") : _t("Enable sound feedback");
    }

    get analyticsDisplayPeriodLabel() {
        if (this.state.analyticsPeriod !== "month") {
            return this.state.dateLabel;
        }
        const now = new Date();
        return now.toLocaleDateString(this.localeTag(), {
            month: "long",
            year: "numeric",
        });
    }

    localeTag() {
        if (typeof document === "undefined") return undefined;
        const lang = document.documentElement?.lang || "";
        return lang ? lang.replaceAll("_", "-") : undefined;
    }

    currentVehicleLabel() {
        return _t("Current vehicle");
    }

    get defaultUserName() {
        return _t("Odoo User");
    }

    get defaultUserRole() {
        return _t("Operator");
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
        this.realtimeDebounceTimer = setTimeout(() => {
            if (this.state.page === "analytics") {
                this.fetchAnalytics({ silent: true });
            } else {
                this.fetchData({ silent: true });
            }
        }, 180);
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

    async fetchAnalytics({ silent = false } = {}) {
        this.state.analyticsLoading = true;
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_business_analytics_data",
                [this.state.analyticsPeriod]
            );
            this.state.analytics = {
                ...this.state.analytics,
                ...result,
                kpis: result.kpis || this.state.analytics.kpis,
                daily_washes: result.daily_washes || [],
                popular_services: result.popular_services || [],
                station_utilization: result.station_utilization || { overall: 0, stations: [] },
                top_customers: result.top_customers || [],
                low_supplies: result.low_supplies || [],
                revenue_trend: result.revenue_trend || [],
                customer_mix: result.customer_mix || this.state.analytics.customer_mix,
                revenue_by_category: result.revenue_by_category || [],
                recent_activity: result.recent_activity || [],
            };
            this.state.analyticsLoaded = true;
            this.state.lastUpdate = new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch (error) {
            console.error("Car wash business analytics fetch failed", error);
            if (!silent) {
                this.notification.add(_t("Could not load car wash business analytics."), {
                    type: "danger",
                });
            }
        } finally {
            this.state.analyticsLoading = false;
        }
    }

    async showAnalytics() {
        this.state.page = "analytics";
        this.state.analyticsDetail = false;
        this.state.selectedStationId = false;
        this.state.focusMode = "overview";
        this.playUiTone("nav");
        this.showFeedback(_t("Business Analytics"));
        await this.fetchAnalytics();
    }

    showOperations() {
        this.state.page = "operations";
        this.state.analyticsDetail = false;
        this.state.focusMode = "overview";
        this.state.selectedStationId = false;
        this.playUiTone("nav");
        this.showFeedback(_t("Car Wash Dashboard"));
    }

    async setAnalyticsPeriod(period) {
        const normalized = period === "month" ? "month" : "today";
        if (this.state.analyticsPeriod === normalized && this.state.analyticsLoaded) return;
        this.state.analyticsPeriod = normalized;
        this.state.analyticsDetail = false;
        this.playUiTone("tap");
        await this.fetchAnalytics();
    }

    async onAnalyticsPeriodChange(event) {
        await this.setAnalyticsPeriod(event.target.value);
    }

    async openAnalyticsDetail(detailType, key = false, label = "") {
        if (!detailType) return;
        this.state.analyticsDetailLoading = true;
        this.state.analyticsDetail = {
            detail_type: detailType,
            title: label || _t("Analytics Detail"),
            subtitle: _t("Loading relevant information…"),
            summary: [],
            rows: [],
        };
        this.playUiTone("tap");
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_business_analytics_detail",
                [detailType, key, this.state.analyticsPeriod]
            );
            this.state.analyticsDetail = {
                detail_type: detailType,
                title: result.title || label || _t("Analytics Detail"),
                subtitle: result.subtitle || "",
                summary: result.summary || [],
                rows: result.rows || [],
            };
            this.showFeedback(this.state.analyticsDetail.title);
        } catch (error) {
            console.error("Car wash analytics drill-down failed", error);
            this.state.analyticsDetail = false;
            this.notification.add(_t("Could not load analytics detail."), { type: "danger" });
        } finally {
            this.state.analyticsDetailLoading = false;
        }
    }

    closeAnalyticsDetail() {
        this.state.analyticsDetail = false;
        this.state.analyticsDetailLoading = false;
        this.playUiTone("close");
    }

    openAnalyticsRecord(row) {
        if (!row?.model || !row?.res_id) return;
        this.playUiTone("nav");
        const names = {
            "pos.order": _t("POS Order"),
            "mrp.production": _t("Car Wash Order"),
            "mrp.workorder": _t("Wash Operation"),
            "res.partner": _t("Customer"),
            "product.product": _t("Product"),
        };
        this.action.doAction({
            type: "ir.actions.act_window",
            name: names[row.model] || _t("Odoo Record"),
            res_model: row.model,
            res_id: Number(row.res_id),
            views: [[false, "form"]],
            target: "current",
        });
    }

    get analyticsLineDots() {
        const rows = this.state.analytics.daily_washes || [];
        if (!rows.length) return [];
        const maxValue = Math.max(1, ...rows.map((row) => Number(row.value || 0)));
        const width = 560;
        const height = 150;
        const step = rows.length > 1 ? width / (rows.length - 1) : width;
        return rows.map((row, index) => ({
            x: Math.round(index * step),
            y: Math.round(height - (Number(row.value || 0) / maxValue) * 125),
            value: Number(row.value || 0),
            label: row.label,
            bucket_key: row.bucket_key ?? index,
        }));
    }

    get analyticsLinePoints() {
        return this.analyticsLineDots.map((point) => `${point.x},${point.y}`).join(" ");
    }

    get analyticsLineAreaPoints() {
        const dots = this.analyticsLineDots;
        if (!dots.length) return "0,150 560,150";
        return `0,150 ${dots.map((point) => `${point.x},${point.y}`).join(" ")} 560,150`;
    }

    analyticsBarStyle(value, rows) {
        const maxValue = Math.max(1, ...(rows || []).map((row) => Number(row.value || 0)));
        const percent = Math.max(4, Math.round((Number(value || 0) / maxValue) * 100));
        return `height:${percent}%`;
    }

    stationDonutStyle() {
        const value = Math.max(0, Math.min(100, Number(this.state.analytics.station_utilization?.overall || 0)));
        const p1 = value * 0.34;
        const p2 = value * 0.68;
        return `background:conic-gradient(#168cf2 0 ${p1}%,#18b7e8 ${p1}% ${p2}%,#55cbed ${p2}% ${value}%,#e7eef7 ${value}% 100%)`;
    }

    customerDonutStyle() {
        const value = Math.max(0, Math.min(100, Number(this.state.analytics.customer_mix?.returning_percent || 0)));
        return `background:conic-gradient(#138ff0 0 ${value}%,#73cff3 ${value}% 100%)`;
    }

    categoryDonutStyle() {
        const rows = this.state.analytics.revenue_by_category || [];
        const colors = ["#138ff0", "#1eb8e9", "#55c8ec", "#78d4ef", "#a8ddf3"];
        if (!rows.length) return "background:#edf3f8";
        let cursor = 0;
        const segments = [];
        rows.forEach((row, index) => {
            const end = Math.min(100, cursor + Number(row.percent || 0));
            segments.push(`${colors[index % colors.length]} ${cursor}% ${end}%`);
            cursor = end;
        });
        if (cursor < 100) segments.push(`#e7eef7 ${cursor}% 100%`);
        return `background:conic-gradient(${segments.join(",")})`;
    }

    categoryColor(index) {
        return ["#138ff0", "#1eb8e9", "#55c8ec", "#78d4ef", "#a8ddf3"][index % 5];
    }

    supplyBarStyle(value) {
        const percent = Math.max(0, Math.min(100, Number(value || 0)));
        return `width:${percent}%`;
    }

    roundNumber(value) {
        const number = Number(value || 0);
        return Number.isFinite(number) ? Math.round(number) : 0;
    }

    formatMoney(value) {
        const number = Number(value || 0);
        const code = this.state.analytics.currency_code || "LYD";
        try {
            return new Intl.NumberFormat(this.localeTag(), {
                style: "currency",
                currency: code,
                maximumFractionDigits: 0,
            }).format(number);
        } catch {
            return `${number.toLocaleString()} ${code}`;
        }
    }

    growthText(value) {
        if (value === false || value === null || value === undefined) return "—";
        const number = Number(value || 0);
        return `${number >= 0 ? "+" : ""}${number}%`;
    }

    growthClass(value) {
        if (value === false || value === null || value === undefined) return "neutral";
        return Number(value) >= 0 ? "up" : "down";
    }

    activityTime(value) {
        if (!value) return "—";
        const parsed = new Date(String(value).replace(" ", "T") + (String(value).includes("Z") ? "" : "Z"));
        if (Number.isNaN(parsed.getTime())) return "—";
        return parsed.toLocaleTimeString(this.localeTag(), { hour: "2-digit", minute: "2-digit" });
    }

    updateClock() {
        const now = new Date();
        this.state.nowLabel = now.toLocaleTimeString(this.localeTag(), {
            hour: "2-digit",
            minute: "2-digit",
        });
        this.state.dateLabel = now.toLocaleDateString(this.localeTag(), {
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
        if (minutes < 60) return `${minutes} ${_t("min")}`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}${_t("h")} ${rest}${_t("m")}` : `${hours}${_t("h")}`;
    }

    formatFinishedAt(value) {
        if (!value) return "—";
        const normalized = String(value).includes("T") ? value : String(value).replace(" ", "T") + "Z";
        const parsed = new Date(normalized);
        if (Number.isNaN(parsed.getTime())) return value;
        return parsed.toLocaleTimeString(this.localeTag(), { hour: "2-digit", minute: "2-digit" });
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
        this.state.page = "operations";
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
        if (this.state.page === "analytics") {
            await this.fetchAnalytics();
        } else {
            await this.fetchData();
        }
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
