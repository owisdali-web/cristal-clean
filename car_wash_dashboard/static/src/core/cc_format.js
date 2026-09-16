/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
const EASTERN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

export function westernDigits(value) {
    return String(value ?? "")
        .replace(/[٠-٩]/g, (d) => String(ARABIC_DIGITS.indexOf(d)))
        .replace(/[۰-۹]/g, (d) => String(EASTERN_DIGITS.indexOf(d)));
}

export function formatNumber(value, maximumFractionDigits = 0) {
    const number = Number(value || 0);
    return new Intl.NumberFormat("ar-LY-u-nu-latn", {
        maximumFractionDigits,
        minimumFractionDigits: 0,
    }).format(Number.isFinite(number) ? number : 0);
}

export function formatMinutes(value, fallback = "—") {
    if (value === false || value === null || value === undefined || value === "") {
        return fallback;
    }
    const minutes = Number(value);
    if (!Number.isFinite(minutes)) {
        return fallback;
    }
    if (minutes < 60) {
        return _t("%s د", formatNumber(Math.max(0, Math.round(minutes))));
    }
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return m ? _t("%s س %s د", formatNumber(h), formatNumber(m)) : _t("%s س", formatNumber(h));
}

export function formatCurrency(value, symbol = "د.ل") {
    const suffix = symbol || "د.ل";
    return `${formatNumber(value, 2)} ${suffix}`;
}

export function formatPlate(value) {
    return westernDigits(value || "—").replace(/\s+/g, " ").trim();
}

export function isOpaqueReference(value) {
    return String(value || "").trim().startsWith("#");
}

export function formatClock(date = new Date()) {
    return new Intl.DateTimeFormat("ar-LY-u-nu-latn", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    }).format(date);
}

export function formatArabicDate(date = new Date()) {
    return new Intl.DateTimeFormat("ar-LY-u-nu-latn", {
        weekday: "long",
        day: "numeric",
        month: "long",
    }).format(date);
}

export function clamp(value, min = 0, max = 100) {
    const number = Number(value || 0);
    return Math.min(max, Math.max(min, Number.isFinite(number) ? number : min));
}

export function stationKindLabel(kind) {
    return ({ general: _t("عامة"), auto: _t("أوتوماتيك"), polish: _t("تلميع") })[kind] || _t("عامة");
}

export function stationStateLabel(state) {
    return ({
        available: _t("متاحة"),
        busy: _t("مشغولة"),
        queued: _t("بانتظار البدء"),
        overloaded: _t("تجاوز السعة"),
        maintenance: _t("صيانة"),
        closed: _t("مغلقة"),
    })[state] || _t("غير محددة");
}

export function vehicleBodyType(model = "") {
    const text = String(model).toLowerCase();
    if (/hilux|ranger|navara|pickup|بيك/.test(text)) return "pickup";
    if (/tucson|sportage|land cruiser|patrol|prado|rav4|suv|جيب/.test(text)) return "suv";
    if (/yaris|i10|picanto|hatch|هاتش/.test(text)) return "hatchback";
    return "sedan";
}

export function vehicleColorHex(color = "") {
    const text = String(color).toLowerCase();
    const map = [
        [/أبيض|white/, "#f3f5f6"],
        [/أسود|black/, "#23282d"],
        [/فضي|silver/, "#b8c2c9"],
        [/رمادي|grey|gray/, "#717d85"],
        [/أحمر|red/, "#b94949"],
        [/أزرق|blue/, "#3977a8"],
        [/ذهبي|gold/, "#ad8b4a"],
    ];
    return (map.find(([re]) => re.test(text)) || [null, "#7f8c94"])[1];
}
