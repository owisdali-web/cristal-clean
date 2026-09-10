/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DateTime } from "luxon";

export class OtpCountdown extends Component {
    static template = "delivery_otp_confirm.OtpCountdown";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({
            seconds: 0,
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
        const raw = this.props.record.data.expiry;
        if (!raw) {
            this.state.text = "--:--";
            this.state.expired = true;
            this.state.seconds = 0;
            return;
        }

        // In Odoo 17/18 the value can be a luxon DateTime or a raw SQL string.
        let exp;
        if (typeof raw === "string") {
            exp = DateTime.fromSQL(raw, { zone: "utc" });
        } else {
            // Already a DateTime object
            exp = raw.setZone ? raw : DateTime.fromJSDate(raw);
        }
        if (!exp || !exp.isValid) {
            this.state.text = "--:--";
            this.state.expired = true;
            return;
        }

        const diff = Math.max(0, Math.floor(exp.diff(DateTime.utc(), "seconds").seconds));
        this.state.seconds = diff;
        this.state.expired = diff <= 0;

        const m = Math.floor(diff / 60);
        const s = diff % 60;
        this.state.text = `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
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