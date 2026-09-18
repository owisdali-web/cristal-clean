# Validation — 18.0.6.9.3

Validation performed outside an Odoo registry:

- 106 versioned static/regression tests across 15 non-registry test files: PASS
- Python source compile: PASS
- XML/QWeb parse: PASS (4 files)
- JavaScript syntax: PASS
- Manifest asset existence: PASS (9 assets)
- Arabic PO duplicate msgid scan: PASS (0 duplicates)
- XLSX export smoke test: PASS; valid Microsoft Excel 2007+ workbook produced
- XLSX workbook verification with artifact_tool: PASS; Executive Summary values inspected, formula-error scan returned 0 matches, key sheets rendered for visual review
- PDF export smoke test: PASS; valid 7-page PDF produced
- PDF render verification: PASS; all 7 pages rendered to images and key pages visually inspected for clipping/layout
- Dedicated print-view smoke test: PASS; standalone print HTML produced
- Export package/source scan: no 35-operation PDF truncation contract remains

Runtime Odoo registry/browser verification is still required on Staging after module Upgrade, including live RPC drill-down and browser download/print behavior.
