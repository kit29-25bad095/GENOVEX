# GENOVEX — PHASE 15: SECURITY & PRIVACY INCIDENT RESPONSE PLAN
## Protocols for Detection, Containment, Eradication, and UAE Regulatory Breach Notification

### 1. Purpose & Scope
This Incident Response Plan (IRP) defines the mandatory technical and organizational procedures for identifying, triaging, containing, and reporting security incidents and personal data breaches within the GENOVEX healthcare platform.

The plan covers all components of GENOVEX:
- Patient and anonymous assessment endpoints.
- Clinician Decision Support Portal.
- Admin Medical Content Management System.
- Primary Database (SQLite/PostgreSQL) and automated backup repositories.
- Cloud hosting compute, edge rewrites, and external AI integrations.

---

### 2. Incident Classification & Severity Levels

| Severity Tier | Definition / Criteria | Incident Examples | Maximum Containment SLA | Regulatory Notification SLA |
|---|---|---|:---:|:---:|
| **SEV-1: CRITICAL** | Confirmed unauthorized exfiltration or exposure of sensitive reproductive health data (PHI), database credential compromise, or active ransomware attack. | Exfiltration of `assessment_reports` table; compromise of production `SECRET_KEY` or master DB credentials. | **< 2 Hours** | **Immediate (< 72 Hours to UAE Authorities)** |
| **SEV-2: HIGH** | Compromise of administrative or clinician account credentials without verified broad database dump; systemic service denial (DoS). | Clinician account takeover; widespread brute-force attack causing application downtime. | **< 4 Hours** | **Assessment within 24 Hours** |
| **SEV-3: MEDIUM** | Isolated failure of security controls, unauthorized attempt to modify clinical rules blocked by audit gate, localized rate limit abuse. | Blocked SQL injection probe; abnormal volume of failed login attempts from a single IP subnet. | **< 12 Hours** | **Internal incident log only** |
| **SEV-4: LOW** | Informational security event, minor misconfiguration without vulnerability exposure, deprecated dependency alert. | Outdated npm package alert without active exploit vector; scanner pinging non-existent endpoints. | **< 48 Hours** | **Internal tracking** |

---

### 3. Incident Response Lifecycle Phases

```
+---------------------------------------------------------------------------------------+
|                               INCIDENT RESPONSE LIFECYCLE                             |
+---------------------------------------------------------------------------------------+
|  1. IDENTIFICATION & TRIAGE                                                           |
|     - Alert ingestion via automated logging, Sentry error tracker, or user report.    |
|     - Incident Commander (IC) designated; severity classification assigned.           |
|                                                                                       |
|  2. CONTAINMENT & ISOLATION                                                           |
|     - Short-Term: Session invalidation, IP blocking, API key rotation, worker drain.   |
|     - Long-Term: Database connection isolation, firewall rule tightening.            |
|                                                                                       |
|  3. EVIDENCE PRESERVATION & FORENSICS                                                 |
|     - Snapshot immutable audit logs (`audit_logs`), correlation ID request trails.    |
|     - Preserve forensic memory and disk snapshots without altering metadata.          |
|                                                                                       |
|  4. ERADICATION & REMEDIATION                                                         |
|     - Patch vulnerable code paths; rotate all active JWT signing secrets.             |
|     - Restore verified clean database snapshot if tampering occurred.                 |
|                                                                                       |
|  5. RECOVERY & RESTORATION                                                            |
|     - Phased re-enabling of services; enhanced monitoring for 72 hours.               |
|                                                                                       |
|  6. POST-INCIDENT REVIEW & REGULATORY NOTIFICATION                                    |
|     - File formal breach notification with UAE Data Office, MOHAP, DHA, and DoH.      |
|     - Publish comprehensive root-cause analysis (RCA) and mitigation backlog.         |
+---------------------------------------------------------------------------------------+
```

---

### 4. UAE Regulatory Breach Notification Protocols

Under **UAE Federal Decree-Law No. 45 of 2021 (PDPL) Article 26** and **Federal Law No. 2 of 2019 (Health Data Law)**, if a personal data breach occurs that presents a risk to the privacy or confidentiality of data subjects, mandatory notification timelines must be strictly observed.

#### 4.1 Notification to UAE Data Office & Healthcare Regulators
- **Notification Timeline:** Within **72 hours** of becoming aware of a confirmed data breach involving personal data.
- **Regulatory Contacts:**
  - UAE Data Office (Federal Level)
  - Ministry of Health and Prevention (MOHAP) Information Security Department
  - Dubai Health Authority (DHA) Health Informatics Section
  - Department of Health Abu Dhabi (DoH) Digital Health Division
- **Mandatory Notification Content:**
  1. Nature and categories of compromised data (e.g., pseudonymous reproductive assessment records, clinician credentials).
  2. Approximate number of data subjects affected.
  3. Identity and contact details of the Data Protection Officer (DPO).
  4. Likely consequences and clinical privacy impact of the breach.
  5. Measures taken or proposed to contain, remediate, and mitigate potential adverse effects.

#### 4.2 Notification to Affected Data Subjects
- Where a breach poses a high risk to individual confidentiality, GENOVEX shall notify affected registered users without undue delay via registered email, providing clear, accessible guidance on recommended protective steps (e.g., immediate password resets).

---

### 5. Technical Containment Runbooks

#### Runbook A: Production Secret Compromise (`SECRET_KEY`)
1. Immediately generate a new 64-character cryptographically random key:
   `python -c "import secrets; print(secrets.token_hex(32))"`
2. Update the environment configuration in the secure secrets store (AWS SSM / Vercel Environment Variables).
3. Restart backend service instances. This automatically invalidates all existing JWT bearer tokens.
4. Announce session refresh to active clients.

#### Runbook B: Targeted Account Takeover / Brute-Force Attack
1. Manually trigger administrative user account deactivation:
   `UPDATE users SET is_active = 0 WHERE email = 'target@example.com';`
2. Add target JWT to in-memory revocation blacklist (`revoke_token`).
3. Add offending IP subnet to network firewall / edge WAF blocklist.
4. Notify user through out-of-band channel to verify identity and initiate password recovery.

#### Runbook C: Database Data Corruption or Tampering
1. Drain traffic from active database instance.
2. Locate latest clean daily backup from `./backend/backups` or UAE S3 vault.
3. Validate SHA-256 backup checksum using `BackupService.restore_backup`.
4. Restore database state and replay clean immutable `audit_logs` entries.
5. Verify database schema parity using `test_schema_parity.py`.
