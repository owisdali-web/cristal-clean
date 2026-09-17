# 18.0.6.9 — Crystal Clean Report Center

This release replaces the old Reports navigation (which opened a standard MRP list) with an in-dashboard Report Center matching the approved Crystal Clean visual concept.

## Added
- Reports page inside the existing dashboard client action; Dashboard, Analytics, and Customer Display are unchanged.
- Filter bar: period, custom date range, station, service, vehicle size, customer, and status.
- Report categories: Overview, Operations, Revenue, Services, Stations, Customers, Supplies, and Exceptions.
- Management KPIs: total cars, finished cars, waiting cars, official POS revenue, average ticket, and unique customers.
- Revenue trend, cars by service, payment methods, operations table, service performance, station performance, customer report, low-supply report, and exception report.
- Saved report presets for daily, monthly, revenue, station, customer, and inventory views.
- Print support using browser print CSS.
- Authenticated PDF export and Excel export using the same active report filters.

## Financial source of truth
Revenue is calculated only from paid/done/invoiced Point of Sale orders for products recognized as car-wash services. MRP is used for operational performance, timing, station utilization, and wash-order status.

## Upgrade
Upgrade the existing module in place. Do not uninstall it.

## Preserved operational contract
The routing design introduced in earlier releases remains unchanged: a car-wash service is expected to produce one active Work Order for the current routing flow. Historical operations are preserved; the module does not delete routing history and uses archival/retention behavior instead of deleting historical work orders.
