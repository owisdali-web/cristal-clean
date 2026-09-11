# Crystal Clean Car Wash Dashboard 18.0.5.1

CSS asset hotfix for the Concept Replica dashboard.

## Root cause fixed
The 18.0.5.0 package accidentally contained an orphan tail from a Google Fonts URL at the top level of `dashboard_concept_replica.css`:

`500;600;700;800&family=Manrope...`

That is not a CSS selector/declaration and can break Odoo's backend CSS asset bundle, producing the red fallback banner.

## Changes
- Removed the malformed orphan Google Fonts fragment.
- No remote `@import` is used in backend assets.
- Replaced `light-dark()` variables with explicit light-theme values for conservative Odoo 18 asset compatibility.
- Uses system/local Arabic font fallbacks.
- No business logic, MRP, stock, accounting, POS, materials, BoMs, or work-center records changed.
