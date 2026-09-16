/** @odoo-module **/

import { Component } from "@odoo/owl";

export class StationCard extends Component {
    typeLabel(value) {
        return {
            automatic: "Automatic",
            polishing: "Polishing",
            general: "General",
        }[value] || "General";
    }

    statusLabel(value) {
        return {
            available: "Available",
            busy: "Busy",
            conflict: "Check Station",
            not_configured: "Not Configured",
        }[value] || "Available";
    }

    sizeLabel(value) {
        return value === "large" ? "Large" : value === "small" ? "Small" : "—";
    }

    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} min`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}h ${rest}m` : `${hours}h`;
    }

    vehicleImage() {
        const visual = this.props.station?.current_car?.vehicle_visual || "car";
        const safe = ["car", "pickup", "van", "truck"].includes(visual) ? visual : "car";
        if (safe === "car") {
            return "/car_wash_dashboard/static/src/img/concept_car.webp";
        }
        return `/car_wash_dashboard/static/src/img/car_${safe}.svg`;
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
