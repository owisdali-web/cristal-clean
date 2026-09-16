/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Plate } from "../../core/Plate";
import { CarSvg } from "../../illustrations/car_svg/CarSvg";
export class ReadyForPickup extends Component {
    static template = "car_wash_dashboard.ReadyForPickup";
    static components = { Plate, CarSvg };
    static props = ["cars", "newKeys?"];
    static defaultProps = { newKeys: [] };
    get title() { return _t("تفضّل بالاستلام"); }
    get subtitle() { return _t("سيارات جاهزة الآن"); }
    get empty() { return _t("لا توجد سيارات جاهزة للاستلام الآن"); }
    isNew(car) { return this.props.newKeys.includes(car.display_key); }
}
