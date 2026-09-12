# Car Wash Dashboard 18.0.5.2 — OWL Template Runtime Fix

## Root cause fixed
Owl templates do not expose JavaScript constructors/globals such as `String` and `Math` as direct template-context functions.

The 18.0.5.1 template contained:
- `String(...).padStart(...)`
- `Math.min(...)`

Owl compiled those as `ctx.String(...)` / `ctx.Math...`, which caused:
`TypeError: ctx.String is not a function`.

## Fix
- Added component method `formatCount(value)` and call it from QWeb.
- Added component method `materialPreviewCount()` and call it from QWeb.
- Kept JavaScript globals inside normal JS code where they are valid.
- Preserved the 18.0.5.1 CSS asset fix.
- No business logic, MRP, stock, accounting, POS, materials, stations or automations changed.
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
