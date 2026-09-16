/** @odoo-module **/

import { Component } from "@odoo/owl";

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
        const visual = item?.vehicle_visual || "car";
        const safe = ["car", "pickup", "van", "truck"].includes(visual) ? visual : "car";
        if (safe === "car") {
            return "/car_wash_dashboard/static/src/img/concept_car.webp";
        }
        return `/car_wash_dashboard/static/src/img/car_${safe}.svg`;
    }
}

QueuePanel.template = "car_wash_dashboard.QueuePanel";
QueuePanel.props = {
    queue: Array,
    total: Number,
    onOpenQueue: Function,
    onOpenCar: Function,
};
