# 18.0.6.9.5 — Full Arabic / English Localization

## Language behavior

- The dashboard follows the active Odoo user language; there is no separate dashboard language preference.
- English users keep the existing English/LTR interface.
- Arabic users receive Arabic UI copy and RTL layout across Dashboard, Analytics, Reports, Customer Display, drill-downs, feedback messages, filters, and dashboard configuration labels.
- Crystal Clean branding and logo assets remain unchanged.

## Translation hardening

- Expanded `ar_001.po` to cover all current frontend `_t()`/`tr()` literals and backend/export translation literals.
- Report Excel, PDF, and Print labels now use the Odoo language context; Arabic Excel sheets use right-to-left worksheet mode.
- Analytics dynamic detail labels and status text are routed through Odoo translation helpers.
- RTL detection additionally recognizes an Arabic HTML language code, while preserving Odoo `dir=rtl` / `o_rtl` detection.
- Custom station/menu/field labels used by this addon are included in the Arabic catalog.

## Regression protection

- Added localization contract tests for frontend strings, backend/export strings, Arabic direction, report export RTL support, and custom Odoo field/view labels.
- Translation PO integrity rules remain enforced: every entry carries `#. module: car_wash_dashboard`, with no duplicate or empty entries.

## Preserved behavior

- No POS/MRP/stock/accounting workflow was changed by this release.
- Dashboard, dynamic Work Centers, Analytics, Reports interactions, Customer Display, Light/Dark mode, and export data logic are preserved.

---

# 18.0.6.9.3 — Interactive Management Reports

## Reports interface

- Report Center cards, revenue bars, service/payment legends, station rows, customer rows, supply rows, and exception rows now support in-page drill-down.
- Drill-down results stay inside Reports and can open the underlying Odoo record when a source record is available.
- Print no longer prints the dashboard chrome. It opens a dedicated, clean A4 landscape print view using the active filters.
- PDF and Excel exports use the exact same active Report Center filters and paid POS orders remain the official revenue source.
- Export actions now show a preparing state, download through a controlled request, and show success/error feedback instead of behaving like passive links.

## Excel — Management Workbook

The Excel export is now a multi-sheet management workbook:

- Executive Summary
- Operations
- Revenue & Payments
- Services
- Stations
- Customers
- Supplies
- Exceptions

It includes Crystal Clean branding, report period, generated-by/time metadata, applied filters, management highlights, freeze panes, filters, professional widths/formats, conditional formatting, totals, and management charts where appropriate.

## PDF — Management Report

- Multi-page Crystal Clean management report.
- Executive Summary, Revenue & Payments, Wash Operations, Service Performance, Station Performance, Top Customers, and Supplies & Exceptions sections.
- Header/footer metadata and page numbering.
- Full operation output with ReportLab pagination; the old 35-operation truncation is removed.

## Data contract

- Report revenue is calculated from paid/done/invoiced POS orders for car-wash service products.
- The backend now exposes transaction-level POS data and source model/record identifiers needed for drill-down.
- Report-period filters remain the single source for screen, print, PDF, and Excel outputs.

## Preserved behavior

- Dashboard, Analytics, Customer Display, dynamic Work Centers, POS/MRP operation flow, stock, and accounting logic are unchanged by this release.

## Preserved routing guarantees

- Each car-wash service remains designed to produce **one active Work Order** for the current operation flow.
- Upgrade/migration logic does not delete historical MRP production or Work Order history; inactive legacy routing records remain preserved.
