/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { WashTunnel } from "../../illustrations/wash_tunnel/WashTunnel";
export class IdleScreen extends Component {
    static template = "car_wash_dashboard.IdleScreen";
    static components = { WashTunnel };
    static props = ["company"];
    get t(){ return { welcome:_t("أهلاً وسهلاً بكم"), line:_t("نعتني بسيارتكم بعناية من البداية حتى اللمعة الأخيرة") }; }
    get demoCar(){ return {vehicle_model:"Toyota Camry",vehicle_color:"فضي"}; }
}
