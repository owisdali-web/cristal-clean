# Validation — 18.0.6.8.1 Customer Lounge Polish

Fresh static validation adds coverage for:

- live Light/Dark theme synchronization on the customer screen;
- explicit customer-display Light and Dark palettes;
- stable featured-car rendering;
- larger lounge typography;
- additional Full Screen / TV Mode readability scaling;
- preservation of the V6.8 read-only customer-display contract.

---

# Validation — 18.0.6.8 Customer Lounge Display

Fresh source-tree verification completed before packaging:

- 79 static/visual/interaction/translation/customer-display contract tests: PASS
- Python compile (`models`, `controllers`, migration, tests): PASS
- XML/QWeb parse: PASS
- JavaScript syntax (`node --check`): PASS
- Manifest asset existence: PASS (9/9)
- Customer display is read-only and reuses `get_dashboard_data()` payload
- Featured rotation interval: 120000 ms
- Ready-priority path: present
- Fullscreen/TV mode path: present
- Existing Operations/Analytics selectors were not replaced; new visual CSS is scoped to customer display/navigation classes

A fresh extracted-ZIP verification is required before delivery and is recorded in the assistant delivery note.

Odoo Registry/browser runtime remains a staging verification step after module Upgrade.
