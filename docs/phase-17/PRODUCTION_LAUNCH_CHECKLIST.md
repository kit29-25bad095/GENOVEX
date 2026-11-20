# GENOVEX — Production Launch Readiness Checklist

## 1. Executive Go / No-Go Decision Framework

Before deploying GENOVEX to live production in the UAE healthcare market, every item in this checklist must be validated and signed off by the designated technical and clinical leads.

**CRITICAL SAFEGUARD:** This checklist confirms deployment preparedness only. The platform must **NOT** be launched to real patients or clinicians until upcoming phases (Phase 11: Admin Dashboard, Phase 12: Clinical Navigation, Phase 14: Database & API Integration, Phase 15: Security & Regulatory, Phase 16: Testing & Clinical Validation) are completed.

---

## 2. Multi-Domain Verification Checklist

### Category A: Infrastructure, Cloud & Data Sovereignty
- [ ] **UAE Data Residency Verified:** All compute (ECS tasks), databases (persistent storage/RDS), and backups reside strictly within AWS UAE (`me-central-1` Dubai) or Azure UAE North.
- [ ] **Zero Data Egress:** Verified that no health data, IP addresses, or assessment logs egress to servers outside the United Arab Emirates.
- [ ] **Multi-AZ High Availability:** Production load balancers and container tasks deployed across at least 2 distinct Availability Zones.
- [ ] **Auto-Scaling Operational:** CPU and memory scaling policies verified under simulated stress (target: 70% threshold).
- [ ] **Non-Root Container Enforcement:** Frontend (`nextjs:1001`) and backend (`genovex:1001`) run without root privileges.

### Category B: Security, Authentication & Cryptography
- [ ] **Zero Hardcoded Secrets in Git:** Verified that all repository files are free of plaintext secrets, API keys, and passwords.
- [ ] **Production Secret Key Entropy:** `SECRET_KEY` generated with high-entropy cryptographic randomness (>= 64 chars, 256-bit entropy).
- [ ] **Simulated Persona Auth Hard Disabled:** `ALLOW_SIMULATED_AUTH=False` strictly enforced in production configuration.
- [ ] **Debug Mode Hard Disabled:** `DEBUG=False` verified; application code fails closed and crashes on startup if `DEBUG=True` in production.
- [ ] **CORS Origin Lockdown:** Only verified production HTTPS domains (`https://genovex.ae`, `https://app.genovex.ae`) allowed; `localhost` unconditionally rejected.
- [ ] **Edge TLS 1.3 Strict & HSTS:** HSTS configured with `max-age=63072000; includeSubDomains; preload`; TLS 1.0/1.1 disabled.
- [ ] **Security Headers Active:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` active.

### Category C: Clinical Safety, Determinism & Content Governance
- [ ] **Clinical Determinism Intact:** Deterministic rule engine operates independently of AI; verified that AI never overrides clinical rules or changes risk outcome tiers.
- [ ] **Non-Diagnostic Medical Framing:** All UI text, assessment outcome reports, and summaries strictly adhere to informational/risk-identification framing. No diagnostic or prescriptive therapy claims.
- [ ] **Bilingual Equivalence Verified:** All 11 questionnaire domains, questions, options, and clinical rationales verified for semantic equivalence in English and Arabic.
- [ ] **Medical Content Publication Gate:** Only medically reviewed and approved content versions are visible to the public or patient users.
- [ ] **AI Safety Boundaries Active:** Input length limited to 2000 chars, output schema strictly constrained, AI circuit breaker active with fallback to deterministic text.

### Category D: Observability, Logging & Disaster Recovery
- [ ] **Health Probes Operational:** `/health/live`, `/health/ready`, and `/health/detailed` responding with expected payloads and status codes.
- [ ] **Correlation ID Propagation:** `X-Correlation-ID` header emitted on 100% of responses and logged with structured JSON context.
- [ ] **Patient Data Redacted from Logs:** Verified that passwords, emails, names, and questionnaire answers are never written to log streams.
- [ ] **Automated Backup Engine Active:** Background maintenance scheduler verified; automated daily backups running with SHA-256 integrity checks.
- [ ] **Off-Site Backup Replication:** Verified that backup snapshots replicate to encrypted S3 bucket in `me-central-1` with 30-day retention.
- [ ] **Disaster Recovery Tested:** Database restoration runbook successfully executed and verified against a test database instance.

### Category E: Legal, Regulatory & Intellectual Property
- [ ] **UAE PDPL Compliance Review:** Patient consent mechanism and privacy notice comply with Federal Decree-Law No. 45.
- [ ] **Health Data Law Review:** Data retention and access logging comply with Federal Law No. 2 of 2019.
- [ ] **Intellectual Property & Third-Party Licensing Page:** Component (`frontend/components/intellectual-property-licensing.tsx`) and page (`/licensing`) active and accessible via footer.

---

## 3. Go / No-Go Sign-Off Matrix

| Sign-Off Role | Name & Title | Decision (GO / NO-GO) | Date & Signature |
| :--- | :--- | :--- | :--- |
| **Lead DevOps / Cloud Architect** | Principal DevOps Lead | PENDING REVIEW | |
| **Principal Security Architect** | Head of Cybersecurity | PENDING REVIEW | |
| **Medical Director / Clinical Lead** | Chief Medical Officer | PENDING REVIEW | |
| **Legal & Compliance Counsel** | UAE Healthcare Legal Counsel | PENDING REVIEW | |
| **Product & Project Sponsor** | GENOVEX Project Sponsor | PENDING REVIEW | |
