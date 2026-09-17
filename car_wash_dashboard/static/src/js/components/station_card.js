/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { vehicleImagePath } from "../vehicle_visuals";

export class StationCard extends Component {
    typeLabel(value) {
        return {
            automatic: _t("Automatic"),
            polishing: _t("Polishing"),
            general: _t("General"),
        }[value] || _t("General");
    }

    statusLabel(value) {
        return {
            available: _t("Available"),
            busy: _t("Busy"),
            finishing: _t("Finishing"),
            conflict: _t("Check Station"),
            not_configured: _t("Not Configured"),
        }[value] || _t("Available");
    }

    sizeLabel(value) {
        return value === "large" ? _t("Large") : value === "small" ? _t("Small") : "—";
    }

    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} ${_t("min")}`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}${_t("h")} ${rest}${_t("m")}` : `${hours}${_t("h")}`;
    }

    currentVehicleLabel() {
        return _t("Current vehicle");
    }

    progressStyle() {
        const value = Number(this.props.station?.progress_percent);
        const safe = Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
        return `width: ${safe}%`;
    }

    vehicleImage() {
        return vehicleImagePath(this.props.station?.current_car);
    }

    select() {
        if (!this.props.station?.is_placeholder) {
            this.props.onSelect(this.props.station.id);
        }
    }
}

StationCard.template = "car_wash_dashboard.StationCard";
StationCard.props = {
    station: Object,
    selected: Boolean,
    onSelect: Function,
};
