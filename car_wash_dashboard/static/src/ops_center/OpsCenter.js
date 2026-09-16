/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import "../core/cc_data_service";
import { useCcData, useClock } from "../core/cc_hooks";
import { formatClock, formatMinutes, formatNumber } from "../core/cc_format";
import { WashTunnel } from "../illustrations/wash_tunnel/WashTunnel";
import { KpiCard } from "./components/KpiCard";
import { StationGrid } from "./components/StationGrid";
import { QueuePanel } from "./components/QueuePanel";
import { StationDrawer } from "./components/StationDrawer";
import { ManagementStrip } from "./components/ManagementStrip";
import { LiveBadge } from "./components/LiveBadge";
import { ConnectionBanner } from "./components/ConnectionBanner";

export class OpsCenter extends Component {
    static template = "car_wash_dashboard.OpsCenter";
    static components = { WashTunnel, KpiCard, StationGrid, QueuePanel, StationDrawer, ManagementStrip, LiveBadge, ConnectionBanner };
    static props = ["*"];

    setup() {
        this.data = useCcData();
        this.user = user;
        this.clock = useClock(1000);
        this.state = useState({
            loading: true,
            refreshing: false,
            online: navigator.onLine !== false,
            error: "",
            bundle: null,
            isManager: false,
            selectedStationId: null,
            drawerOpen: false,
            theme: localStorage.getItem("cc_ops_theme") || "dark",
            lastUpdated: null,
            demo: false,
            paused: document.hidden,
        });
        this.unwatch = null;
        this.visibilityHandler = () => { this.state.paused = document.hidden; };
        onWillStart(async () => {
            try { this.state.isManager = await this.user.hasGroup("car_wash_dashboard.group_car_wash_manager"); }
            catch { this.state.isManager = false; }
            await this.load(true);
        });
        onMounted(() => document.addEventListener("visibilitychange", this.visibilityHandler));
        onWillUnmount(() => { this.unwatch?.(); document.removeEventListener("visibilitychange", this.visibilityHandler); });
    }

    get t() {
        return {
            title: _t("مركز التشغيل — Crystal Clean"),
            subtitle: _t("صورة لحظية من MRP بدون تغيير أوامر العمل"),
            theme: _t("تبديل المظهر"),
            demo: _t("وضع العرض التجريبي"),
            retry: _t("إعادة المحاولة"),
            noData: _t("لا توجد بيانات تشغيل متاحة الآن"),
        };
    }

    async load(initial = false) {
        if (!initial) this.state.refreshing = true;
        this.state.error = "";
        try {
            const bundle = await this.data.loadOpsBundle(this.state.isManager);
            this.state.bundle = bundle;
            this.state.demo = Boolean(bundle.demo);
            this.state.online = true;
            this.state.lastUpdated = new Date();
            this.bindRealtime(bundle.operations?.company_id || bundle.topology?.company_id || bundle.intelligence?.company_id);
        } catch (error) {
            this.state.online = false;
            this.state.error = _t("تعذر تحديث بيانات التشغيل. ستبقى آخر قراءة ظاهرة.");
            console.error("Crystal Clean operations refresh failed", error);
        } finally {
            this.state.loading = false;
            this.state.refreshing = false;
        }
    }

    bindRealtime(companyId) {
        if (!companyId || this.boundCompanyId === companyId) return;
        this.unwatch?.();
        this.boundCompanyId = companyId;
        this.unwatch = this.data.watch(companyId, (event) => {
            if (event.kind === "offline") {
                this.state.online = false;
                return;
            }
            this.load(false);
        });
    }

    get operations() { return this.state.bundle?.operations || {}; }
    get intelligence() { return this.state.bundle?.intelligence || {}; }
    get management() { return this.state.bundle?.management || null; }
    get team() { return this.state.bundle?.team || null; }

    get stations() {
        const base = this.operations.stations || this.state.bundle?.topology?.stations || [];
        const intel = new Map((this.intelligence.stations || []).map((row) => [row.station_id, row]));
        return [...base]
            .map((station) => {
                const i = intel.get(station.id) || {};
                const running = i.running_jobs || [];
                const enrichedCars = (station.cars || []).map((car) => {
                    const run = running.find((r) => r.production_id === car.production_id || r.production_id === car.id) || {};
                    return { ...car, remaining_minutes: run.remaining_minutes ?? car.remaining_minutes, delay_minutes: run.delay_minutes || 0 };
                });
                return { ...station, ...i, id: station.id, name: station.name, kind: station.kind, display_order: station.display_order, cars: enrichedCars };
            })
            .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
    }

    get queueRows() {
        const source = this.operations.queue?.rows || this.state.bundle?.queue?.queue?.rows || [];
        const intelByWo = new Map();
        for (const station of this.intelligence.stations || []) {
            for (const row of station.queue || []) intelByWo.set(row.workorder_id, { ...row, station_code: station.station_code, station_name: station.station_name, eta_reliable: row.estimate_reliable });
        }
        return source.map((row) => ({ ...row, ...(intelByWo.get(row.workorder_id) || {}) }));
    }

    get kpis() {
        const o = this.operations.kpis || {};
        const i = this.intelligence.kpis || {};
        const totalCapacity = this.stations.reduce((sum, s) => sum + Math.max(1, Number(s.capacity || 1)), 0);
        const expectedValues = (this.intelligence.stations || []).map((s) => Number(s.avg_expected_today_minutes || 0)).filter((v) => v > 0);
        const expected = expectedValues.length ? expectedValues.reduce((a, b) => a + b, 0) / expectedValues.length : 0;
        const actual = Number(i.avg_completed_duration_today_minutes || 0);
        const delta = expected > 0 ? actual - expected : 0;
        return [
            { key: "washing", label: _t("في الغسيل"), value: o.in_service || 0, caption: _t("السعة الكلية %s", formatNumber(totalCapacity)), icon: "≋", tone: "info" },
            { key: "waiting", label: _t("في الانتظار"), value: o.waiting_for_station || 0, caption: _t("أقدم انتظار %s", formatMinutes(i.max_queue_age_minutes || 0)), icon: "⌛", tone: "warning" },
            { key: "ready", label: _t("جاهزة بالموقف"), value: o.ready_for_delivery || 0, caption: _t("بانتظار الاستلام"), icon: "✓", tone: "positive" },
            { key: "done", label: _t("منتهية اليوم"), value: i.completed_today || 0, caption: _t("آخر ساعة %s", formatNumber(i.completed_last_60_minutes || 0)), icon: "↗", tone: "neutral" },
            { key: "avg", label: _t("متوسط المدة"), value: actual, caption: expected ? _t("المتوقع %s · الفرق %s", formatMinutes(expected), formatMinutes(Math.abs(delta))) : _t("لا يوجد خط أساس كافٍ"), icon: "◷", tone: delta > 3 ? "warning" : "info", suffix: _t(" د"), decimals: 1 },
            { key: "delay", label: _t("متأخرة"), value: i.delayed_running_jobs || 0, caption: _t("عمليات تجاوزت الزمن المتوقع"), icon: "!", tone: Number(i.delayed_running_jobs || 0) > 0 ? "danger" : "neutral" },
        ];
    }

    get projectedClear() { return this.intelligence.kpis?.projection_reliable_for_all_stations === false ? false : (this.intelligence.kpis?.projected_system_clear_minutes || 0); }
    get headerCar() { return (this.operations.cars || [])[0] || {}; }
    get clockText() { return formatClock(this.clock.now); }

    retry() { this.load(false); }
    get rootClass() { return `o_cc_ops ${this.state.loading ? "is-loading" : ""} ${this.state.paused ? "o_cc_paused" : ""}`; }

    toggleTheme() {
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        localStorage.setItem("cc_ops_theme", this.state.theme);
    }
    selectStation(id) { this.state.selectedStationId = id; this.state.drawerOpen = true; }
    closeDrawer() { this.state.drawerOpen = false; }
}

registry.category("actions").add("crystal_clean_ops_center", OpsCenter);
