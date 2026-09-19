/** @odoo-module **/

const SMALL_VEHICLE_IMAGE = "/car_wash_dashboard/static/src/img/vehicle_small.webp";
const LARGE_VEHICLE_IMAGE = "/car_wash_dashboard/static/src/img/vehicle_large.webp";

const LARGE_VISUALS = new Set(["large", "pickup", "van", "truck", "suv"]);

/**
 * Resolve a reference-style dashboard vehicle image.
 *
 * Explicit Small/Large is the primary source of truth. Legacy body type values
 * are kept only as a backwards-compatible fallback for older wash orders.
 */
export function vehicleImagePath(vehicle) {
    const size = String(vehicle?.vehicle_size || "").toLowerCase();
    const visual = String(vehicle?.vehicle_visual || "").toLowerCase();

    if (size === "large") {
        return LARGE_VEHICLE_IMAGE;
    }
    if (size === "small") {
        return SMALL_VEHICLE_IMAGE;
    }
    if (LARGE_VISUALS.has(visual)) {
        return LARGE_VEHICLE_IMAGE;
    }
    return SMALL_VEHICLE_IMAGE;
}
