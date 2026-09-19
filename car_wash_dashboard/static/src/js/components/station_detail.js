/** @odoo-module **/

import { Component } from "@odoo/owl";
import { translateUi } from "../ui_translations";
import { vehicleImagePath } from "../vehicle_visuals";

export class StationDetail extends Component {
    tr(text, ...args) {
        return translateUi(text, ...args);
    }

    typeLabel(value) {
        return {
            automatic: this.tr("Automatic Station"),
            polishing: this.tr("Polishing Station"),
            general: this.tr("General Station"),
        }[value] || this.tr("General Station");
    }

    statusLabel(value) {
        return {
            available: this.tr("Available"),
            busy: this.tr("Busy"),
            finishing: this.tr("Finishing"),
            conflict: this.tr("Station Conflict"),
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

    noNotesLabel() {
        return this.tr("No notes");
    }

    vehicleImage() {
        return vehicleImagePath(this.props.station?.current_car);
    }
}

StationDetail.template = "car_wash_dashboard.StationDetail";
StationDetail.props = {
    station: Object,
    onClose: Function,
    onOpenShopFloor: Function,
    onOpenProduction: Function,
    onOpenWorkorder: Function,
};
