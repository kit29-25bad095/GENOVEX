# GENOVEX Future Development & Phase Integration Guidelines

## 1. Architectural Boundary Principles for Future Phases

As development continues across subsequent platform phases:
- **Phase 10:** Clinician Portal (Being developed by a dedicated team member)
- **Phase 11:** Comprehensive Admin Dashboard
- **Phase 12:** Clinical Navigation & UAE Clinic Referral Directory
- **Phase 13:** PDF Report Generation & Assessment History
- **Phase 14:** Production Database Migration (PostgreSQL / Managed RDS)
- **Phase 15:** Security Hardening & Penetration Testing
- **Phase 16:** CI/CD & Cloud Infrastructure Deployment (UAE Sovereign Region)
- **Phase 17:** Performance Optimization & Load Testing

All future module implementations must strictly adhere to the infrastructure and architectural standards established in Phase 18.

---

## 2. Integration Invariants for Remaining Phases

### 2.1 Clinician Portal (Phase 10) & Admin Dashboard (Phase 11) Integration
1. **RBAC Dependency Reuse:**
   - Always gate administrative and clinical routes with `require_roles([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])` or `require_roles([RoleEnum.CLINICIAN, RoleEnum.ADMIN, RoleEnum.SUPERADMIN])`.
   - Never rely on client-side role assertions or persona selectors for authorization.
2. **Maintenance Telemetry Consumption:**
   - The Admin Dashboard should directly consume:
     - `GET /api/v1/admin/health/diagnostics` for system health graphs.
     - `GET /api/v1/admin/maintenance/backups` for database snapshot management.
     - `GET /api/v1/admin/maintenance/clinical-assets` for review cycle alerts.
     - `GET /api/v1/admin/maintenance/ai-telemetry` for AI cost and circuit breaker status.

### 2.2 Clinical Navigation & Referral (Phase 12)
1. **Deterministic Specialty Mapping:**
   - Specialty recommendations must flow directly from the deterministic clinical rule outcome (e.g., Andrology for severe male factor, Urology for anatomical varicoceles/cryptorchidism, Reproductive Endocrinology for hormonal dysfunction).
   - Clinic listings in Dubai (DHA), Abu Dhabi (DOH), and Northern Emirates (MoHAP) must be verified against official health authority registries.

### 2.3 Database Migration to PostgreSQL (Phase 14)
1. **Schema Compatibility:**
   - Database models already use standard SQLAlchemy data types compatible with PostgreSQL.
   - Replace `sqlite3.backup` routines with `pg_dump` streaming or AWS RDS Automated Snapshots.
   - Maintain the same `BackupService` interface so administrative endpoints remain unchanged.

### 2.4 Sensitive Data Logging Prohibition
1. **No Log Leaks:**
   - When building Phase 13 (Report Generation) or Phase 10 (Clinician Portal), developers must never log generated PDF byte streams, patient questionnaire answers, or authentication tokens.
   - Always pass contextual objects through `sanitize_dict()` or rely on the centralized structured logger.
