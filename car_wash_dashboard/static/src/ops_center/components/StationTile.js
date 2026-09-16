/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Plate } from "../../core/Plate";
import { CarSvg } from "../../illustrations/car_svg/CarSvg";
import { formatMinutes, stationKindLabel, stationStateLabel } from "../../core/cc_format";
export class StationTile extends Component {
    static template = "car_wash_dashboard.StationTile";
    static components = { Plate, CarSvg };
    static props = ["station", "onSelect"];
    get state() { return this.props.station.runtime_state || "available"; }
    get stateLabel() { return stationStateLabel(this.state); }
    get kindLabel() { return stationKindLabel(this.props.station.kind); }
    get car() { return (this.props.station.cars || [])[0] || {}; }
    get plate() { return this.car.plate || this.car.public_reference || ""; }
    get remaining() {
        if (this.car.delay_minutes > 0) return _t("متأخرة %s", formatMinutes(this.car.delay_minutes));
        if (this.car.remaining_minutes !== false && this.car.remaining_minutes !== undefined) return formatMinutes(this.car.remaining_minutes);
        return _t("قيد التقدير");
    }
    get queueText() { return _t("%s في الصف", this.props.station.queue_count || 0); }
    get occupancyPercent() { return Math.min(100, Number(this.props.station.occupancy_rate || 0)); }
    get occupancyText() { return `${this.props.station.occupancy || 0}/${this.props.station.capacity || 1}`; }
    get queueStack() { return Array.from({ length: Math.min(3, Number(this.props.station.queue_count || 0)) }, (_, i) => i); }
    select() { this.props.onSelect(this.props.station.id); }
}
