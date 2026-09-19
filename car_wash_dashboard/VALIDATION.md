# Validation — 18.0.6.9.10

Validation performed outside an Odoo registry before packaging:

- OWL template global-constructor regression: PASS
- Unified frontend translation gateway contract: PASS
- Odoo RTL / Arabic runtime fallback detection: PASS
- Arabic/English translation runtime simulation: PASS
- Frontend PO `odoo-javascript` scope contract: PASS
- Versioned static/regression suite: PASS
- Python source syntax/AST: PASS
- XML/QWeb parse: PASS
- JavaScript syntax: PASS
- Manifest asset existence: PASS
- Invalid translation occurrence check: PASS

Runtime verification is still required on Odoo.sh Staging after Upgrade. Hard-refresh once after the upgrade so the rebuilt assets and frontend translations are loaded.

---

# Validation — 18.0.6.9.8

Validation performed outside an Odoo registry before packaging:

- Translation occurrence regression: PASS
- Versioned static/regression test suite: PASS
- Python source syntax compile/AST: PASS
- XML/QWeb parse: PASS
- JavaScript syntax: PASS
- Manifest asset existence: PASS
- Arabic PO coverage/integrity: PASS
- No `model:ir.module.module,description:*` occurrence remains.
- Customers 360 contracts from 18.0.6.9.7 remain covered.

Runtime verification is still required on Odoo.sh Staging after Upgrade.

---

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
