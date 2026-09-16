/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";

const ACTION_TAG = "crystal_clean_station_dashboard.client_action";

export class CrystalCleanLightDashboard extends Component {
    static template = "crystal_clean_station_dashboard.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            error: "",
            refreshing: false,
            generatedAt: null,
            companyName: "كريستال كلين",
            userName: "",
            userInitial: "CC",
            source: "",
            stations: [],
            queue: { total: 0, rows: [] },
            cars: [],
            filters: {
                search: "",
                status: "all",
                service: "all",
                worker: "all",
            },
            now: new Date(),
        });

        this._refreshTimer = null;
        this._clockTimer = null;

        onWillStart(async () => {
            await this.loadDashboard();
        });

        onMounted(() => {
            this._clockTimer = window.setInterval(() => {
                this.state.now = new Date();
            }, 30000);

            this._refreshTimer = window.setInterval(() => {
                if (!document.hidden) {
                    this.loadDashboard({ silent: true });
                }
            }, 30000);

            this._visibilityHandler = () => {
                if (!document.hidden) {
                    this.loadDashboard({ silent: true });
                }
            };
            document.addEventListener("visibilitychange", this._visibilityHandler);
        });

        onWillUnmount(() => {
            if (this._clockTimer) {
                window.clearInterval(this._clockTimer);
            }
            if (this._refreshTimer) {
                window.clearInterval(this._refreshTimer);
            }
            if (this._visibilityHandler) {
                document.removeEventListener("visibilitychange", this._visibilityHandler);
            }
        });
    }

    async loadDashboard({ silent = false } = {}) {
        if (!silent) {
            this.state.loading = true;
        }
        this.state.refreshing = true;
        this.state.error = "";

        try {
            let payload = null;
            let source = "";

            // V15+ contract: preferred source for the operations screen.
            try {
                payload = await this.orm.call("mrp.production", "get_operations_data", [], {});
                if (payload && payload.stations) {
                    source = "operations";
                }
            } catch {
                payload = null;
            }

            // Backward-compatible source used by the existing V13 dashboard.
            if (!payload) {
                payload = await this.orm.call("mrp.production", "get_dashboard_data", [], {});
                source = "legacy";
            }

            this.applyPayload(payload || {}, source);
        } catch (error) {
            console.error("Crystal Clean dashboard load error:", error);
            this.state.error = _t("تعذر تحميل بيانات المحطات. أعد المحاولة.");
            if (!silent) {
                this.notification.add(this.state.error, {
                    type: "danger",
                    title: _t("لوحة كريستال كلين"),
                });
            }
        } finally {
            this.state.loading = false;
            this.state.refreshing = false;
        }
    }

    applyPayload(payload, source) {
        this.state.source = source;
        this.state.companyName = payload.company_name || payload.companyName || "كريستال كلين";
        this.state.userName =
            payload.current_user_name ||
            payload.user_name ||
            payload.user?.name ||
            "";
        this.state.userInitial =
            payload.current_user_initial ||
            this.initials(this.state.userName) ||
            "CC";
        this.state.generatedAt = payload.generated_at || payload.today_start || null;

        const cars = Array.isArray(payload.cars)
            ? payload.cars
            : Array.isArray(payload.active_cars)
              ? payload.active_cars
              : [];

        const queue = payload.queue && typeof payload.queue === "object"
            ? payload.queue
            : {
                  total: Number(payload.waiting || 0),
                  rows: [],
              };

        const rawStations = Array.isArray(payload.stations)
            ? payload.stations
            : Array.isArray(payload.workcenter_load)
              ? payload.workcenter_load
              : [];

        this.state.cars = cars;
        this.state.queue = {
            total: Number(queue.total || 0),
            rows: Array.isArray(queue.rows) ? queue.rows : [],
        };

        this.state.stations = rawStations
            .map((station, index) => this.normalizeStation(station, index, cars))
            .sort((a, b) => {
                const ao = Number(a.displayOrder || 0);
                const bo = Number(b.displayOrder || 0);
                if (ao !== bo) {
                    return ao - bo;
                }
                return String(a.code).localeCompare(String(b.code), undefined, { numeric: true });
            });
    }

    normalizeStation(station, index, cars) {
        const code =
            station.station_code ||
            this.extractStationCode(station.name) ||
            station.code ||
            `S${index + 1}`;

        const runtimeState =
            station.runtime_state ||
            this.legacyRuntimeState(station);

        const localCars = Array.isArray(station.cars) ? station.cars : [];
        const matchedCars = cars.filter((car) => this.carBelongsToStation(car, station));
        const currentCar = localCars[0] || matchedCars[0] || null;

        const service =
            currentCar?.service_name ||
            currentCar?.service ||
            station.service_name ||
            station.operation_name ||
            this.kindLabel(station.kind || station.cc_station_kind);

        const worker =
            station.worker_name ||
            station.employee_name ||
            station.assigned_employee_name ||
            currentCar?.worker_name ||
            currentCar?.employee_name ||
            "";

        const progressValue = Number(currentCar?.progress);
        const hasProgress = Number.isFinite(progressValue);
        const progress = hasProgress
            ? Math.max(0, Math.min(100, progressValue))
            : null;

        const eta = this.getEta(currentCar, station);

        return {
            id: station.id,
            code,
            name: station.name || code,
            displayOrder:
                station.display_order ??
                station.cc_station_order ??
                station.sequence ??
                index + 1,
            kind: station.kind || station.cc_station_kind || "general",
            runtimeState,
            statusLabel: this.statusLabel(runtimeState),
            statusClass: this.statusClass(runtimeState),
            service,
            worker,
            load: Number(station.load || 0),
            occupancy: Number(station.occupancy ?? station.in_progress ?? 0),
            queueCount: Number(station.queue_count ?? station.queue ?? 0),
            capacity: Number(station.capacity || 1),
            car: currentCar,
            plate:
                currentCar?.plate ||
                currentCar?.vehicle_plate ||
                currentCar?.license_plate ||
                "",
            vehicleModel:
                currentCar?.vehicle_model ||
                currentCar?.model ||
                "",
            eta,
            progress,
            hasProgress,
            isAvailable: runtimeState === "available",
            isMaintenance: runtimeState === "maintenance",
            isClosed: runtimeState === "closed",
        };
    }

    legacyRuntimeState(station) {
        if (station.manual_state === "maintenance") {
            return "maintenance";
        }
        if (station.manual_state === "closed") {
            return "closed";
        }
        const inProgress = Number(station.in_progress || station.occupancy || 0);
        const queue = Number(station.queue || station.queue_count || 0);
        const capacity = Number(station.capacity || 1);

        if (inProgress > capacity) {
            return "overloaded";
        }
        if (inProgress > 0) {
            return "busy";
        }
        if (queue > 0) {
            return "queued";
        }
        return "available";
    }

    carBelongsToStation(car, station) {
        const candidateIds = [
            car.station_id,
            car.workcenter_id,
            car.current_workcenter_id,
            car.current_station_id,
        ]
            .map((value) => {
                if (Array.isArray(value)) {
                    return value[0];
                }
                if (value && typeof value === "object") {
                    return value.id;
                }
                return value;
            })
            .filter((value) => value !== undefined && value !== null);

        if (candidateIds.some((value) => Number(value) === Number(station.id))) {
            return true;
        }

        const stationName =
            car.workcenter_name ||
            car.station_name ||
            car.station ||
            "";
        return Boolean(stationName && station.name && stationName === station.name);
    }

    getEta(car, station) {
        if (!car) {
            return "";
        }

        if (
            car.eta_reliable === false ||
            car.show_eta === false ||
            station.eta_reliable === false ||
            station.show_eta === false
        ) {
            return _t("قيد التقدير");
        }

        const candidates = [
            car.remaining_minutes,
            car.eta_minutes,
            car.expected_remaining_minutes,
            station.remaining_minutes,
            station.eta_minutes,
        ];

        const value = candidates.find(
            (item) => item !== undefined && item !== null && Number.isFinite(Number(item))
        );

        if (value === undefined) {
            return _t("قيد التقدير");
        }

        const minutes = Math.max(0, Math.round(Number(value)));
        if (minutes === 0) {
            return _t("الآن");
        }
        return `${minutes} ${_t("دقيقة")}`;
    }

    extractStationCode(name) {
        const match = String(name || "").match(/\bA\s*([0-9]{1,2})\b/i);
        return match ? `A${match[1]}` : "";
    }

    initials(name) {
        const parts = String(name || "")
            .trim()
            .split(/\s+/)
            .filter(Boolean);
        if (!parts.length) {
            return "";
        }
        return parts
            .slice(0, 2)
            .map((part) => part[0])
            .join("")
            .toUpperCase();
    }

    kindLabel(kind) {
        const labels = {
            general: _t("محطة خدمة"),
            auto: _t("غسيل آلي"),
            polish: _t("تلميع وحماية"),
        };
        return labels[kind] || _t("محطة خدمة");
    }

    statusLabel(state) {
        const labels = {
            available: _t("جاهزة"),
            queued: _t("في الانتظار"),
            busy: _t("مشغولة"),
            overloaded: _t("مزدحمة"),
            maintenance: _t("قيد الصيانة"),
            closed: _t("مغلقة"),
        };
        return labels[state] || _t("غير معروف");
    }

    statusClass(state) {
        const classes = {
            available: "ready",
            queued: "queued",
            busy: "busy",
            overloaded: "overloaded",
            maintenance: "maintenance",
            closed: "closed",
        };
        return classes[state] || "closed";
    }

    get filteredStations() {
        const search = this.state.filters.search.trim().toLowerCase();
        const status = this.state.filters.status;
        const service = this.state.filters.service;
        const worker = this.state.filters.worker;

        return this.state.stations.filter((station) => {
            const haystack = [
                station.code,
                station.name,
                station.service,
                station.worker,
                station.plate,
                station.vehicleModel,
            ]
                .join(" ")
                .toLowerCase();

            const matchesSearch = !search || haystack.includes(search);
            const matchesStatus = status === "all" || station.runtimeState === status;
            const matchesService = service === "all" || station.kind === service;
            const matchesWorker = worker === "all" || station.worker === worker;

            return matchesSearch && matchesStatus && matchesService && matchesWorker;
        });
    }

    get workerOptions() {
        return [...new Set(this.state.stations.map((s) => s.worker).filter(Boolean))]
            .sort()
            .map((name) => ({ value: name, label: name }));
    }

    get totalStations() {
        return this.state.stations.length;
    }

    get readyCount() {
        return this.state.stations.filter((s) => s.runtimeState === "available").length;
    }

    get busyCount() {
        return this.state.stations.filter((s) =>
            ["busy", "queued", "overloaded"].includes(s.runtimeState)
        ).length;
    }

    get maintenanceCount() {
        return this.state.stations.filter((s) => s.runtimeState === "maintenance").length;
    }

    get gridClass() {
        const count = this.filteredStations.length;
        if (count >= 9) {
            return "cc-grid-5";
        }
        if (count >= 7) {
            return "cc-grid-4";
        }
        if (count >= 5) {
            return "cc-grid-3";
        }
        return "cc-grid-2";
    }

    get formattedDate() {
        return new Intl.DateTimeFormat("ar-LY-u-nu-latn", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        }).format(this.state.now);
    }

    get formattedTime() {
        return new Intl.DateTimeFormat("ar-LY-u-nu-latn", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: true,
        }).format(this.state.now);
    }

    onSearchInput(ev) {
        this.state.filters.search = ev.target.value || "";
    }

    onStatusChange(ev) {
        this.state.filters.status = ev.target.value;
    }

    onServiceChange(ev) {
        this.state.filters.service = ev.target.value;
    }

    onWorkerChange(ev) {
        this.state.filters.worker = ev.target.value;
    }

    resetFilters() {
        this.state.filters.search = "";
        this.state.filters.status = "all";
        this.state.filters.service = "all";
        this.state.filters.worker = "all";
    }

    async refreshNow() {
        await this.loadDashboard();
    }

    logout() {
        window.location.assign("/web/session/logout");
    }
}

registry.category("actions").add(ACTION_TAG, CrystalCleanLightDashboard);
