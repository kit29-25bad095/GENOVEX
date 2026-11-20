# GENOVEX AI Service Reliability & Monitoring Specification

## 1. Role and Boundaries of AI in GENOVEX

In accordance with UAE digital health standards and clinical risk management protocols:
- **Non-Diagnostic Constraint:** AI/LLM components in GENOVEX are strictly supplementary. They generate bilingual conversational summaries, patient-friendly medical explanations, and translation enhancements.
- **Rule Engine Isolation:** AI systems **never** determine, modify, calculate, or override clinical risk tiers, referral recommendations, or urgent safety alerts. Those decisions are exclusively made by the deterministic clinical rule engine.

---

## 2. Operational Circuit Breaker Pattern

To shield the user experience from third-party LLM outages, rate limits (HTTP 429), or network timeouts, the platform implements an active, in-memory circuit breaker (`AIMonitoringService`):

```
       [ CLOSED ] ──( 3 Consecutive Failures )──> [ OPEN ]
           ▲                                          │
           │                                          │ (Cooldown: 60s)
           │                                          ▼
     (Probe Success) <── [ HALF_OPEN ] <──────────────┘
```

### 2.1 State Descriptions
1. **`CLOSED` (Normal Operation):**
   - Requests are dispatched to the AI provider.
   - Latency, token usage, and outcomes are tracked.
   - Consecutive failure counter resets to 0 upon every successful call.
2. **`OPEN` (Tripped / Safety Mode):**
   - Tripped automatically when failure counter reaches `AI_CIRCUIT_BREAKER_MAX_FAILURES` (Default: 3).
   - In this state, external network calls are bypassed entirely.
   - The system immediately returns pre-compiled, medically verified deterministic fallbacks.
   - Avoids compounding latency spikes or exhausting API quotas.
3. **`HALF_OPEN` (Trial Recovery):**
   - After `AI_CIRCUIT_BREAKER_COOLDOWN_SEC` (Default: 60s) in the `OPEN` state, the circuit transitions to `HALF_OPEN`.
   - A single probe request is permitted through to the external provider.
   - If the probe succeeds, the circuit resets to `CLOSED`. If it fails or times out, the circuit reverts to `OPEN` for another cooldown cycle.

---

## 3. Deterministic Safety Fallbacks

Every AI-assisted function provides a mandatory deterministic fallback function:
- **Report Explanation Fallback:** Returns standard, clinically verified narrative blocks keyed directly to the patient's deterministic outcome tier (Tier 1-4).
- **Arabic Translation Fallback:** Returns verified static Arabic translations for standard medical explanations.
- **User Guarantee:** The patient experiences zero disruption, zero 500 errors, and zero clinical compromise if the AI provider experiences complete downtime.

---

## 4. Telemetry Metrics & Monitoring API

The endpoint `GET /api/v1/admin/maintenance/ai-telemetry` provides administrative visibility into:
- Current circuit state (`CLOSED`, `OPEN`, `HALF_OPEN`)
- Total requests handled
- Total failures, timeouts, and rate limits encountered
- Moving average latency (`average_latency_ms`)
- Cumulative tokens consumed and estimated USD cost
- Administrative manual reset trigger (`POST /api/v1/admin/maintenance/ai-telemetry/reset`)
