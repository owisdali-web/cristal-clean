/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { vehicleImagePath } from "../vehicle_visuals";

export class StationDetail extends Component {
    typeLabel(value) {
        return {
            automatic: _t("Automatic Station"),
            polishing: _t("Polishing Station"),
            general: _t("General Station"),
        }[value] || _t("General Station");
    }

    statusLabel(value) {
        return {
            available: _t("Available"),
            busy: _t("Busy"),
            finishing: _t("Finishing"),
            conflict: _t("Station Conflict"),
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

    noNotesLabel() {
        return _t("No notes");
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
