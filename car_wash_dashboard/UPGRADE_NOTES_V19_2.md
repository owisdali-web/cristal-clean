# 18.0.19.2 — Odoo 18 SCSS compatibility fix

- Fixes Odoo 18 asset compilation error: `Incompatible units: vw and px`.
- Preserves native CSS `clamp()` / `min()` expressions through Sass interpolation so LibSass does not evaluate mixed viewport/absolute units.
- Frontend styling only; no Python model, controller, security, or business logic changes.
