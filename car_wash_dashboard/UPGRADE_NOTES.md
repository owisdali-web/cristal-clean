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
