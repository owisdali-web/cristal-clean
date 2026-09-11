# Crystal Clean Car Wash Dashboard 18.0.3.0

## Runtime stack
- Python/Odoo ORM backend
- OWL JavaScript client action
- QWeb/XML HTML templates
- SCSS + plain CSS animations
- Inline + standalone SVG vehicle silhouettes

## Main changes
- Dashboard analytics use real Crystal Clean `x_cc_*` wash-order architecture.
- Current-company scoping is enforced.
- Basic/Premium/Deluxe analytics replaced by actual sold wash services.
- Vehicle cards use real plate/model/color snapshots.
- Work-center queue includes pending/waiting/ready/progress.
- Direct Shop Floor navigation is available.
- Materials panel reads recipe materials directly.
- Sales-order values and posted accounting values are separate.
- V3 visual wash-tunnel scene, animated water/foam, SVG sedan/pickup/van/truck.
- Templates moved from large inline JS strings into maintainable QWeb/XML.

## C++ / VB.NET
Examples are included under `extras/` only for future external integrations. They are not Odoo runtime dependencies and are not loaded by the browser.
