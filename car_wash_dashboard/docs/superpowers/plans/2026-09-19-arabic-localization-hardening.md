# Arabic Localization Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guarantee complete module-owned Arabic UI localization when the Odoo user language is Arabic while preserving existing English behavior.

**Architecture:** Retain Odoo `_t()` / `_()` as primary translation and add an Arabic-only deterministic frontend fallback sourced from the same catalog. Audit all module-owned visible literals and route dynamic labels through `tr()`.

**Tech Stack:** Odoo 18 Enterprise, OWL/QWeb, JavaScript, Python, GNU gettext PO, unittest static contract tests.

**Spec:** `docs/superpowers/specs/2026-09-19-arabic-localization-hardening-design.md`

## Global Constraints
- Odoo 18 manifest version must match `18.0.x.y.z` maximum format.
- Crystal Clean branding remains untranslated.
- Stored business data is never translated by the UI localization layer.
- No separate language selector.
- No database mutation in localization code.

## Review Focus
- Arabic user with stale frontend translation cache still gets Arabic module labels.
- English users never receive fallback Arabic.
- Dynamic status labels are translated; customer/service/station stored names are not altered.
- New frontend/backend labels cannot ship without Arabic catalog entries.
- RTL applies only when Arabic/Odoo direction requires it.

---

### Task 1: Runtime-safe frontend translation helper

**Files:**
- Modify: `static/src/js/ui_translations.js`
- Test: `tests/test_v696_arabic_runtime_hardening.py`

**Interfaces:**
- Consumes: Odoo `_t(source)` and `document.documentElement.lang/dir`.
- Produces: `translateUi(text)` returning Arabic only when active Odoo/browser language is Arabic; English otherwise.

- [ ] Write a failing static contract test for an explicit Arabic fallback map and Arabic-language detection.
- [ ] Run only the new test and verify RED because the fallback map does not exist.
- [ ] Add `AR_UI_TRANSLATIONS`, `isArabicUi()`, and fallback behavior while keeping `_t()` primary.
- [ ] Run the test and verify GREEN.

### Task 2: Catalog and dynamic-label completeness

**Files:**
- Modify: `i18n/ar_001.po`
- Modify as needed: `static/src/xml/dashboard.xml`, `static/src/js/dashboard.js`, component JS files
- Test: `tests/test_v696_arabic_runtime_hardening.py`

**Interfaces:**
- Consumes: all `_t("literal")` and visible `tr("literal")` labels.
- Produces: complete Arabic catalog and no unlocalized module-owned visible labels.

- [ ] Add failing tests that AST/regex-scan frontend labels and assert Arabic entries/fallback values exist.
- [ ] Verify RED on intentionally uncovered labels if any.
- [ ] Add/fix Arabic translations and route dynamic statuses through `tr()`.
- [ ] Verify GREEN and no dynamic `_t(variable)`.

### Task 3: Backend/export translation contract

**Files:**
- Modify as needed: `models/business_analytics.py`, `models/report_center.py`, `controllers/reports.py`, `i18n/ar_001.po`
- Test: `tests/test_v696_arabic_runtime_hardening.py`

**Interfaces:**
- Consumes: Python `_()` literals used for backend payload copy and report exports.
- Produces: all backend-owned labels catalogued for Arabic; stored data untouched.

- [ ] Write AST-based failing test for real Python `_()` literal calls missing from PO.
- [ ] Verify RED if missing entries exist.
- [ ] Add translations/fix literal escaping without translating stored record values.
- [ ] Verify GREEN.

### Task 4: Localization regression suite

**Files:**
- Modify: `__manifest__.py`
- Modify legacy version-only tests to accept the new patch version without weakening functional assertions.
- Test: full static suite excluding Odoo-runtime-only `test_dashboard.py`.

**Interfaces:**
- Produces: versioned localization-hardened base for Customers 360.

- [ ] Bump to valid Odoo version `18.0.6.9.6` only after localization tests are green.
- [ ] Run Python compile, XML parse, JS syntax, PO integrity, and full static tests.
- [ ] Record exact results before moving to Customers 360.
