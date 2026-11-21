# GENOVEX: PHASE 14 API INTEGRATION SPECIFICATION
## Unified `/api/v1/` Architecture, Endpoints Inventory, Error Contracts & Frontend Client Integration

**Platform:** GENOVEX Male Reproductive Health Platform  
**Phase:** Phase 14 – Database & Unified API Integration  
**Backend Framework:** FastAPI 0.110+ (ASGI)  
**Frontend Framework:** Next.js 14+ (App Router)  

---

## 1. Unified API Architecture & Router Organization

All platform endpoints are strictly organized and unified under the canonical versioned prefix:
`/api/v1/`

Top-level unversioned endpoints are restricted strictly to operational health and diagnostic probes:
- `GET /health`: Operational health check returning platform status and regional deployment context (`market: "UAE"`).

### 1.1 API Router Registration Map

In `backend/main.py`, routers are partitioned by bounded domain context:

| Router Module | Mount Prefix | Tags / Domain | Authentication / RBAC Scope |
|---|---|---|---|
| `auth.py` | `/api/v1/auth` | Authentication & User Accounts | Public registration/login; Bearer token for profile/password. |
| `questionnaire.py` | `/api/v1/questionnaire` | Adaptive Questionnaire Engine | Public guest token or authenticated patient sessions. |
| `assessment_evaluation.py` | `/api/v1/assessment` | Clinical Evaluation Engine & Claiming | Guest token evaluation & account claiming. |
| `reports.py` | `/api/v1` (`/assessments`, `/reports`) | Formal Reports, Verification & History | Patient ownership, public token verification, expiring clinician share. |
| `clinical_navigation.py` | `/api/v1/navigation` | Clinical Navigation & UAE Directory | Public facilities directory & search; Admin write access. |
| `admin_dashboard.py` | `/api/v1/admin` | Platform Operational Metrics & Users | `ADMIN`, `SUPERADMIN` roles required. |
| `admin_clinical_rules.py` | `/api/v1/admin/rules` | Clinical Rule Engine CMS | `ADMIN`, `SUPERADMIN` roles required. |
| `admin_medical_content.py` | `/api/v1/admin/medical-content` | Evidence-Based Clinical Content CMS | `ADMIN`, `SUPERADMIN` roles required. |
| `clinician.py` | `/api/v1/clinician` | Clinician Portal & Secondary Review | `CLINICIAN`, `ADMIN` roles required. |

---

## 2. Comprehensive Endpoint Catalog

### 2.1 Authentication & Identity (`/api/v1/auth`)
- `POST /api/v1/auth/register`: Register new patient or clinician account.
- `POST /api/v1/auth/login`: Authenticate with email/password; returns signed JWT.
- `GET /api/v1/auth/me`: Retrieve profile of currently authenticated user.
- `PUT /api/v1/auth/me`: Update profile fields (`full_name`, `credentials_summary`).
- `POST /api/v1/auth/change-password`: Rotate user password with current password verification and NIST complexity validation.

### 2.2 Questionnaire Engine (`/api/v1/questionnaire`)
- `GET /api/v1/questionnaire/active`: Fetch active questionnaire version and domain structure.
- `POST /api/v1/questionnaire/sessions`: Start new assessment session (guest or authenticated).
- `GET /api/v1/questionnaire/sessions/{session_token}`: Fetch assessment state and saved answers.
- `POST /api/v1/questionnaire/sessions/{session_token}/answers`: Submit or update answers for specific questions.
- `POST /api/v1/questionnaire/sessions/{session_token}/complete`: Transition assessment status to `SUBMITTED`.

### 2.3 Evaluation & Reports (`/api/v1/assessment` & `/api/v1/reports`)
- `POST /api/v1/assessment/{session_token}/evaluate`: Run deterministic clinical rule engine on submitted assessment.
- `POST /api/v1/assessment/{session_token}/claim`: Bind guest assessment session to authenticated user account.
- `GET /api/v1/assessment/{session_token}/report`: Retrieve compiled assessment report data.
- `GET /api/v1/assessments/history`: Paginated assessment history for authenticated patient.
- `GET /api/v1/assessments/compare`: Compare outcomes between two historical assessments.
- `GET /api/v1/assessments/{assessment_id}`: Retrieve metadata for specific assessment.
- `GET /api/v1/reports/{report_reference}/verify`: Public verification of report authenticity.
- `POST /api/v1/reports/{report_reference}/share`: Generate secure expiring share link for clinician.
- `POST /api/v1/reports/{report_reference}/revoke-share`: Instantly revoke active share link.
- `GET /api/v1/reports/{report_reference}/download`: Download official evidence-linked PDF report.
- `GET /api/v1/reports/shared/{share_token}`: Access report via secure clinician share token.

### 2.4 Clinical Navigation & UAE Directory (`/api/v1/navigation`)
- `GET /api/v1/navigation/facilities`: Public directory of UAE healthcare facilities with filters (Emirate, specialty, 24/7 emergency).
- `GET /api/v1/navigation/facilities/{identifier}`: Detailed facility profile by slug or integer ID.
- `GET /api/v1/navigation/recommendations/{session_token_or_ref}`: Matched healthcare facilities based on assessment outcome tier.
- `POST /api/v1/navigation/facilities`: Admin creation of new licensed UAE facility.
- `PUT /api/v1/navigation/facilities/{facility_id}`: Admin update of facility details.

### 2.5 Admin Operations (`/api/v1/admin`)
- `GET /api/v1/admin/overview`: Platform metrics, user role counts, assessment breakdown.
- `GET /api/v1/admin/users`: User directory with search, filter, and pagination.
- `GET /api/v1/admin/users/{user_id}`: User profile, assessment count, audit logs.
- `PATCH /api/v1/admin/users/{user_id}/status`: Activate or deactivate user.
- `PATCH /api/v1/admin/users/{user_id}/role`: Update user role (`PATIENT`, `CLINICIAN`, `ADMIN`).
- `GET /api/v1/admin/audit-events`: Paginated audit log search with date/action filters.
- `GET /api/v1/admin/config`: Safe platform environment configuration.

---

## 3. Standardized HTTP Status Codes & Error Contracts

All endpoints return predictable, standardized HTTP status codes:

| Code | Status | Usage / Trigger Condition |
|---|---|---|
| **200** | `OK` | Successful GET, PUT, PATCH, or non-creation POST. |
| **201** | `Created` | Successful entity creation (e.g., user registration, facility creation). |
| **400** | `Bad Request` | Business rule violations (e.g. invalid current password, incomplete answers). |
| **401** | `Unauthorized` | Missing, expired, or invalid JWT Bearer token. |
| **403** | `Forbidden` | Role mismatch (e.g. Patient accessing Admin) or IDOR violation. |
| **404** | `Not Found` | Entity does not exist (e.g. invalid assessment ID, unknown facility slug). |
| **409** | `Conflict` | Resource conflict (e.g. email address already registered). |
| **422** | `Unprocessable Entity` | Pydantic schema validation failure (malformed body, missing required fields). |
| **429** | `Too Many Requests` | Rate limit threshold exceeded. |
| **500** | `Internal Server Error` | Unhandled server exception with sanitized error response. |

### 3.1 Sanitized Error Response Specification
Under no circumstances are raw Python tracebacks, internal database schema details, or Protected Health Information (PHI) leaked in error responses.

Standardized Error Structure:
```json
{
  "detail": "Descriptive, client-safe error message",
  "correlation_id": "optional-request-uuid"
}
```

---

## 4. Frontend API Client Integration (`frontend/lib/api.ts`)

The Next.js frontend interacts with the FastAPI backend through a unified API client architecture in `frontend/lib/api.ts`:

### 4.1 Dynamic Base URL Resolution
The API client dynamically resolves the backend URL, supporting multiple deployment environments:
```typescript
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000/api/v1";
```
- Local Development: defaults to `http://127.0.0.1:8000/api/v1`.
- Vercel / Cloud Staging: configured via `NEXT_PUBLIC_API_BASE_URL` environment variable.

### 4.2 Unified Token Injection & Handling
```typescript
function getAuthHeaders(token?: string): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  const activeToken = token || (typeof window !== "undefined" ? localStorage.getItem("genovex_token") : null);
  if (activeToken) {
    headers["Authorization"] = `Bearer ${activeToken}`;
  }
  return headers;
}
```

### 4.3 Resilience & Timeout Wrapper
All fetch operations are executed through `fetchWithTimeout()` with built-in retry and graceful error translation, ensuring the UI remains responsive even during intermittent network latency.
