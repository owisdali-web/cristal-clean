# Customer Lounge Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Live Car Journey TV page under Customers using the existing dashboard payload.

**Architecture:** Extend the existing OWL client action with a third page state (`customer_display`). Derive the four customer-facing stages entirely from the current dashboard payload and render them with page-scoped CSS; use the browser Fullscreen API for TV mode and the existing bus/polling refresh path for live updates.

**Tech Stack:** Odoo 18 Enterprise, OWL/QWeb, JavaScript, CSS, Python unittest contract tests.

**Spec:** `docs/superpowers/specs/2026-09-17-customer-lounge-display-design.md`

## Global Constraints
- Do not change the existing Operations or Analytics visual design.
- Do not create/write/unlink POS, MRP, Stock, Account, or Partner records from the customer page.
- Featured vehicle rotation interval is exactly 120000 ms (2 minutes).
- Ready vehicles take featured priority.
- Full-screen mode is browser-local and requires no server persistence.

---

### Task 1: Customer sidebar navigation
**Files:** `static/src/xml/dashboard.xml`, `static/src/js/dashboard.js`, `tests/test_v68_customer_lounge_display.py`
- [x] Add failing contract test for nested Customers navigation.
- [x] Add `customer_display` page state and bound `showCustomerDisplay` handler.
- [x] Add Live Car Journey child button under Customers.
- [x] Run contract test.

### Task 2: Live journey data projection
**Files:** `static/src/js/dashboard.js`, `tests/test_v68_customer_lounge_display.py`
- [x] Add failing contract tests for four stages, ETA, rotation, and ready priority.
- [x] Derive Waiting/Washing/Finishing/Ready from existing dashboard payload.
- [x] Add ticket/ETA/progress/journey helper functions.
- [x] Add 120-second featured rotation and new-ready priority behavior.
- [x] Run contract test.

### Task 3: Customer TV interface
**Files:** `static/src/xml/dashboard.xml`, `static/src/css/dashboard_concept_replica.css`, `tests/test_v68_customer_lounge_display.py`
- [x] Add failing contract test for customer display visual shell and Fullscreen API.
- [x] Add featured-car hero, four stage columns, idle state, footer, and TV button.
- [x] Add page-scoped responsive and fullscreen CSS.
- [x] Run contract test.

### Task 4: Translation/catalog coverage
**Files:** `static/src/js/ui_translations.js`, `i18n/ar_001.po`
- [x] Add all new customer-facing literals to runtime translation catalog.
- [x] Add Arabic translations for new literals.
- [x] Run existing full-Arabic/static translation contract tests.

### Task 5: Regression verification and packaging
**Files:** `__manifest__.py`, `UPGRADE_NOTES.md`, `VALIDATION.md`
- [x] Bump version to 18.0.6.8.
- [x] Run Python compile, XML parse, JS syntax, static contracts, asset validation, and ZIP re-extraction verification.
- [x] Package `car_wash_dashboard_18.0.6.8_customer_lounge_display.zip`.
