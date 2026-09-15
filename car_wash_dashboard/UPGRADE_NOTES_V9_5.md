# Crystal Clean Dashboard 18.0.9.5

Typography repair based on Odoo Shell forensics.

- Removed V9.3 and V9.4 typography layers from active backend assets.
- Eliminated the global `.cc9-root *` font-family override that replaced FontAwesome glyphs.
- Restored FontAwesome explicitly with `.cc9-root .fa` / `.fa::before`.
- Reduced typography overrides to scoped selectors and removed the 365 `!important` cascade.
- Cairo remains preferred when available, with Windows-safe Arabic fallbacks. No remote font import or font binary is bundled.
- No Python, JavaScript, XML structure, business logic, layout, images, animations, MRP, POS, stock, accounting, or realtime logic changed.
