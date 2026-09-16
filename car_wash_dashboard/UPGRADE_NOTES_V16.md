# Crystal Clean 18.0.16.0 — Operational Intelligence

Backend-only release. No visual redesign is included.

## Added
- `get_operational_intelligence_data()` read-only API.
- Running Work Order elapsed/remaining/over-expected metrics.
- Per-station queue aging and deterministic ETA projection.
- Per-station throughput: completed today and rolling last 60 minutes.
- Per-station average actual/expected duration for completed work today.
- Global delayed-running count, maximum queue age and projected system clearance.
- Explicit reliability flag: ETA is suppressed for an over-capacity station rather than reporting a misleading number.

## Safety
- No Work Order reassignment.
- No automatic station routing.
- No state transitions.
- No POS, Stock, Accounting or MRP business-logic changes.
- V15 operations APIs are retained unchanged for compatibility.
