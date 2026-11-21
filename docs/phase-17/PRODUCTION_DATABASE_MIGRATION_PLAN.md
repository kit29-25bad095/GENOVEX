# GENOVEX Production Database Migration Plan (SQLite to PostgreSQL 16)

**Project:** GENOVEX Clinical Health & Genetic Risk Assessment Platform  
**Source Database:** Local Authoritative SQLite (`genovex.db`)  
**Target Database:** Amazon RDS PostgreSQL 16 (Multi-AZ, `me-central-1` Dubai)  
**Verification Level:** Statically Audited & Formally Documented (Local Runtime Testing Pending Target PostgreSQL Instance)  

---

## 1. Static PostgreSQL 16 Compatibility Audit

An exhaustive static code review was performed on all SQLAlchemy models (`backend/app/models/`) and Alembic migrations (`backend/alembic/versions/`):

1. **Dialect-Agnostic Boolean Defaults:**
   - In `0002_add_password_reset_tokens.py`, boolean default was updated to `server_default=sa.false()`, eliminating SQLite (`0`) vs PostgreSQL (`FALSE`) syntax divergence.
   - All boolean columns in `0001_phase5_baseline.py` specify `sa.Boolean()` with standard Python nullability, compatible across SQLite and PostgreSQL.
2. **Autoincrement & Sequences:**
   - In SQLite, integer primary keys use internal `ROWID` autoincrement.
   - In PostgreSQL, primary key columns rely on underlying sequences (`<table_name>_<column>_seq`). Direct data insertion from SQLite preserves integer IDs but **does not automatically advance PostgreSQL sequences**. A dedicated sequence synchronization step is mandatory.
3. **Foreign Key Integrity:**
   - Circular dependencies were evaluated: none exist. The schema forms a clean directed acyclic graph (DAG) enabling deterministic table-by-table data insertion.
4. **Driver Compatibility:**
   - `psycopg2-binary>=2.9.9` is added to `backend/requirements.txt` to provide standard DBAPI communication with PostgreSQL 16.

> [!NOTE]
> PostgreSQL 16 compatibility has been reviewed statically across all 18 tables, indexes, constraints, and migrations. Because PostgreSQL is not installed locally on the development workstation, runtime execution of this migration must be performed against the isolated RDS staging instance during cloud deployment.

---

## 2. Nine-Step Repeatable Migration Process

### Step 1: Authoritative Source Backup & Verification
Capture a timestamped cold snapshot of `genovex.db` and calculate its cryptographic checksum:
- **Verified Baseline Snapshot:** `backups/genovex_pre_phase17_migration_20261121_133125.db`
- **File Size:** `4,993,024 bytes`
- **SHA-256 Checksum:** `7058ff3cd120da624ffa3a0c22714fe5d0bef757f775a7f2c73643e97d32aa37`
- **Integrity Validation:** Run `PRAGMA integrity_check;` and `PRAGMA foreign_key_check;`.

### Step 2: Target PostgreSQL Database Provisioning
Provision Amazon RDS PostgreSQL 16 Multi-AZ instance in AWS Dubai (`me-central-1`) inside private subnets:
```bash
aws rds create-db-instance \
    --region me-central-1 \
    --db-instance-identifier genovex-prod-db \
    --db-instance-class db.t4g.medium \
    --engine postgres \
    --engine-version 16.3 \
    --multi-az \
    --allocated-storage 50 \
    --storage-type gp3 \
    --storage-encrypted \
    --kms-key-id arn:aws:kms:me-central-1:ACCOUNT:key/KEY-ID \
    --no-publicly-accessible
```

### Step 3: Schema Creation via Alembic Head
Run Alembic migrations against the fresh PostgreSQL target to create all tables, indexes, and constraints:
```bash
export DATABASE_URL="postgresql+psycopg2://genovex_app:[PASS]@genovex-prod-db.[id].me-central-1.rds.amazonaws.com:5432/genovex_prod"
alembic upgrade head
```
*Expected target revision:* `0002_add_password_reset_tokens`.

### Step 4: Topological Data Transfer (Foreign-Key Safe Order)
Extract records from SQLite and insert into PostgreSQL following strict dependency hierarchy:
1. `users` (18 records)
2. `medical_categories` (5 records)
3. `medical_references` (7 records)
4. `healthcare_facilities` (8 records)
5. `questionnaire_versions` (1 record)
6. `audit_logs` (8 records)
7. `clinical_rules` (22 records)
8. `medical_conditions` (12 records)
9. `clinical_rule_versions` (22 records)
10. `condition_references` (25 records)
11. `condition_contents` (24 records)
12. `content_versions` (13 records)
13. `questions` (19 records)
14. `assessments` (90 records)
15. `assessment_responses` (179 records)
16. `assessment_reports` (89 records)
17. `clinical_review_records` (7 records)
18. `password_reset_tokens` (0 records)

### Step 5: PostgreSQL Sequence Synchronization
Execute explicit sequence updates for all tables to ensure subsequent `INSERT` operations generate valid primary keys:
```sql
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users;
SELECT setval(pg_get_serial_sequence('medical_categories', 'id'), COALESCE(MAX(id), 1)) FROM medical_categories;
SELECT setval(pg_get_serial_sequence('medical_references', 'id'), COALESCE(MAX(id), 1)) FROM medical_references;
SELECT setval(pg_get_serial_sequence('healthcare_facilities', 'id'), COALESCE(MAX(id), 1)) FROM healthcare_facilities;
SELECT setval(pg_get_serial_sequence('questionnaire_versions', 'id'), COALESCE(MAX(id), 1)) FROM questionnaire_versions;
SELECT setval(pg_get_serial_sequence('audit_logs', 'id'), COALESCE(MAX(id), 1)) FROM audit_logs;
SELECT setval(pg_get_serial_sequence('clinical_rules', 'id'), COALESCE(MAX(id), 1)) FROM clinical_rules;
SELECT setval(pg_get_serial_sequence('medical_conditions', 'id'), COALESCE(MAX(id), 1)) FROM medical_conditions;
SELECT setval(pg_get_serial_sequence('clinical_rule_versions', 'id'), COALESCE(MAX(id), 1)) FROM clinical_rule_versions;
SELECT setval(pg_get_serial_sequence('condition_references', 'id'), COALESCE(MAX(id), 1)) FROM condition_references;
SELECT setval(pg_get_serial_sequence('condition_contents', 'id'), COALESCE(MAX(id), 1)) FROM condition_contents;
SELECT setval(pg_get_serial_sequence('content_versions', 'id'), COALESCE(MAX(id), 1)) FROM content_versions;
SELECT setval(pg_get_serial_sequence('questions', 'id'), COALESCE(MAX(id), 1)) FROM questions;
SELECT setval(pg_get_serial_sequence('assessments', 'id'), COALESCE(MAX(id), 1)) FROM assessments;
SELECT setval(pg_get_serial_sequence('assessment_responses', 'id'), COALESCE(MAX(id), 1)) FROM assessment_responses;
SELECT setval(pg_get_serial_sequence('assessment_reports', 'id'), COALESCE(MAX(id), 1)) FROM assessment_reports;
SELECT setval(pg_get_serial_sequence('clinical_review_records', 'id'), COALESCE(MAX(id), 1)) FROM clinical_review_records;
SELECT setval(pg_get_serial_sequence('password_reset_tokens', 'id'), COALESCE(MAX(id), 1)) FROM password_reset_tokens;
```

### Step 6: Row Count & Parity Comparison
Compare target table record counts against the verified SQLite source baseline:
- Target sum must match exactly **520 application records** across all 18 tables.

### Step 7: Constraint & Foreign Key Verification
Execute queries checking for orphaned foreign keys or integrity errors:
```sql
SELECT count(*) FROM assessment_responses r LEFT JOIN assessments a ON r.assessment_id = a.id WHERE a.id IS NULL;
-- Expected: 0
SELECT count(*) FROM assessment_reports rep LEFT JOIN assessments a ON rep.assessment_id = a.id WHERE a.id IS NULL;
-- Expected: 0
```

### Step 8: Application Smoke Testing
Connect a staging backend instance to the migrated database and run the validation suite (auth login, questionnaire fetch, report generation).

### Step 9: Rollback Procedure
If migration fails at any step:
1. Drop and recreate the `genovex_prod` PostgreSQL schema (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`).
2. Restore authoritative state from the verified SQLite cold snapshot.
3. Investigate the schema exception before re-attempting.
