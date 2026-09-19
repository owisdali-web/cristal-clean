# Car Wash Business Analytics Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the approved CleanDrive Business Analytics page to the existing Odoo 18 car-wash dashboard with real POS/MRP/stock data and no business-record mutations.

**Architecture:** Extend `mrp.production` with a read-only analytics RPC that aggregates POS, MRP, work-center, customer, and stock data into one stable payload. Extend the existing OWL client action with an `analytics` page state and a dedicated QWeb section rendered with CSS/SVG-based charts so no new runtime JS chart dependency is required.

**Tech Stack:** Odoo 18 ORM, OWL/QWeb, JavaScript, CSS, Python, POS, MRP, Stock.

**Spec:** `docs/superpowers/specs/2026-09-17-business-analytics-dashboard-design.md`

## Global Constraints
- Target Odoo version: 18 Enterprise.
- Operational dashboard remains the default page and must not regress.
- Analytics is read-only and must not mutate MRP, stock, POS, accounting, or customer records.
- User timezone drives day/month boundaries.
- No invented financial, inventory, or utilization data.
- Visual structure follows the approved CleanDrive analytics concept.

---

### Task 1: Analytics backend contract

**Files:**
- Create: `models/business_analytics.py`
- Modify: `models/__init__.py`
- Modify: `__manifest__.py`
- Test: `tests/test_v65_business_analytics.py`

**Interfaces:**
- Produces: `mrp.production.get_business_analytics_data(period='today') -> dict` with keys `period`, `kpis`, `daily_washes`, `popular_services`, `station_utilization`, `top_customers`, `low_supplies`, `revenue_trend`, `customer_mix`, `revenue_by_category`, `recent_activity`.

- [ ] Write a failing static contract test asserting version `18.0.6.5`, `point_of_sale` dependency, new model import, RPC name, required payload keys, timezone helpers, and no create/write/unlink calls in the analytics file.
- [ ] Run the test and confirm it fails because the new backend does not exist.
- [ ] Implement the analytics aggregation in `models/business_analytics.py` using read-only ORM searches/read_group and timezone-aware period helpers.
- [ ] Run the test and existing pure-Python tests.

### Task 2: Analytics page state and navigation

**Files:**
- Modify: `static/src/js/dashboard.js`
- Modify: `static/src/xml/dashboard.xml`
- Test: `tests/test_v65_business_analytics.py`

**Interfaces:**
- Consumes: `get_business_analytics_data(period)`.
- Produces: `state.page`, `state.analyticsPeriod`, `state.analytics`, `showAnalytics()`, `showOperations()`, `setAnalyticsPeriod(period)`, chart helper getters/styles.

- [ ] Add failing assertions for sidebar Analytics navigation, analytics state, RPC call, period selector, and required template card titles.
- [ ] Run the test and confirm failure.
- [ ] Implement analytics fetching/navigation with bound callbacks and isolated error handling.
- [ ] Render the approved analytics card structure in QWeb.
- [ ] Run contract tests and JS syntax checks.

### Task 3: Exact visual treatment and responsive charts

**Files:**
- Modify: `static/src/css/dashboard_concept_replica.css`
- Test: `tests/test_v65_business_analytics.py`

**Interfaces:**
- Consumes analytics QWeb classes.
- Produces responsive KPI grid, chart cards, SVG line chart, CSS bars, donut rings, ranked lists, and activity feed.

- [ ] Add failing CSS contract assertions for analytics page/card/grid/chart/list/donut classes.
- [ ] Run test and confirm failure.
- [ ] Implement CSS matching the approved white/blue CleanDrive concept and responsive behavior.
- [ ] Run tests and inspect generated static structure.

### Task 4: Regression and packaging

**Files:**
- Modify: `UPGRADE_NOTES.md`
- Modify: `VALIDATION.md`
- Package: `car_wash_dashboard_18.0.6.5_business_analytics.zip`

- [ ] Run all repository tests.
- [ ] Run Python compile checks.
- [ ] Parse XML/QWeb files.
- [ ] Run JavaScript syntax checks.
- [ ] Verify manifest asset paths and ZIP root structure.
- [ ] Re-extract the final ZIP and rerun the tests against the extracted artifact.
