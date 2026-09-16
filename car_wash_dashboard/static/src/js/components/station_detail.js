/** @odoo-module **/

import { Component } from "@odoo/owl";

export class StationDetail extends Component {
    typeLabel(value) {
        return {
            automatic: "Automatic Station",
            polishing: "Polishing Station",
            general: "General Station",
        }[value] || "General Station";
    }

    statusLabel(value) {
        return {
            available: "Available",
            busy: "Busy",
            conflict: "Station Conflict",
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
        const file = safe === "car" ? "car_sedan" : `car_${safe}`;
        return `/car_wash_dashboard/static/src/img/${file}.svg`;
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
