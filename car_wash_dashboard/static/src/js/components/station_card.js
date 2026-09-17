/** @odoo-module **/

import { Component } from "@odoo/owl";
import { vehicleImagePath } from "../vehicle_visuals";

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
            finishing: "Finishing",
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
