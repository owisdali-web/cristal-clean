/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const REFRESH_TYPE = "crystal_clean_dashboard_refresh";
const SAFETY_REFRESH_MS = 60_000;
const DEBOUNCE_MS = 400;

function demoRequested() {
    return new URLSearchParams(window.location.search).get("cc_demo") === "1";
}

function demoCars() {
    const models = ["Toyota Camry", "Hyundai Tucson", "Kia Sportage", "Nissan Sunny", "Mercedes C200", "Toyota Hilux", "Kia Picanto", "Toyota Prado"];
    const colors = [_t("أبيض"), _t("أسود"), _t("فضي"), _t("رمادي"), _t("أحمر"), _t("أزرق")];
    return Array.from({ length: 16 }, (_, i) => ({
        id: 800 + i,
        production_id: 800 + i,
        plate: `${(i % 9) + 1}-${123456 + i * 731}`,
        vehicle_model: models[i % models.length],
        vehicle_color: colors[i % colors.length],
        service_name: i % 3 ? _t("غسيل متكامل") : _t("تنظيف خارجي"),
        status_code: i < 7 ? "in_progress" : i < 13 ? "waiting" : "ready_delivery",
        current_stage: i % 2 ? _t("غسيل خارجي") : _t("تلميع ولمعة"),
        progress: Math.min(96, 18 + i * 6),
        remaining_minutes: 4 + (i % 8) * 3,
    }));
}

function demoStations(cars) {
    const states = ["busy", "busy", "queued", "available", "busy", "maintenance", "available", "queued", "overloaded", "closed", "busy", "available"];
    return Array.from({ length: 12 }, (_, i) => {
        const capacity = i === 8 ? 1 : 2;
        const occupancy = states[i] === "overloaded" ? 2 : states[i] === "busy" ? 1 : 0;
        const queue = states[i] === "queued" ? 2 : i === 8 ? 3 : 0;
        const stationCars = cars.slice(i % 8, (i % 8) + Math.max(occupancy, queue ? 1 : 0));
        return {
            id: i + 1,
            name: `محطة A${i + 1}`,
            station_code: `A${i + 1}`,
            display_order: (i + 1) * 10,
            kind: i === 8 ? "auto" : i === 9 ? "polish" : "general",
            runtime_state: states[i],
            capacity,
            occupancy,
            queue_count: queue,
            over_capacity: states[i] === "overloaded",
            occupancy_rate: Math.round((occupancy / capacity) * 100),
            done_today: 3 + (i % 7),
            cars: stationCars,
        };
    });
}

function demoOpsBundle(isManager) {
    const cars = demoCars();
    const stations = demoStations(cars);
    const queueRows = cars.slice(7, 13).map((car, i) => ({
        workorder_id: 1200 + i,
        station_id: stations[(i + 2) % stations.length].id,
        station_code: stations[(i + 2) % stations.length].station_code,
        station_position: i + 1,
        queue_age_minutes: 5 + i * 4,
        expected_minutes: 18 + i * 2,
        estimated_start_in_minutes: i === 4 ? false : 6 + i * 7,
        eta_reliable: i !== 4,
        vehicle: car,
    }));
    const intelligenceStations = stations.map((s, i) => ({
        station_id: s.id,
        station_code: s.station_code,
        station_name: s.name,
        runtime_state: s.runtime_state,
        capacity: s.capacity,
        occupancy: s.occupancy,
        queue_count: s.queue_count,
        over_capacity: s.over_capacity,
        projection_reliable: i !== 8,
        projected_clear_minutes: i === 8 ? false : 12 + i * 3,
        done_today: s.done_today,
        done_last_60_minutes: i % 4,
        avg_duration_today_minutes: 21 + (i % 5),
        avg_expected_today_minutes: 24,
        delayed_running_jobs: i % 5 === 0 ? 1 : 0,
        queue_age_max_minutes: 7 + i * 2,
    }));
    return {
        demo: true,
        topology: { company_id: 1, company_name: _t("كريستال كلين"), stations },
        operations: {
            company_id: 1,
            company_name: _t("كريستال كلين"),
            currency_symbol: "د.ل",
            kpis: { active_vehicles: 16, in_service: 7, waiting_for_station: 6, ready_for_delivery: 3, station_total: 12, station_available: 3, station_busy: 5, station_maintenance: 1, station_closed: 1, station_overloaded: 1 },
            stations,
            queue: { total: queueRows.length, rows: queueRows, by_station: [] },
            cars,
            ready_delivery: cars.slice(13),
            waiting_cars: cars.slice(7, 13),
            diagnostics: { overloaded_station_ids: [9] },
        },
        queue: { queue: { total: queueRows.length, rows: queueRows, by_station: [] } },
        intelligence: {
            company_id: 1,
            company_name: _t("كريستال كلين"),
            kpis: { active_workorders: 13, running_jobs: 7, queued_jobs: 6, delayed_running_jobs: 2, completed_today: 41, completed_last_60_minutes: 4, avg_completed_duration_today_minutes: 23.8, max_queue_age_minutes: 29, projected_system_clear_minutes: 47, projection_reliable_for_all_stations: false },
            stations: intelligenceStations,
            diagnostics: { unreliable_projection_station_ids: [9], overloaded_station_ids: [9] },
        },
        management: isManager ? {
            currency_symbol: "د.ل",
            commercial: { pos_sales_today: 3860, orders_today: 48, avg_ticket_today: 80.42, customers_served_today: 44 },
            financial: { collected_today: 3520, posted_expenses_today: 640, operational_balance_today: 3220 },
            operations: { active_vehicles: 16, running_jobs: 7, queued_jobs: 6, ready_for_pickup: 3, completed_today: 41, avg_completed_duration_today_minutes: 23.8, delayed_running_jobs: 2, station_live_occupancy_pct: 58.3, overloaded_stations: 1 },
        } : null,
        materials: null,
        customers: null,
        team: isManager ? { kpis: { operational_users: 9, worked_today: 8, currently_checked_in: 6, current_presence_pct: 66.7, worked_today_pct: 88.9 } } : null,
    };
}

function demoDisplay() {
    const cars = demoCars().slice(0, 9).map((car, i) => ({
        display_key: `demo-${i + 1}`,
        public_reference: car.plate,
        vehicle_model: car.vehicle_model,
        vehicle_color: car.vehicle_color,
        service_name: car.service_name,
        display_state: i < 6 ? "in_service" : "waiting",
        display_label: i < 6 ? _t("قيد الخدمة") : _t("في الانتظار"),
        progress_percent: i < 6 ? 25 + i * 12 : 0,
        current_stage: i % 2 ? _t("التجفيف") : "الغسيل الخارجي",
        station_code: `A${(i % 8) + 1}`,
        eta_minutes: i === 7 ? false : 4 + i * 3,
        eta_reliable: i !== 7,
        eta_scope: "current_stage",
        queue_position: i < 6 ? 0 : i - 5,
    }));
    const ready = demoCars().slice(13, 16).map((car, i) => ({
        display_key: `ready-${i}`,
        public_reference: car.plate,
        vehicle_model: car.vehicle_model,
        vehicle_color: car.vehicle_color,
        service_name: car.service_name,
        display_state: "ready_for_pickup",
        display_label: _t("جاهزة للاستلام"),
        progress_percent: 100,
        current_stage: _t("جاهزة للاستلام"),
        station_code: "",
        eta_minutes: 0,
        eta_reliable: true,
        eta_scope: "service",
        queue_position: 0,
    }));
    return {
        demo: true,
        contract_version: "17.0-customer-display",
        company: { id: 1, name: _t("كريستال كلين"), logo_available: false, logo_url: "" },
        display_policy: { intro_enabled: true, intro_seconds: 2, rotation_seconds: 10, fullscreen_requires_user_gesture: true, show_vehicle_model: true, show_current_stage: true, show_eta: true, show_ready_for_pickup: true },
        counts: { visible: cars.length + ready.length, in_service: 6, waiting: 3, ready_for_pickup: 3 },
        idle: false,
        rotation: cars,
        ready_for_pickup: ready,
    };
}

export const ccDataService = {
    dependencies: ["orm", "bus_service"],
    start(env, { orm, bus_service: busService }) {
        const watchers = new Map();
        const channelRefCount = new Map();
        const pending = new Map();

        function channel(companyId) { return `crystal_clean_dashboard_${companyId}`; }
        function notify(companyId, detail = {}) {
            const callbacks = watchers.get(Number(companyId)) || new Set();
            for (const cb of callbacks) cb(detail);
        }
        function debounceNotify(companyId, detail) {
            const id = Number(companyId);
            window.clearTimeout(pending.get(id));
            pending.set(id, window.setTimeout(() => {
                pending.delete(id);
                if (!document.hidden) notify(id, detail);
            }, DEBOUNCE_MS));
        }
        function onBus(payload) {
            const data = payload?.payload || payload || {};
            if (data.company_id) debounceNotify(data.company_id, { kind: "bus", payload: data });
        }
        busService.subscribe?.(REFRESH_TYPE, onBus);

        const safetyTimer = window.setInterval(() => {
            if (document.hidden) return;
            for (const companyId of watchers.keys()) notify(companyId, { kind: "safety" });
        }, SAFETY_REFRESH_MS);

        const onVisibility = () => {
            if (!document.hidden) for (const companyId of watchers.keys()) debounceNotify(companyId, { kind: "visible" });
        };
        const onOffline = () => { for (const id of watchers.keys()) notify(id, { kind: "offline" }); };
        const onOnline = () => { for (const id of watchers.keys()) debounceNotify(id, { kind: "online" }); };
        document.addEventListener("visibilitychange", onVisibility);
        window.addEventListener("offline", onOffline);
        window.addEventListener("online", onOnline);

        async function call(method, args = []) {
            return orm.call("mrp.production", method, args);
        }

        return {
            isDemo: demoRequested,
            async loadOpsBundle(isManager = false) {
                if (demoRequested()) return demoOpsBundle(isManager);
                const [topology, operations, queue, intelligence] = await Promise.all([
                    call("get_station_topology"),
                    call("get_operations_data"),
                    call("get_queue_data"),
                    call("get_operational_intelligence_data"),
                ]);
                let management = null;
                let team = null;
                if (isManager) {
                    [management, team] = await Promise.all([call("get_management_data"), call("get_team_data")]);
                }
                const bundle = { topology, operations, queue, intelligence, management, team };
                if (!topology || !Array.isArray(topology.stations) || topology.stations.length === 0) return demoOpsBundle(isManager);
                return bundle;
            },
            async loadDisplay() {
                if (demoRequested()) return demoDisplay();
                const data = await call("get_customer_display_data");
                if (!data || (!data.idle && !data.rotation?.length && !data.ready_for_pickup?.length)) return demoDisplay();
                return data;
            },
            async stationDetails(id) { return call("get_station_details", [id]); },
            watch(companyId, callback) {
                const id = Number(companyId || 0);
                if (!id) return () => {};
                if (!watchers.has(id)) watchers.set(id, new Set());
                watchers.get(id).add(callback);
                const refs = (channelRefCount.get(id) || 0) + 1;
                channelRefCount.set(id, refs);
                if (refs === 1) busService.addChannel?.(channel(id));
                return () => {
                    watchers.get(id)?.delete(callback);
                    if (watchers.get(id)?.size === 0) watchers.delete(id);
                    const next = Math.max(0, (channelRefCount.get(id) || 1) - 1);
                    if (next === 0) {
                        channelRefCount.delete(id);
                        busService.deleteChannel?.(channel(id));
                    } else channelRefCount.set(id, next);
                };
            },
            _debug: { safetyTimer },
        };
    },
};

registry.category("services").add("cc_data", ccDataService);
