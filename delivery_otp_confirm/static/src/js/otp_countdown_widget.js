/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// `luxon` is a global provided by the Odoo asset bundle (same as core does:
// `const { DateTime } = luxon;`). It is NOT exported from
// "@web/core/l10n/dates", which is why the previous import was undefined.
const { DateTime } = luxon;

export class OtpCountdown extends Component {
    static template = "delivery_otp_confirm.OtpCountdown";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ text: "--:--", expired: false });
        this.timer = null;

        onMounted(() => {
            this._tick();
            this.timer = setInterval(() => this._tick(), 1000);
        });
        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
        });
    }

    /**
     * Return the expiry as a luxon DateTime.
     * In Odoo 18 a datetime field value is already a luxon DateTime, but we
     * keep a few fallbacks in case the value arrives as a string/Date.
     */
    _getExpiry() {
        const raw = this.props.record?.data?.[this.props.name];
        if (!raw) {
            return null;
        }
        if (raw.isLuxonDateTime) {
            return raw;
        }
        if (typeof raw === "string") {
            return DateTime.fromSQL(raw, { zone: "utc" });
        }
        if (raw instanceof Date) {
            return DateTime.fromJSDate(raw);
        }
        return DateTime.fromISO(String(raw));
    }

    _tick() {
        const exp = this._getExpiry();
        if (!exp || !exp.isValid) {
            this.state.text = "--:--";
            this.state.expired = true;
            return;
        }

        const diff = Math.max(
            0,
            Math.floor(exp.diff(DateTime.now(), "seconds").seconds)
        );
        this.state.expired = diff <= 0;
        const m = Math.floor(diff / 60);
        const s = diff % 60;
        this.state.text =
            `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    get isExpired() {
        return this.state.expired;
    }

    get displayText() {
        return this.state.text;
    }
}

// Odoo 17/18 field registry expects a descriptor object, not the component.
export const otpCountdown = {
    component: OtpCountdown,
    supportedTypes: ["datetime"],
};

registry.category("fields").add("otp_countdown", otpCountdown);
