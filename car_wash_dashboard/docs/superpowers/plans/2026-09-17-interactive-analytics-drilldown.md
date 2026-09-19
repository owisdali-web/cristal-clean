# Interactive Analytics Drill-down Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every meaningful Business Analytics KPI, chart segment, ranked row, supply row, and activity row clickable so it opens a contextual read-only drill-down panel inside the dashboard, with an optional action to open the original Odoo record.

**Architecture:** Keep the existing 18.0.6.5 analytics summary RPC unchanged in purpose, enrich aggregate rows with stable identifiers, and add one read-only RPC `get_business_analytics_detail(detail_type, key, period)` for on-demand drill-down data. The OWL client owns one analytics-detail state object and renders a right-side panel without mutating MRP, stock, POS, or accounting records.

**Tech Stack:** Odoo 18 Enterprise, Python ORM, OWL, QWeb XML, CSS.

**Spec:** Approved in-chat design: analytics page remains visually unchanged; clicks reveal only relevant information in an in-dashboard panel; records may be opened in standard Odoo views via an explicit secondary action.

## Global Constraints
- Odoo version: 18 Enterprise.
- Analytics interactions are read-only.
- Preserve existing operational dashboard behavior and Business Analytics visual layout.
- No create/write/unlink in analytics backend or frontend business actions.
- Keep audio/visual click feedback optional and non-blocking.

---

### Task 1: Backend drill-down contract
**Files:**
- Modify: `models/business_analytics.py`
- Test: `tests/test_v66_interactive_analytics.py`

**Interfaces:**
- Produces: `mrp.production.get_business_analytics_detail(detail_type, key=False, period='today') -> dict`
- Result fields: `detail_type`, `title`, `subtitle`, `summary`, `rows`.

- [ ] Write failing static contract tests for the method, identifiers, read-only behavior, and supported detail types.
- [ ] Run the test and verify RED.
- [ ] Implement helpers to serialize POS orders, work orders, customers, supplies, and activities into a common read-only row shape.
- [ ] Implement drill-down dispatch for revenue, washes, customers, service, station, supply, revenue bucket, customer mix, category, and recent activity.
- [ ] Re-run tests and verify GREEN.

### Task 2: OWL analytics detail state and event handlers
**Files:**
- Modify: `static/src/js/dashboard.js`
- Test: `tests/test_v66_interactive_analytics.py`

**Interfaces:**
- Consumes: `get_business_analytics_detail`.
- Produces: `openAnalyticsDetail(type, key, label)`, `closeAnalyticsDetail()`, `openAnalyticsRecord(row)`.

- [ ] Write failing tests for bound handlers, detail RPC, loading state, and record-opening action.
- [ ] Run test and verify RED.
- [ ] Add analytics detail state and bound callbacks.
- [ ] Add on-demand RPC loading, feedback tone, panel close, and supported model-to-action mapping.
- [ ] Re-run test and verify GREEN.

### Task 3: Clickable analytics visual contract
**Files:**
- Modify: `static/src/xml/dashboard.xml`
- Modify: `static/src/css/dashboard_concept_replica.css`
- Test: `tests/test_v66_interactive_analytics.py`

**Interfaces:**
- Consumes: `openAnalyticsDetail`, `analyticsDetail` state.
- Produces: interactive KPI/chart/list affordances and a side-panel drill-down.

- [ ] Write failing tests for clickable KPIs, line dots, service bars, station legend, customer rows, supply rows, revenue bars, customer mix, category legend, activity rows, and detail panel classes.
- [ ] Run test and verify RED.
- [ ] Add semantic buttons/click handlers without changing the visual hierarchy.
- [ ] Add right-side detail panel with summary, rows, loading/empty states, close button, and optional “Open in Odoo”.
- [ ] Add hover/focus styles and responsive panel behavior.
- [ ] Re-run test and verify GREEN.

### Task 4: Versioning, full verification, and package
**Files:**
- Modify: `__manifest__.py`
- Modify: `UPGRADE_NOTES.md`
- Modify: `VALIDATION.md`

- [ ] Update version to `18.0.6.6`.
- [ ] Run full Python unit/static suite.
- [ ] Compile Python, parse XML/QWeb, syntax-check all JavaScript, validate manifest assets, and scan analytics sources for business mutation calls.
- [ ] Build ZIP with one top-level `car_wash_dashboard/` directory.
- [ ] Extract ZIP into a fresh directory and repeat verification on the packaged artifact.
