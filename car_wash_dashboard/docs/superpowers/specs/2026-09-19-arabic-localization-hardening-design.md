# Arabic Localization Hardening Design

## Goal
When an Odoo user uses Arabic (`ar_*`), every user-facing label owned by `car_wash_dashboard` renders in Arabic and RTL; English users retain the existing English/LTR experience. Crystal Clean branding and stored business data remain unchanged.

## Current evidence
The 18.0.6.9.4 runtime diagnostic showed frontend bundle registration and RTL support were healthy, but the installed Arabic catalog lacked 87 JavaScript literals and 9 Python literals. The newer 18.0.6.9.5 source already closes the JavaScript catalog gap statically, so this hardening focuses on runtime robustness and preventing regression.

## Design
1. Keep Odoo user language as the single language source. No separate language switch is added.
2. Keep `_t()` / `_()` as the primary translation mechanism so Odoo language switching remains native.
3. Add a deterministic Arabic fallback map for module-owned frontend labels in `ui_translations.js`. It is used only when the browser/Odoo document language is Arabic and Odoo `_t()` returns the source text. This protects the dashboard from stale/missing frontend translation cache while keeping English unchanged.
4. Pass every module-owned dynamic status/heading through the existing `tr()` helper before display. Stored names (customer, vehicle, service, station, plate) are never translated by this layer.
5. Keep explicit RTL class/direction logic driven from Odoo/document language.
6. Keep the PO catalog complete and valid. Add tests that compare all `_t()` literals and Python `_()` literals against `ar_001.po`, and that verify every explicit Arabic fallback key has a non-empty Arabic value.
7. Keep `Crystal Clean` untranslated intentionally.

## Success criteria
- Static missing frontend translation literals: 0.
- Static missing backend translation literals: 0, excluding escaped-regex false positives that are not real Python AST literals.
- No dynamic `_t(variable)` calls.
- Arabic fallback covers every module-owned frontend label used by `translateUi`.
- English mode returns source English text; Arabic mode returns Arabic for module-owned UI labels.
- Existing dashboards, reports, exports, and customer display behavior remain unchanged apart from localization.
