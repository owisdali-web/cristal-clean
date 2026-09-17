# 18.0.6.7.2 Translation Bundle Validation

Validation targets for this release:

1. Manifest version is `18.0.6.7.2`.
2. `models/ir_http.py` inherits `ir.http` and overrides the Odoo 18 classmethod `_get_translation_frontend_modules_name()`.
3. The override preserves the parent module list and adds `car_wash_dashboard` once.
4. `models/__init__.py` imports the override so it is registered in the Odoo registry.
5. `i18n/ar_001.po` contains the missing lowercase `Station details` translation.
6. Existing OWL/JS, XML/QWeb, CSS, analytics, vehicle visual, interactivity, and RTL contracts continue to pass.
7. Third-party minified Chart.js is excluded from Odoo translation-source assumptions; its internal `_t(` token is unrelated to `@web/core/l10n/translation`.

Runtime verification still requires an Odoo 18 staging upgrade followed by the read-only Shell audit and a hard browser refresh under an Arabic user.

## Additional static translation hardening

- OWL template `tr(...)` literals are centralized in `static/src/js/ui_translations.js` as literal `_t("...")` calls so Odoo can extract them statically.
- Dashboard/component helpers no longer call `_t(variable)` dynamically.
- The unused bundled `Chart.js` minified file was removed; it was not referenced by the manifest or dashboard source and its internal `_t()` helper created a false positive in the translation audit.
- A runtime Odoo `TransactionCase` assertion now checks that `car_wash_dashboard` is returned by `ir.http._get_translation_frontend_modules_name()`.
