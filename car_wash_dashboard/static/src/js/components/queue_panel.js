/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { vehicleImagePath } from "../vehicle_visuals";

export class QueuePanel extends Component {
    formatMinutes(value) {
        const minutes = Number(value);
        if (!Number.isFinite(minutes) || minutes < 0) return "—";
        if (minutes < 60) return `${minutes} ${_t("min")}`;
        const hours = Math.floor(minutes / 60);
        const rest = minutes % 60;
        return rest ? `${hours}${_t("h")} ${rest}${_t("m")}` : `${hours}${_t("h")}`;
    }

    sizeLabel(value) {
        return value === "large" ? _t("Large") : value === "small" ? _t("Small") : "—";
    }

    currentVehicleLabel() {
        return _t("Current vehicle");
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
