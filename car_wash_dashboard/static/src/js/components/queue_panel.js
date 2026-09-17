/** @odoo-module **/

import { Component } from "@odoo/owl";
import { vehicleImagePath } from "../vehicle_visuals";

export class QueuePanel extends Component {
    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} min`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}h ${rest}m` : `${hours}h`;
    }

    sizeLabel(value) {
        return value === "large" ? "Large" : value === "small" ? "Small" : "—";
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
