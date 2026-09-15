# Crystal Clean Dashboard 18.0.9.6

Typography-only update based on Odoo Shell font forensics.

- Uses Odoo 18 bundled Tajawal files via `/web/static/fonts/google/Tajawal/...` with local `@font-face` declarations.
- Does not bundle or redistribute font files in this module.
- Preserves FontAwesome explicitly.
- Removes V9.5 from the active asset list (file retained for history, not loaded).
- No layout, Python, JS, QWeb, MRP, POS, stock, accounting, realtime or automation changes.
