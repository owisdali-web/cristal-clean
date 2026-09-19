# Validation — 18.0.6.9.5

Validation performed outside an Odoo registry before packaging:

- Versioned static/regression test suite: PASS
- Python source syntax compile: PASS
- XML/QWeb parse: PASS
- JavaScript syntax: PASS
- Manifest asset existence: PASS
- Arabic PO integrity: PASS (no duplicate msgids, no missing module comments, no empty translations)
- Frontend translation coverage contract: PASS
- Backend/analytics/export translation coverage contract: PASS
- Arabic/LTR direction contract: PASS
- Report Excel RTL/localized-label contract: PASS
- Report PDF/Print localized-label and RTL-direction contract: PASS

Runtime verification is still required on Odoo.sh Staging after Upgrade. Test with one English user and one Arabic user, and hard-refresh the web client after the module upgrade so the updated translation assets are loaded.
