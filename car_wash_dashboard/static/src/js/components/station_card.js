/** @odoo-module **/

import { Component } from "@odoo/owl";
import { translateUi } from "../ui_translations";
import { vehicleImagePath } from "../vehicle_visuals";

export class StationCard extends Component {
    tr(text, ...args) {
        return translateUi(text, ...args);
    }

    typeLabel(value) {
        return {
            automatic: this.tr("Automatic"),
            polishing: this.tr("Polishing"),
            general: this.tr("General"),
        }[value] || this.tr("General");
    }

    statusLabel(value) {
        return {
            available: this.tr("Available"),
            busy: this.tr("Busy"),
            finishing: this.tr("Finishing"),
            conflict: this.tr("Check Station"),
            not_configured: this.tr("Not Configured"),
        }[value] || this.tr("Available");
    }

    sizeLabel(value) {
        return value === "large" ? this.tr("Large") : value === "small" ? this.tr("Small") : "—";
    }

    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} ${this.tr("min")}`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}${this.tr("h")} ${rest}${this.tr("m")}` : `${hours}${this.tr("h")}`;
    }

    currentVehicleLabel() {
        return this.tr("Current vehicle");
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
