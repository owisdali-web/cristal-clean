/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import "../core/cc_data_service";
import { useCcData, useClock, useRotation } from "../core/cc_hooks";
import { formatArabicDate, formatClock } from "../core/cc_format";
import { StartGate } from "./components/StartGate";
import { IntroSplash } from "./components/IntroSplash";
import { CounterBar } from "./components/CounterBar";
import { HeroCarCard } from "./components/HeroCarCard";
import { ReadyForPickup } from "./components/ReadyForPickup";
import { NextInLine } from "./components/NextInLine";
import { IdleScreen } from "./components/IdleScreen";
import { ConnectionBanner } from "../ops_center/components/ConnectionBanner";

export class CustomerDisplay extends Component {
    static template = "car_wash_dashboard.CustomerDisplay";
    static components = { StartGate, IntroSplash, CounterBar, HeroCarCard, ReadyForPickup, NextInLine, IdleScreen, ConnectionBanner };
    static props = ["*"];

    setup() {
        this.dataService = useCcData();
        this.clock = useClock(1000);
        this.state = useState({
            data: null,
            phase: "gate",
            loading: true,
            online: navigator.onLine !== false,
            lastUpdated: null,
            error: "",
            newReadyKeys: [],
            theme: localStorage.getItem("cc_display_theme") || "dark",
            chimeEnabled: localStorage.getItem("cc_display_chime") === "1",
            burnX: 0,
            burnY: 0,
            paused: document.hidden,
            demo: false,
        });
        this.rotation = useRotation(
            () => this.state.data?.rotation || [],
            () => this.state.data?.display_policy?.rotation_seconds || 10
        );
        this.readyKeys = new Set();
        this.unwatch = null;
        this.introTimer = null;
        this.burnTimer = null;
        this.visibilityHandler = () => { this.state.paused = document.hidden; };
        onWillStart(() => this.load(true));
        onMounted(() => {
            document.addEventListener("visibilitychange", this.visibilityHandler);
            this.burnTimer = window.setInterval(() => {
                const n = Math.floor(Date.now() / 600000);
                this.state.burnX = ((n % 5) - 2) * 2;
                this.state.burnY = (((n * 3) % 5) - 2) * 2;
            }, 600000);
        });
        onWillUnmount(() => {
            this.unwatch?.();
            window.clearTimeout(this.introTimer);
            window.clearInterval(this.burnTimer);
            document.removeEventListener("visibilitychange", this.visibilityHandler);
            if (this.audioContext) this.audioContext.close?.();
        });
    }

    get t() {
        return {
            welcome: _t("أهلاً بكم — نعتني بسيارتكم الآن"),
            privacy: _t("لا تُعرض أسماء أو أرقام هواتف أو مبالغ على هذه الشاشة"),
            theme: _t("تبديل المظهر"),
            soundOn: _t("إيقاف تنبيه الجاهزية"),
            soundOff: _t("تشغيل تنبيه الجاهزية"),
            noActive: _t("لا توجد سيارة قيد الخدمة الآن"),
            demo: _t("وضع العرض التجريبي"),
        };
    }

    async load(initial = false) {
        try {
            const data = await this.dataService.loadDisplay();
            const previous = this.readyKeys;
            const next = new Set((data.ready_for_pickup || []).map((car) => car.display_key));
            const newKeys = [...next].filter((key) => !previous.has(key));
            this.readyKeys = next;
            this.state.data = data;
            this.state.demo = Boolean(data.demo);
            this.state.newReadyKeys = initial ? [] : newKeys;
            this.state.online = true;
            this.state.lastUpdated = new Date();
            this.bindRealtime(data.company?.id);
            if (!initial && newKeys.length && this.state.chimeEnabled) this.playReadyTone();
            if (!initial && this.state.phase === "live") this.rotation.restart();
        } catch (error) {
            this.state.online = false;
            this.state.error = _t("تعذر تحديث شاشة العرض");
            console.error("Crystal Clean customer display refresh failed", error);
        } finally {
            this.state.loading = false;
        }
    }

    bindRealtime(companyId) {
        if (!companyId || this.boundCompanyId === companyId) return;
        this.unwatch?.();
        this.boundCompanyId = companyId;
        this.unwatch = this.dataService.watch(companyId, (event) => {
            if (event.kind === "offline") { this.state.online = false; return; }
            this.load(false);
        });
    }

    async startDisplay() {
        const policy = this.policy;
        try {
            if (policy.fullscreen_requires_user_gesture && !document.fullscreenElement) await document.documentElement.requestFullscreen?.();
        } catch (error) {
            console.debug("Fullscreen request was not accepted", error);
        }
        this.unlockAudio();
        if (policy.intro_enabled) {
            this.state.phase = "intro";
            window.clearTimeout(this.introTimer);
            this.introTimer = window.setTimeout(() => { this.state.phase = "live"; }, Math.max(0.5, Number(policy.intro_seconds || 2)) * 1000);
        } else {
            this.state.phase = "live";
        }
    }

    unlockAudio() {
        try {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            this.audioContext = this.audioContext || new Ctx();
            this.audioContext.resume?.();
        } catch { /* optional audio */ }
    }

    playReadyTone() {
        if (!this.audioContext) return;
        try {
            const now = this.audioContext.currentTime;
            [660, 880].forEach((frequency, index) => {
                const osc = this.audioContext.createOscillator();
                const gain = this.audioContext.createGain();
                osc.frequency.value = frequency;
                osc.type = "sine";
                gain.gain.setValueAtTime(0.0001, now + index * 0.11);
                gain.gain.exponentialRampToValueAtTime(0.07, now + index * 0.11 + 0.02);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + index * 0.11 + 0.16);
                osc.connect(gain).connect(this.audioContext.destination);
                osc.start(now + index * 0.11);
                osc.stop(now + index * 0.11 + 0.18);
            });
        } catch { /* optional audio */ }
    }

    toggleChime() {
        this.state.chimeEnabled = !this.state.chimeEnabled;
        localStorage.setItem("cc_display_chime", this.state.chimeEnabled ? "1" : "0");
        if (this.state.chimeEnabled) { this.unlockAudio(); this.playReadyTone(); }
    }
    toggleTheme() {
        this.state.theme = this.state.theme === "dark" ? "light" : "dark";
        localStorage.setItem("cc_display_theme", this.state.theme);
    }

    get company() { return this.state.data?.company || { name: "Crystal Clean", logo_available: false, logo_url: "" }; }
    get policy() { return this.state.data?.display_policy || { intro_enabled: true, intro_seconds: 2, rotation_seconds: 10, fullscreen_requires_user_gesture: true, show_vehicle_model: true, show_current_stage: true, show_eta: true, show_ready_for_pickup: true }; }
    get counts() { return this.state.data?.counts || { in_service: 0, waiting: 0, ready_for_pickup: 0 }; }
    get rotationCars() { return this.state.data?.rotation || []; }
    get readyCars() { return this.state.data?.ready_for_pickup || []; }
    get currentCar() { const rows = this.rotationCars; return rows.length ? rows[this.rotation.state.index % rows.length] : null; }
    get isIdle() { return Boolean(this.state.data?.idle); }
    get clockText() { return formatClock(this.clock.now); }
    get dateText() { return formatArabicDate(this.clock.now); }
    get burnStyle() { return `transform: translate(${this.state.burnX}px, ${this.state.burnY}px);`; }
    get rotationStyle() { return `--cc-rotation:${Math.max(3, Number(this.policy.rotation_seconds || 10))}s`; }
    get rootClass() { return `o_cc_display ${this.state.paused ? "o_cc_paused" : ""}`; }
    dotClass(index) { return `cc_rotation_dot ${index === (this.rotation.state.index % Math.max(1, this.rotationCars.length)) ? "is-active" : ""}`; }
}

registry.category("actions").add("crystal_clean_customer_display", CustomerDisplay);
