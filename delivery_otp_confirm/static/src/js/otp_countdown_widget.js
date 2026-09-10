/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DateTime } from "@web/core/l10n/dates";

console.log("[OTP Widget] JS file loaded");

export class OtpCountdown extends Component {
    static template = "delivery_otp_confirm.OtpCountdown";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({
            text: "--:--",
            expired: false,
        });
        this.timer = null;
        this._tick = this._tick.bind(this);

        onMounted(() => {
            this._tick();
            this.timer = setInterval(this._tick, 1000);
        });

        onWillUnmount(() => {
            if (this.timer) {
                clearInterval(this.timer);
                this.timer = null;
            }
        });
    }

    _tick() {
        // Use the actual field name the widget is bound to
        const raw = this.props.record.data[this.props.name];

        if (!raw) {
            this.state.text = "--:--";
            this.state.expired = true;
            return;
        }

        let exp;
        try {
            if (typeof raw === "string") {
                exp = DateTime.fromSQL(raw, { zone: "utc" });
            } else if (raw && raw.isLuxonDateTime) {
                exp = raw;
            } else if (raw instanceof Date) {
                exp = DateTime.fromJSDate(raw, { zone: "utc" });
            } else {
                exp = DateTime.fromISO(String(raw), { zone: "utc" });
            }
        } catch (e) {
            exp = null;
        }

        if (!exp || !exp.isValid) {
            this.state.text = "--:--";
            this.state.expired = true;
            return;
        }

        const diff = Math.max(
            0,
            Math.floor(exp.diff(DateTime.utc(), "seconds").seconds)
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

OtpCountdown.supportedTypes = ["datetime"];

registry.category("fields").add("otp_countdown", OtpCountdown);
console.log("[OTP Widget] registered as otp_countdown");