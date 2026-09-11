# Crystal Clean Car Wash Dashboard 18.0.4.0

## V4 Live Journey

This upgrade keeps the validated 18.0.3.1 CSS fix and adds a live animated operational layer.

### New
- Animated Vehicle Journey: entry -> real MRP workorder stations -> ready for delivery.
- Vehicle marker physically glides between nodes when the real workorder state changes.
- Water animation while washing and sparkle animation when ready for delivery.
- Per-car journey percent, current station, next stage, current-stage age, and evidence-based delay warning.
- Odoo 18 `bus` push refresh: Shop Floor / MRP / wash-sale changes emit a lightweight refresh signal.
- 30-second polling remains only as a fallback.
- Realtime header badge and live event toast.
- Company-scoped bus channel; bus payload contains no customer or vehicle details.
- Optional C++ and VB.NET reference examples remain outside Odoo runtime.

### Safety
- No automatic completion, cancellation, reservation, stock consumption, or stage movement was added.
- Shop Floor remains the operational source of truth.
- Realtime automation only refreshes the dashboard after committed Odoo changes.
- Existing `x_cc_*` architecture is preserved.
- Existing 18.0.3.1 SVG/CSS fallback remains preserved.
