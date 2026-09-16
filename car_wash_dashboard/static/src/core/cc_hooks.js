/** @odoo-module **/

import { onMounted, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { clamp } from "./cc_format";

export function useCcData() {
    return useService("cc_data");
}

export function useReducedMotion() {
    const state = useState({ reduced: false });
    let media;
    const sync = () => { state.reduced = Boolean(media?.matches); };
    onMounted(() => {
        media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
        sync();
        media?.addEventListener?.("change", sync);
    });
    onWillUnmount(() => media?.removeEventListener?.("change", sync));
    return state;
}

export function useClock(intervalMs = 1000) {
    const state = useState({ now: new Date() });
    let timer;
    onMounted(() => {
        timer = window.setInterval(() => { state.now = new Date(); }, intervalMs);
    });
    onWillUnmount(() => window.clearInterval(timer));
    return state;
}

export function useRotation(getItems, getSeconds) {
    const state = useState({ index: 0, tick: 0 });
    let timer;
    const advance = () => {
        if (document.hidden) return;
        const items = getItems() || [];
        if (items.length <= 1) {
            state.index = 0;
            return;
        }
        state.index = (state.index + 1) % items.length;
        state.tick += 1;
    };
    const start = () => {
        window.clearInterval(timer);
        const seconds = Math.max(3, Number(getSeconds?.() || 10));
        timer = window.setInterval(advance, seconds * 1000);
    };
    onMounted(start);
    onWillUnmount(() => window.clearInterval(timer));
    return { state, advance, restart: start };
}

export function useCountUp(initialValue = 0, duration = 560) {
    const state = useState({ value: Number(initialValue || 0) });
    let raf = 0;
    const setTarget = (targetValue) => {
        const target = Number(targetValue || 0);
        if (!Number.isFinite(target)) return;
        const startValue = Number(state.value || 0);
        if (startValue === target) return;
        cancelAnimationFrame(raf);
        const started = performance.now();
        const frame = (now) => {
            const p = clamp((now - started) / duration, 0, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            state.value = startValue + (target - startValue) * eased;
            if (p < 1) raf = requestAnimationFrame(frame);
            else state.value = target;
        };
        raf = requestAnimationFrame(frame);
    };
    onWillUpdateProps((nextProps) => {
        if (Object.prototype.hasOwnProperty.call(nextProps, "value")) setTarget(nextProps.value);
    });
    onWillUnmount(() => cancelAnimationFrame(raf));
    return { state, setTarget };
}
