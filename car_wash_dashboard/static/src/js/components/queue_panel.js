/** @odoo-module **/

import { Component } from "@odoo/owl";
import { translateUi } from "../ui_translations";
import { vehicleImagePath } from "../vehicle_visuals";

export class QueuePanel extends Component {
    tr(text, ...args) {
        return translateUi(text, ...args);
    }

    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} ${this.tr("min")}`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}${this.tr("h")} ${rest}${this.tr("m")}` : `${hours}${this.tr("h")}`;
    }

    sizeLabel(value) {
        return value === "large" ? this.tr("Large") : value === "small" ? this.tr("Small") : "—";
    }

    currentVehicleLabel() {
        return this.tr("Current vehicle");
    }

    vehicleImage(item) {
        return vehicleImagePath(item);
    }
}

QueuePanel.template = "car_wash_dashboard.QueuePanel";
QueuePanel.props = {
    queue: Array,
    total: Number,
    onOpenQueue: Function,
    onOpenCar: Function,
};
