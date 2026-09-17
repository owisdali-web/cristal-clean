# Validation — 18.0.6.9.1 Report Center Runtime Hotfix

Validated in the build workspace:
- 94 static/regression tests passed (Odoo-runtime test module excluded from local non-Odoo runner).
- Dedicated v6.9.1 regression verifies the invalid relational `order_id.date_order` SQL ordering is absent and Python chronological sorting is present.
- Python source syntax compilation passed.
- OWL/QWeb XML parsing passed.
- JavaScript syntax checks passed.
- Manifest asset paths validated.
- ZIP cleanliness check excludes `__pycache__` and `.pyc`.

The exact Odoo 18 runtime failure was independently reproduced by the staging shell before this hotfix. Final registry/RPC verification must still be performed after upgrading 18.0.6.9.1 on Staging.
