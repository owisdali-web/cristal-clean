/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { KpiCard } from "./components/kpi_card";
import { QueuePanel } from "./components/queue_panel";
import { StationCard } from "./components/station_card";
import { StationDetail } from "./components/station_detail";
import { vehicleImagePath } from "./vehicle_visuals";
import { translateUi } from "./ui_translations";

const BUS_NOTIFICATION_TYPE = "car_wash_dashboard_refresh";
const POLLING_FALLBACK_MS = 30000;
const FEEDBACK_HIDE_MS = 1600;
const THEME_STORAGE_KEY = "car_wash_dashboard_theme";
const CUSTOMER_FEATURE_ROTATION_MS = 120000;

export class CarWashDashboard extends Component {
    tr(text, ...args) {
        return translateUi(text, ...args);
    }

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
            customerFeaturedIndex: 0,
            isCustomerTvMode: false,
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
            customersLoading: false,
            customersLoaded: false,
            selectedCustomerId: false,
            customerDetailLoading: false,
            customerDetail: false,
            customerBehaviorFilter: "",
            customerFilters: {
                search: "",
                segment: "",
                service_id: "",
                activity_period: "all",
            },
            customersData: {
                currency_code: "LYD",
                currency_symbol: "",
                high_value_threshold: 0,
                kpis: {
                    total_customers: 0,
                    new_this_month: 0,
                    returning_customers: 0,
                    frequent_customers: 0,
                    inactive_customers: 0,
                    average_spend: 0,
                },
                customers: [],
                top_by_revenue: [],
                most_frequent: [],
                new_vs_returning: [],
                service_preferences: [],
                filter_options: { services: [], segments: [] },
            },
            carsLoading: false,
            carsPeriod: "today",
            carsStatusFilter: "all",
            carsData: {
                period_label: "",
                kpis: { total_cars: 0, finished_cars: 0, waiting_cars: 0, total_revenue: 0 },
                operations: [],
            },
            servicesLoading: false,
            servicesPeriod: "today",
            servicesData: {
                period_label: "",
                currency_code: "LYD",
                currency_symbol: "",
                kpis: { total_revenue: 0 },
                services: [],
                filter_options: { services: [] },
            },
            reportsLoading: false,
            reportsLoaded: false,
            reportDetail: false,
            reportExporting: false,
            reportExportFormat: "",
            reportTab: "overview",
            reportFilters: {
                period: "today",
                date_from: "",
                date_to: "",
                station_id: "",
                service_id: "",
                vehicle_size: "",
                customer_id: "",
                status: "",
            },
            reports: {
                period_label: "",
                date_from: "",
                date_to: "",
                currency_code: "LYD",
                currency_symbol: "",
                kpis: { total_cars: 0, finished_cars: 0, waiting_cars: 0, total_revenue: 0, average_ticket: 0, unique_customers: 0 },
                revenue_trend: [],
                cars_by_service: [],
                payment_methods: [],
                transactions: [],
                operations: [],
                services: [],
                stations: [],
                customers: [],
                supplies: [],
                exceptions: [],
                filter_options: { stations: [], services: [], customers: [] },
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
        this.customerFeatureTimer = null;
        this.customerReadyInitialized = false;
        this.customerReadySeenIds = new Set();

        // OWL event handlers and callbacks are passed around as function references.
        // Bind every interactive handler once so `this` always points to the dashboard
        // instance, whether the handler is called from this template or a child component.
        this.onBusNotification = this.onBusNotification.bind(this);
        this.onSearchInput = this.onSearchInput.bind(this);
        this.showAnalytics = this.showAnalytics.bind(this);
        this.showCustomerDisplay = this.showCustomerDisplay.bind(this);
        this.advanceFeaturedVehicle = this.advanceFeaturedVehicle.bind(this);
        this.toggleCustomerTvMode = this.toggleCustomerTvMode.bind(this);
        this.onCustomerFullscreenChange = this.onCustomerFullscreenChange.bind(this);
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
        this.fetchCars = this.fetchCars.bind(this);
        this.setCarsPeriod = this.setCarsPeriod.bind(this);
        this.setCarsStatusFilter = this.setCarsStatusFilter.bind(this);
        this.openCarRecord = this.openCarRecord.bind(this);
        this.openCarOrders = this.openCarOrders.bind(this);
        this.openServices = this.openServices.bind(this);
        this.fetchServices = this.fetchServices.bind(this);
        this.setServicesPeriod = this.setServicesPeriod.bind(this);
        this.openServiceRecord = this.openServiceRecord.bind(this);
        this.manageServices = this.manageServices.bind(this);
        this.openCustomers = this.openCustomers.bind(this);
        this.fetchCustomers = this.fetchCustomers.bind(this);
        this.onCustomerFilterChange = this.onCustomerFilterChange.bind(this);
        this.applyCustomerSegment = this.applyCustomerSegment.bind(this);
        this.applyCustomerService = this.applyCustomerService.bind(this);
        this.applyCustomerBehavior = this.applyCustomerBehavior.bind(this);
        this.resetCustomerFilters = this.resetCustomerFilters.bind(this);
        this.selectCustomer = this.selectCustomer.bind(this);
        this.closeCustomerDetail = this.closeCustomerDetail.bind(this);
        this.openCustomerRecord = this.openCustomerRecord.bind(this);
        this.openReports = this.openReports.bind(this);
        this.fetchReports = this.fetchReports.bind(this);
        this.setReportTab = this.setReportTab.bind(this);
        this.onReportFilterChange = this.onReportFilterChange.bind(this);
        this.applyReportFilters = this.applyReportFilters.bind(this);
        this.resetReportFilters = this.resetReportFilters.bind(this);
        this.applyReportPreset = this.applyReportPreset.bind(this);
        this.exportReport = this.exportReport.bind(this);
        this.printReport = this.printReport.bind(this);
        this.openReportDetail = this.openReportDetail.bind(this);
        this.closeReportDetail = this.closeReportDetail.bind(this);
        this.openReportRecord = this.openReportRecord.bind(this);
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
                } else if (this.state.page === "reports") {
                    this.fetchReports({ silent: true });
                } else if (this.state.page === "customers") {
                    this.fetchCustomers({ silent: true });
                } else if (this.state.page === "cars") {
                    this.fetchCars({ silent: true });
                } else if (this.state.page === "services") {
                    this.fetchServices({ silent: true });
                } else {
                    this.fetchData({ silent: true });
                }
            }, POLLING_FALLBACK_MS);
            this.clockTimer = setInterval(() => this.updateClock(), 30000);
            this.customerFeatureTimer = setInterval(() => {
                if (this.state.page === "customer_display") {
                    this.advanceFeaturedVehicle();
                }
            }, CUSTOMER_FEATURE_ROTATION_MS);
            if (typeof document !== "undefined") {
                document.addEventListener("fullscreenchange", this.onCustomerFullscreenChange);
            }
        });

        onWillUnmount(() => {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
            if (this.clockTimer) clearInterval(this.clockTimer);
            if (this.realtimeDebounceTimer) clearTimeout(this.realtimeDebounceTimer);
            if (this.feedbackTimer) clearTimeout(this.feedbackTimer);
            if (this.customerFeatureTimer) clearInterval(this.customerFeatureTimer);
            if (typeof document !== "undefined") {
                document.removeEventListener("fullscreenchange", this.onCustomerFullscreenChange);
            }
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
        const rootLanguage = (document.documentElement?.getAttribute("lang") || "").toLowerCase();
        const bodyLanguage = (document.body?.getAttribute("lang") || "").toLowerCase();
        if (rootLanguage.startsWith("ar") || bodyLanguage.startsWith("ar")) return true;
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
            this.state.theme === "dark" ? this.tr("Dark mode") : this.tr("Light mode")
        );
    }

    get pageTitle() {
        if (this.state.page === "cars") return this.tr("Cars & Wash Orders");
        if (this.state.page === "services") return this.tr("Wash Services");
        if (this.state.page === "analytics") return this.tr("Business Analytics");
        if (this.state.page === "reports") return this.tr("Reports");
        if (this.state.page === "customers") return this.tr("Customer Intelligence");
        if (this.state.page === "customer_display") return this.tr("Live Car Journey");
        return this.tr("Car Wash Dashboard");
    }

    get pageSubtitle() {
        if (this.state.page === "cars") {
            return this.tr("Track every vehicle from waiting to completed wash.");
        }
        if (this.state.page === "services") {
            return this.tr("See which wash services are used, earning, and taking time.");
        }
        if (this.state.page === "analytics") {
            return this.tr("Insights for a cleaner, more profitable tomorrow.");
        }
        if (this.state.page === "reports") {
            return this.tr("Complete reports for your car wash operations.");
        }
        if (this.state.page === "customers") {
            return this.tr("Understand visits, value, vehicles, and customer loyalty.");
        }
        if (this.state.page === "customer_display") {
            return this.tr("A live customer view from check-in to ready for pickup.");
        }
        return this.tr("Live overview of stations, queue and today’s activity.");
    }

    get searchPlaceholder() {
        if (this.state.page === "services") return this.tr("Search services...");
        if (this.state.page === "cars") return this.tr("Search plate, customer, vehicle, or service...");
        if (this.state.page === "customers") return this.tr("Search customers...");
        return this.tr("Search cars, customers, or plates...");
    }

    get viewModeLabel() {
        return this.state.viewMode === "grid" ? this.tr("Grid View") : this.tr("List View");
    }

    get analyticsPeriodLabel() {
        return this.state.analyticsPeriod === "month" ? this.tr("This Month") : this.tr("Today");
    }

    get themeToggleTitle() {
        return this.state.theme === "dark" ? this.tr("Switch to light mode") : this.tr("Switch to dark mode");
    }

    get audioToggleTitle() {
        return this.state.audioEnabled ? this.tr("Mute sound feedback") : this.tr("Enable sound feedback");
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
        return this.tr("Current vehicle");
    }

    get defaultUserName() {
        return this.tr("Odoo User");
    }

    get defaultUserRole() {
        return this.tr("Operator");
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
            } else if (this.state.page === "reports") {
                this.fetchReports({ silent: true });
            } else if (this.state.page === "customers") {
                this.fetchCustomers({ silent: true });
            } else if (this.state.page === "cars") {
                this.fetchCars({ silent: true });
            } else if (this.state.page === "services") {
                this.fetchServices({ silent: true });
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
            this.handleCustomerReadyPriority(this.state.data.finished_today_items || []);
        } catch (error) {
            console.error("Car wash dashboard fetch failed", error);
            if (!silent) {
                this.notification.add(this.tr("Could not load car wash dashboard data."), {
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
                this.notification.add(this.tr("Could not load car wash business analytics."), {
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
        this.showFeedback(this.tr("Business Analytics"));
        await this.fetchAnalytics();
    }

    async fetchReports({ silent = false } = {}) {
        this.state.reportsLoading = true;
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_report_center_data",
                [this.state.reportFilters]
            );
            this.state.reports = {
                ...this.state.reports,
                ...result,
                kpis: result.kpis || this.state.reports.kpis,
                revenue_trend: result.revenue_trend || [],
                cars_by_service: result.cars_by_service || [],
                payment_methods: result.payment_methods || [],
                transactions: result.transactions || [],
                operations: result.operations || [],
                services: result.services || [],
                stations: result.stations || [],
                customers: result.customers || [],
                supplies: result.supplies || [],
                exceptions: result.exceptions || [],
                filter_options: result.filter_options || this.state.reports.filter_options,
            };
            if (!this.state.reportFilters.date_from && result.date_from) this.state.reportFilters.date_from = result.date_from;
            if (!this.state.reportFilters.date_to && result.date_to) this.state.reportFilters.date_to = result.date_to;
            this.state.reportsLoaded = true;
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (error) {
            console.error("Car wash report center fetch failed", error);
            if (!silent) this.notification.add(this.tr("Could not load report center data."), { type: "danger" });
        } finally {
            this.state.reportsLoading = false;
        }
    }

    async openReports() {
        this.state.page = "reports";
        this.state.analyticsDetail = false;
        this.state.reportDetail = false;
        this.state.selectedStationId = false;
        this.state.focusMode = "overview";
        this.playUiTone("nav");
        this.showFeedback(this.tr("Reports"));
        await this.fetchReports();
    }

    setReportTab(tab) {
        const allowed = ["overview", "operations", "revenue", "services", "stations", "customers", "supplies", "exceptions"];
        this.state.reportTab = allowed.includes(tab) ? tab : "overview";
        this.state.reportDetail = false;
        this.playUiTone("tap");
    }

    onReportFilterChange(field, event) {
        if (!(field in this.state.reportFilters)) return;
        this.state.reportFilters[field] = event?.target?.value ?? "";
    }

    async applyReportFilters() {
        await this.fetchReports();
        this.playUiTone("success");
        this.showFeedback(this.tr("Report filters applied."), "success");
    }

    async resetReportFilters() {
        this.state.reportFilters = {
            period: "today", date_from: "", date_to: "", station_id: "", service_id: "", vehicle_size: "", customer_id: "", status: "",
        };
        this.state.reportTab = "overview";
        this.state.reportDetail = false;
        await this.fetchReports();
        this.showFeedback(this.tr("Report filters reset."));
    }

    async applyReportPreset(preset) {
        const presetMap = {
            daily: { period: "today", tab: "overview" },
            monthly: { period: "month", tab: "overview" },
            revenue: { period: "month", tab: "revenue" },
            stations: { period: "month", tab: "stations" },
            customers: { period: "month", tab: "customers" },
            inventory: { period: "today", tab: "supplies" },
        };
        const selected = presetMap[preset] || presetMap.daily;
        this.state.reportFilters.period = selected.period;
        this.state.reportFilters.date_from = "";
        this.state.reportFilters.date_to = "";
        this.state.reportTab = selected.tab;
        await this.fetchReports();
        this.playUiTone("nav");
    }

    reportQueryString() {
        const params = new URLSearchParams();
        Object.entries(this.state.reportFilters || {}).forEach(([key, value]) => {
            if (value !== false && value !== null && value !== undefined && String(value) !== "") params.set(key, String(value));
        });
        return params.toString();
    }

    async exportReport(format) {
        if (this.state.reportExporting || typeof window === "undefined") return;
        const isExcel = format === "xlsx";
        const url = isExcel
            ? `/car_wash_dashboard/reports/xlsx?${this.reportQueryString()}`
            : `/car_wash_dashboard/reports/pdf?${this.reportQueryString()}`;
        this.state.reportExporting = true;
        this.state.reportExportFormat = format;
        this.showFeedback(isExcel ? this.tr("Preparing management workbook…") : this.tr("Preparing PDF report…"));
        try {
            const response = await fetch(url, { credentials: "same-origin" });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const blob = await response.blob();
            const disposition = response.headers.get("Content-Disposition") || "";
            const match = disposition.match(/filename="?([^";]+)"?/i);
            const filename = match?.[1] || (isExcel ? "crystal_clean_management_report.xlsx" : "crystal_clean_management_report.pdf");
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
            this.playUiTone("success");
            this.showFeedback(isExcel ? this.tr("Excel report exported successfully.") : this.tr("PDF report exported successfully."), "success");
        } catch (error) {
            console.error("Car wash report export failed", error);
            this.notification.add(this.tr("Could not export the report."), { type: "danger" });
        } finally {
            this.state.reportExporting = false;
            this.state.reportExportFormat = "";
        }
    }

    printReport() {
        this.playUiTone("tap");
        if (typeof window === "undefined") return;
        const url = `/car_wash_dashboard/reports/print?${this.reportQueryString()}`;
        const popup = window.open(url, "_blank", "noopener");
        if (!popup) this.notification.add(this.tr("Allow pop-ups to print the report."), { type: "warning" });
    }

    openReportDetail(kind, key = false, label = "") {
        this.state.reportDetail = { kind, key, label };
        this.playUiTone("tap");
    }

    closeReportDetail() {
        this.state.reportDetail = false;
        this.playUiTone("close");
    }

    get reportDetailKind() {
        const detail = this.state.reportDetail;
        if (!detail) return "";
        if (detail.kind === "supply") return "supplies";
        if (detail.kind === "exception") return "exceptions";
        if (detail.kind === "station") return "operations";
        if (detail.kind === "customer") return "transactions";
        if (["revenue_bucket", "service", "payment_method"].includes(detail.kind)) return "transactions";
        if (detail.kind === "kpi") {
            if (["total_revenue", "average_ticket"].includes(detail.key)) return "transactions";
            if (detail.key === "unique_customers") return "customers";
            return "operations";
        }
        return "operations";
    }

    get reportDetailTitle() {
        const detail = this.state.reportDetail;
        if (!detail) return "";
        if (detail.label) return detail.label;
        const titles = {
            total_cars: this.tr("Total Cars"), finished_cars: this.tr("Finished Cars"), waiting_cars: this.tr("Waiting Cars"),
            total_revenue: this.tr("Total Revenue"), average_ticket: this.tr("Average Ticket"), unique_customers: this.tr("Unique Customers"),
        };
        return titles[detail.key] || this.tr("Report Details");
    }

    get reportDetailRows() {
        const detail = this.state.reportDetail;
        if (!detail) return [];
        const transactions = this.state.reports.transactions || [];
        const operations = this.state.reports.operations || [];
        if (detail.kind === "revenue_bucket") {
            return transactions.filter((row) => Number(row.trend_bucket_key) === Number(detail.key));
        }
        if (detail.kind === "service") {
            return transactions.filter((row) => Number(row.product_id) === Number(detail.key));
        }
        if (detail.kind === "payment_method") {
            return transactions.filter((row) => (row.payment_methods || []).includes(detail.key));
        }
        if (detail.kind === "station") {
            const station = (this.state.reports.stations || []).find((row) => Number(row.id) === Number(detail.key));
            const name = station?.name || detail.label;
            return operations.filter((row) => row.station === name);
        }
        if (detail.kind === "customer") {
            return transactions.filter((row) => Number(row.partner_id) === Number(detail.key));
        }
        if (detail.kind === "supply") {
            return (this.state.reports.supplies || []).filter((row) => Number(row.product_id) === Number(detail.key));
        }
        if (detail.kind === "exception") {
            return (this.state.reports.exceptions || []).filter((row) => Number(row.res_id) === Number(detail.key));
        }
        if (detail.kind === "kpi") {
            if (detail.key === "total_revenue" || detail.key === "average_ticket") return transactions;
            if (detail.key === "unique_customers") return this.state.reports.customers || [];
            if (detail.key === "finished_cars") return operations.filter((row) => row.status === "done");
            if (detail.key === "waiting_cars") return operations.filter((row) => row.report_stage === "waiting");
            return operations;
        }
        return operations;
    }

    openReportRecord(row) {
        if (!row?.model || !row?.res_id) return;
        this.playUiTone("nav");
        this.action.doAction({ type: "ir.actions.act_window", name: this.tr("Odoo Record"), res_model: row.model, res_id: Number(row.res_id), views: [[false, "form"]], target: "current" });
    }

    get reportRevenueMax() {
        return Math.max(1, ...(this.state.reports.revenue_trend || []).map((row) => Number(row.value || 0)));
    }

    reportBarStyle(value) {
        const height = Math.max(4, Math.round((Number(value || 0) / this.reportRevenueMax) * 100));
        return `height:${height}%`;
    }

    reportDonutStyle(rows, valueKey = "value") {
        const values = (rows || []).map((row) => Math.max(0, Number(row[valueKey] || 0)));
        const total = values.reduce((sum, value) => sum + value, 0);
        if (!total) return "background:conic-gradient(#e7eef7 0 100%)";
        const palette = ["#178cf4", "#22c5d6", "#20b77a", "#f4ad36", "#c257d9", "#93a9bf"];
        let cursor = 0;
        const segments = values.map((value, index) => {
            const start = cursor;
            cursor += (value / total) * 100;
            return `${palette[index % palette.length]} ${start}% ${cursor}%`;
        });
        return `background:conic-gradient(${segments.join(",")})`;
    }

    get customerRows() {
        const rows = this.state.customersData.customers || [];
        if (this.state.customerBehaviorFilter === "new_month") {
            return rows.filter((row) => Boolean(row.is_new_this_month));
        }
        if (this.state.customerBehaviorFilter === "new") {
            return rows.filter((row) => Number(row.visits || 0) <= 1);
        }
        if (this.state.customerBehaviorFilter === "returning") {
            return rows.filter((row) => Number(row.visits || 0) > 1);
        }
        if (this.state.customerBehaviorFilter === "frequent") {
            return rows.filter((row) => Number(row.visits || 0) >= 5);
        }
        return rows;
    }

    isCustomerSelected(partnerId) {
        return Number(this.state.selectedCustomerId || 0) === Number(partnerId || 0);
    }

    customerSegmentLabel(segment) {
        return {
            new: this.tr("New"),
            regular: this.tr("Regular"),
            frequent: this.tr("Frequent"),
            high_value: this.tr("High Value"),
            inactive: this.tr("Inactive"),
        }[segment] || this.tr("Regular");
    }

    customerBarStyle(value, rows) {
        const max = Math.max(1, ...(rows || []).map((row) => Number(row.value || 0)));
        return `width:${Math.max(5, Math.round((Number(value || 0) / max) * 100))}%`;
    }

    formatCustomerMoney(value) {
        const currency = this.state.customersData.currency_code || "LYD";
        try {
            return new Intl.NumberFormat(this.localeTag(), { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value || 0));
        } catch {
            return `${Number(value || 0).toFixed(2)} ${currency}`;
        }
    }

    async showCustomerDisplay() {
        this.state.page = "customer_display";
        this.state.analyticsDetail = false;
        this.state.selectedStationId = false;
        this.state.focusMode = "overview";
        this.state.searchQuery = "";
        this.playUiTone("nav");
        this.showFeedback(this.tr("Live Car Journey"));
        await this.fetchData({ silent: true });
        this.state.customerFeaturedIndex = 0;
    }

    advanceFeaturedVehicle() {
        const vehicles = this.customerFeaturedPool;
        if (!vehicles.length) {
            this.state.customerFeaturedIndex = 0;
            return;
        }
        this.state.customerFeaturedIndex = (this.state.customerFeaturedIndex + 1) % vehicles.length;
    }

    handleCustomerReadyPriority(items) {
        const ids = new Set((items || []).map((item) => Number(item.production_id || item.id || 0)).filter(Boolean));
        if (!this.customerReadyInitialized) {
            this.customerReadySeenIds = ids;
            this.customerReadyInitialized = true;
            return;
        }
        const newReadyId = [...ids].find((id) => !this.customerReadySeenIds.has(id));
        this.customerReadySeenIds = ids;
        if (!newReadyId || this.state.page !== "customer_display") return;
        const index = this.customerFeaturedPool.findIndex(
            (item) => Number(item.production_id || item.id || 0) === newReadyId
        );
        this.state.customerFeaturedIndex = index >= 0 ? index : 0;
        this.playUiTone("success");
        this.showFeedback(this.tr("Vehicle ready for pickup"), "success");
    }

    async toggleCustomerTvMode() {
        if (typeof document === "undefined") return;
        try {
            if (document.fullscreenElement) {
                await document.exitFullscreen();
                return;
            }
            const target = document.querySelector(".cw-customer-display-page");
            if (target?.requestFullscreen) {
                await target.requestFullscreen();
            }
        } catch (error) {
            console.error("Customer display fullscreen failed", error);
            this.notification.add(this.tr("Could not enter TV mode."), { type: "warning" });
        }
    }

    onCustomerFullscreenChange() {
        if (typeof document === "undefined") return;
        this.state.isCustomerTvMode = Boolean(document.fullscreenElement);
    }

    showOperations() {
        this.state.page = "operations";
        this.state.analyticsDetail = false;
        this.state.focusMode = "overview";
        this.state.selectedStationId = false;
        this.playUiTone("nav");
        this.showFeedback(this.tr("Car Wash Dashboard"));
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
            title: label || this.tr("Analytics Detail"),
            subtitle: this.tr("Loading relevant information…"),
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
                title: result.title || label || this.tr("Analytics Detail"),
                subtitle: result.subtitle || "",
                summary: result.summary || [],
                rows: result.rows || [],
            };
            this.showFeedback(this.state.analyticsDetail.title);
        } catch (error) {
            console.error("Car wash analytics drill-down failed", error);
            this.state.analyticsDetail = false;
            this.notification.add(this.tr("Could not load analytics detail."), { type: "danger" });
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
            "pos.order": this.tr("POS Order"),
            "mrp.production": this.tr("Car Wash Order"),
            "mrp.workorder": this.tr("Wash Operation"),
            "res.partner": this.tr("Customer"),
            "product.product": this.tr("Product"),
        };
        this.action.doAction({
            type: "ir.actions.act_window",
            name: names[row.model] || this.tr("Odoo Record"),
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

    formatReportMoney(value) {
        const number = Number(value || 0);
        const code = this.state.reports.currency_code || this.state.analytics.currency_code || "LYD";
        try {
            return new Intl.NumberFormat(this.localeTag(), { style: "currency", currency: code, maximumFractionDigits: 2 }).format(number);
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

    get customerDisplayWaitingVehicles() {
        return (this.state.data.queue || []).map((item, index) => ({
            ...item,
            customer_stage: "waiting",
            customer_queue_index: index,
            progress_percent: 0,
        }));
    }

    get customerDisplayWashingVehicles() {
        return (this.state.data.stations || [])
            .filter((station) => station.current_car && station.visual_status !== "finishing")
            .map((station) => ({
                ...station.current_car,
                customer_stage: "washing",
                station_name: station.name,
                elapsed_minutes: station.elapsed_minutes ?? station.current_car.elapsed_minutes,
                expected_minutes: station.expected_minutes ?? station.current_car.expected_minutes,
                progress_percent: station.progress_percent ?? station.current_car.progress_percent,
            }));
    }

    get customerDisplayFinishingVehicles() {
        return (this.state.data.stations || [])
            .filter((station) => station.current_car && station.visual_status === "finishing")
            .map((station) => ({
                ...station.current_car,
                customer_stage: "finishing",
                station_name: station.name,
                elapsed_minutes: station.elapsed_minutes ?? station.current_car.elapsed_minutes,
                expected_minutes: station.expected_minutes ?? station.current_car.expected_minutes,
                progress_percent: station.progress_percent ?? station.current_car.progress_percent,
            }));
    }

    get customerDisplayReadyVehicles() {
        return (this.state.data.finished_today_items || []).map((item) => ({
            ...item,
            customer_stage: "ready",
            progress_percent: 100,
        }));
    }

    get customerFeaturedPool() {
        return [
            ...this.customerDisplayReadyVehicles,
            ...this.customerDisplayFinishingVehicles,
            ...this.customerDisplayWashingVehicles,
            ...this.customerDisplayWaitingVehicles,
        ];
    }

    get customerFeaturedVehicle() {
        const vehicles = this.customerFeaturedPool;
        if (!vehicles.length) return false;
        const index = this.state.customerFeaturedIndex % vehicles.length;
        return vehicles[index] || vehicles[0];
    }

    customerStageLabel(stage) {
        return {
            waiting: this.tr("Waiting"),
            washing: this.tr("Washing"),
            finishing: this.tr("Drying / Finishing"),
            ready: this.tr("Ready for Pickup"),
        }[stage] || this.tr("Waiting");
    }

    customerStageIcon(stage) {
        return {
            waiting: "fa fa-clock-o",
            washing: "fa fa-tint",
            finishing: "fa fa-sun-o",
            ready: "fa fa-check",
        }[stage] || "fa fa-car";
    }

    customerStageIndex(stage) {
        return { waiting: 0, washing: 1, finishing: 2, ready: 3 }[stage] ?? 0;
    }

    customerJourneyStepClass(vehicle, stepIndex) {
        const current = this.customerStageIndex(vehicle?.customer_stage);
        if (stepIndex < current) return "is-done";
        if (stepIndex === current) return "is-active";
        return "is-upcoming";
    }

    customerTicketLabel(item) {
        const raw = Number(item?.production_id || item?.id || 0);
        return raw ? `#${String(raw).padStart(3, "0")}` : "—";
    }

    customerEtaLabel(item) {
        if (!item) return "—";
        if (item.customer_stage === "ready") return this.tr("Ready now");
        if (item.customer_stage === "waiting") {
            if (item.customer_queue_index === 0) return this.tr("Up Next");
            return item.waiting_minutes !== false && item.waiting_minutes !== undefined
                ? `${this.tr("Waiting")} ${this.formatMinutes(item.waiting_minutes)}`
                : this.tr("Waiting");
        }
        const expected = Number(item.expected_minutes);
        const elapsed = Number(item.elapsed_minutes);
        if (Number.isFinite(expected) && expected > 0 && Number.isFinite(elapsed)) {
            const remaining = Math.max(0, Math.round(expected - elapsed));
            return remaining > 0
                ? `${this.tr("Est. remaining")}: ${this.formatMinutes(remaining)}`
                : this.tr("Finishing now");
        }
        return this.tr("In progress");
    }

    customerProgressPercent(item) {
        if (!item) return 0;
        if (item.customer_stage === "ready") return 100;
        if (item.customer_stage === "waiting") return 0;
        const value = Number(item.progress_percent || 0);
        return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
    }

    customerProgressStyle(item) {
        return `width:${this.customerProgressPercent(item)}%`;
    }

    get customerDisplayTotalVehicles() {
        return this.customerDisplayWaitingVehicles.length
            + this.customerDisplayWashingVehicles.length
            + this.customerDisplayFinishingVehicles.length
            + this.customerDisplayReadyVehicles.length;
    }

    get selectedStation() {
        return (
            this.state.data.stations.find(
                (station) => station.id && station.id === this.state.selectedStationId
            ) || false
        );
    }

    carStage(row) {
        const stage = String(row?.report_stage || row?.status || "");
        if (stage === "done" || stage === "finished") return "finished";
        if (stage === "cancel" || stage === "cancelled") return "cancelled";
        if (stage === "progress") return "in_progress";
        return stage || "unknown";
    }

    get carRows() {
        const query = this.state.searchQuery.trim().toLowerCase();
        const status = this.state.carsStatusFilter || "all";
        return (this.state.carsData.operations || []).filter((row) => {
            if (status !== "all" && this.carStage(row) !== status) return false;
            if (!query) return true;
            return [row.plate, row.vehicle, row.customer, row.service, row.station, row.ticket, row.status_label]
                .some((value) => String(value || "").toLowerCase().includes(query));
        });
    }

    get carStatusCounts() {
        const rows = this.state.carsData.operations || [];
        const counts = { all: rows.length, waiting: 0, in_progress: 0, finished: 0, cancelled: 0 };
        rows.forEach((row) => {
            const key = this.carStage(row);
            if (key in counts) counts[key] += 1;
        });
        return counts;
    }

    get serviceRows() {
        const query = this.state.searchQuery.trim().toLowerCase();
        const rows = this.state.servicesData.services || [];
        if (!query) return rows;
        return rows.filter((row) => String(row.name || "").toLowerCase().includes(query));
    }

    get servicesSoldCount() {
        return (this.state.servicesData.services || []).reduce((sum, row) => sum + Number(row.value || 0), 0);
    }

    get topService() {
        return (this.state.servicesData.services || [])[0] || false;
    }

    formatServicesMoney(value) {
        const amount = Number(value || 0);
        const symbol = this.state.servicesData.currency_symbol || this.state.servicesData.currency_code || "";
        return `${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${symbol}`.trim();
    }

    serviceShareStyle(row) {
        const width = Math.max(0, Math.min(100, Number(row?.sales_percent || 0)));
        return `width:${width}%`;
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

    get realStationCount() {
        return Number(
            this.state.data.station_configuration?.real_station_count
            ?? this.state.data.stations?.length
            ?? 0
        );
    }

    get workCentersTitle() {
        return `${this.tr("Work Centers")} (${this.realStationCount})`;
    }

    get stationCapacityLabel() {
        return this.tr("of %s stations", this.realStationCount);
    }

    get stationGridClass() {
        const count = this.filteredStations.length;
        const bucket = count >= 1 && count <= 6 ? String(count) : "many";
        const listClass = this.state.viewMode === "list" ? " is-list" : "";
        return `cw-station-grid station-count-${bucket}${listClass}`;
    }

    get finishedTodayItems() {
        const query = this.state.searchQuery.trim().toLowerCase();
        const items = this.state.data.finished_today_items || [];
        if (!query) return items;
        return items.filter((item) => this.matchesQuery(item, query));
    }

    get focusTitle() {
        return {
            active: this.tr("Cars In Stations"),
            waiting: this.tr("General Waiting Queue"),
            available: this.tr("Available Stations"),
            finished: this.tr("Finished Today"),
            stations: this.tr("Station Details"),
        }[this.state.focusMode] || this.tr("Dashboard Overview");
    }

    get focusSubtitle() {
        return {
            active: this.tr("Only cars currently running inside a wash station."),
            waiting: this.tr("Only cars waiting for the next available station."),
            available: this.tr("Only stations ready to receive the next car."),
            finished: this.tr("Only wash orders completed today."),
            stations: this.tr("Live status and current car for every wash station."),
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
        return value === "large" ? this.tr("Large") : value === "small" ? this.tr("Small") : "—";
    }

    stationTypeLabel(value) {
        return {
            automatic: this.tr("Automatic"),
            polishing: this.tr("Polishing"),
            general: this.tr("General"),
        }[value] || this.tr("General");
    }

    stationStatusLabel(value) {
        return {
            available: this.tr("Available"),
            busy: this.tr("Busy"),
            finishing: this.tr("Finishing"),
            conflict: this.tr("Check Station"),
            not_configured: this.tr("Not Configured"),
        }[value] || this.tr("Available");
    }

    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} ${this.tr("min")}`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}${this.tr("h")} ${rest}${this.tr("m")}` : `${hours}${this.tr("h")}`;
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
        this.showFeedback(this.tr("Dashboard overview"));
    }

    showStationDirectory() {
        this.state.page = "operations";
        this.activateFocus("stations");
    }

    toggleViewMode() {
        this.state.viewMode = this.state.viewMode === "grid" ? "list" : "grid";
        this.playUiTone("tap");
        this.showFeedback(
            this.state.viewMode === "grid" ? this.tr("Grid view") : this.tr("List view")
        );
    }

    toggleAudio() {
        this.state.audioEnabled = !this.state.audioEnabled;
        if (this.state.audioEnabled) {
            this.playUiTone("success");
        }
        this.showFeedback(
            this.state.audioEnabled ? this.tr("Sound feedback on") : this.tr("Sound feedback off")
        );
    }

    showLiveStatus() {
        this.playUiTone("tap");
        this.showFeedback(this.tr("Live station updates are connected."), "success");
    }

    selectStation(id) {
        if (!id) return;
        this.state.focusMode = "overview";
        this.state.selectedStationId = id;
        this.playUiTone("nav");
        const station = this.state.data.stations.find((item) => item.id === id);
        this.showFeedback(
            station ? `${this.tr("Station details")}: ${station.name}` : this.tr("Station details")
        );
    }

    closeStation() {
        this.state.selectedStationId = false;
        this.playUiTone("close");
    }

    async manualRefresh() {
        if (this.state.page === "analytics") {
            await this.fetchAnalytics();
        } else if (this.state.page === "reports") {
            await this.fetchReports();
        } else if (this.state.page === "customers") {
            await this.fetchCustomers();
        } else if (this.state.page === "cars") {
            await this.fetchCars();
        } else if (this.state.page === "services") {
            await this.fetchServices();
        } else {
            await this.fetchData();
        }
        this.playUiTone("success");
        this.showFeedback(this.tr("Dashboard updated."), "success");
    }

    openQueue() {
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.tr("Waiting Queue"),
            res_model: "mrp.production",
            views: [[false, "list"], [false, "form"]],
            domain: this.state.data.queue_domain || [],
            target: "current",
        });
    }

    async fetchCars({ silent = false } = {}) {
        this.state.carsLoading = true;
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_report_center_data",
                [{ period: this.state.carsPeriod }]
            );
            this.state.carsData = {
                ...this.state.carsData,
                period_label: result.period_label || "",
                kpis: result.kpis || this.state.carsData.kpis,
                operations: result.operations || [],
            };
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (error) {
            console.error("Car center fetch failed", error);
            if (!silent) this.notification.add(this.tr("Could not load car activity."), { type: "danger" });
        } finally {
            this.state.carsLoading = false;
        }
    }

    async openCars() {
        this.state.page = "cars";
        this.state.searchQuery = "";
        this.state.selectedStationId = false;
        this.state.focusMode = "overview";
        this.state.analyticsDetail = false;
        this.state.reportDetail = false;
        this.playUiTone("nav");
        this.showFeedback(this.tr("Cars & Wash Orders"));
        await this.fetchCars();
    }

    async setCarsPeriod(period) {
        const normalized = period === "month" ? "month" : "today";
        if (this.state.carsPeriod === normalized && this.state.carsData.operations.length) return;
        this.state.carsPeriod = normalized;
        this.state.carsStatusFilter = "all";
        await this.fetchCars();
        this.playUiTone("tap");
    }

    setCarsStatusFilter(status) {
        const allowed = ["all", "waiting", "in_progress", "finished", "cancelled"];
        this.state.carsStatusFilter = allowed.includes(status) ? status : "all";
        this.playUiTone("tap");
    }

    openCarRecord(row) {
        this.openReportRecord(row);
    }

    openCarOrders() {
        this.playUiTone("nav");
        const domain = this.state.data.wash_order_domain || [["company_id", "=", this.state.data.company_id]];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.tr("Car Wash Orders"),
            res_model: "mrp.production",
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }

    async fetchServices({ silent = false } = {}) {
        this.state.servicesLoading = true;
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_report_center_data",
                [{ period: this.state.servicesPeriod }]
            );
            this.state.servicesData = {
                ...this.state.servicesData,
                period_label: result.period_label || "",
                currency_code: result.currency_code || this.state.servicesData.currency_code,
                currency_symbol: result.currency_symbol || this.state.servicesData.currency_symbol,
                kpis: result.kpis || this.state.servicesData.kpis,
                services: result.services || [],
                filter_options: result.filter_options || this.state.servicesData.filter_options,
            };
            this.state.lastUpdate = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        } catch (error) {
            console.error("Services center fetch failed", error);
            if (!silent) this.notification.add(this.tr("Could not load service performance."), { type: "danger" });
        } finally {
            this.state.servicesLoading = false;
        }
    }

    async openServices() {
        this.state.page = "services";
        this.state.searchQuery = "";
        this.state.selectedStationId = false;
        this.state.focusMode = "overview";
        this.state.analyticsDetail = false;
        this.state.reportDetail = false;
        this.playUiTone("nav");
        this.showFeedback(this.tr("Wash Services"));
        await this.fetchServices();
    }

    async setServicesPeriod(period) {
        const normalized = period === "month" ? "month" : "today";
        if (this.state.servicesPeriod === normalized && this.state.servicesData.services.length) return;
        this.state.servicesPeriod = normalized;
        await this.fetchServices();
        this.playUiTone("tap");
    }

    openServiceRecord(row) {
        this.openReportRecord(row);
    }

    manageServices() {
        const ids = (this.state.servicesData.filter_options?.services || [])
            .map((item) => Number(item.id || 0))
            .filter(Boolean);
        const domain = ids.length ? [["id", "in", ids]] : [["sale_ok", "=", true], ["type", "=", "service"]];
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.tr("Manage Wash Services"),
            res_model: "product.product",
            views: [[false, "list"], [false, "form"]],
            domain,
            target: "current",
        });
    }

    async fetchCustomers({ silent = false } = {}) {
        this.state.customersLoading = true;
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_customer_intelligence_data",
                [this.state.customerFilters]
            );
            this.state.customersData = {
                ...this.state.customersData,
                ...result,
                kpis: result.kpis || this.state.customersData.kpis,
                customers: result.customers || [],
                top_by_revenue: result.top_by_revenue || [],
                most_frequent: result.most_frequent || [],
                new_vs_returning: result.new_vs_returning || [],
                service_preferences: result.service_preferences || [],
                filter_options: result.filter_options || this.state.customersData.filter_options,
            };
            this.state.customersLoaded = true;
            if (this.state.selectedCustomerId && !this.state.customersData.customers.some((row) => Number(row.partner_id) === Number(this.state.selectedCustomerId))) {
                this.state.selectedCustomerId = false;
                this.state.customerDetail = false;
            }
        } catch (error) {
            console.error("Customer intelligence fetch failed", error);
            if (!silent) this.notification.add(this.tr("Could not load customer intelligence."), { type: "danger" });
        } finally {
            this.state.customersLoading = false;
        }
    }

    async openCustomers() {
        this.state.page = "customers";
        this.state.analyticsDetail = false;
        this.state.reportDetail = false;
        this.state.selectedStationId = false;
        this.state.focusMode = "overview";
        this.state.customerBehaviorFilter = "";
        this.playUiTone("nav");
        this.showFeedback(this.tr("Customer Intelligence"));
        await this.fetchCustomers();
    }

    onCustomerFilterChange(field, event) {
        if (!(field in this.state.customerFilters)) return;
        this.state.customerFilters[field] = event?.target?.value ?? "";
    }

    async applyCustomerSegment(segment) {
        this.state.customerFilters.segment = this.state.customerFilters.segment === segment ? "" : segment;
        this.state.customerBehaviorFilter = "";
        this.state.selectedCustomerId = false;
        this.state.customerDetail = false;
        await this.fetchCustomers();
        this.playUiTone("tap");
    }

    async applyCustomerService(productId) {
        const value = Number(productId || 0);
        this.state.customerFilters.service_id = Number(this.state.customerFilters.service_id || 0) === value ? "" : String(value || "");
        this.state.customerBehaviorFilter = "";
        this.state.selectedCustomerId = false;
        this.state.customerDetail = false;
        await this.fetchCustomers();
        this.playUiTone("tap");
    }

    applyCustomerBehavior(key) {
        this.state.customerBehaviorFilter = this.state.customerBehaviorFilter === key ? "" : key;
        this.state.selectedCustomerId = false;
        this.state.customerDetail = false;
        this.playUiTone("tap");
    }

    async resetCustomerFilters() {
        this.state.customerFilters = { search: "", segment: "", service_id: "", activity_period: "all" };
        this.state.customerBehaviorFilter = "";
        this.state.selectedCustomerId = false;
        this.state.customerDetail = false;
        await this.fetchCustomers();
        this.showFeedback(this.tr("Customer filters reset."));
    }

    async selectCustomer(partnerId) {
        if (!partnerId) return;
        this.state.selectedCustomerId = Number(partnerId);
        this.state.customerDetailLoading = true;
        try {
            const result = await this.orm.call(
                "mrp.production",
                "get_customer_intelligence_detail",
                [Number(partnerId)]
            );
            this.state.customerDetail = result || false;
            this.playUiTone("nav");
        } catch (error) {
            console.error("Customer 360 detail fetch failed", error);
            this.notification.add(this.tr("Could not load customer details."), { type: "danger" });
        } finally {
            this.state.customerDetailLoading = false;
        }
    }

    closeCustomerDetail() {
        this.state.selectedCustomerId = false;
        this.state.customerDetail = false;
        this.playUiTone("close");
    }

    openCustomerRecord() {
        const row = this.state.customerDetail;
        if (!row?.partner_id) return;
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.tr("Customer"),
            res_model: "res.partner",
            res_id: Number(row.partner_id),
            views: [[false, "form"]],
            target: "current",
        });
    }

    openProduction(id) {
        if (!id) return;
        this.playUiTone("nav");
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.tr("Car Wash Order"),
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
            name: this.tr("Wash Operation"),
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
