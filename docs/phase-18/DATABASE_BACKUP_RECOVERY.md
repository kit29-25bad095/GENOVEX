# GENOVEX Database Backup, Verification & Disaster Recovery Guide

## 1. Overview & Recovery Objectives

GENOVEX utilizes SQLite 3 running in Write-Ahead Logging (`WAL`) mode (`journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`). This ensures high-throughput concurrent reads alongside uninterrupted writes.

To guarantee business continuity and clinical audit compliance, the platform enforces:
- **Recovery Point Objective (RPO):** Maximum 6 hours (standard background backup cycle); RPO = 0 for on-demand administrative backups prior to migrations.
- **Recovery Time Objective (RTO):** Under 5 minutes for full database file restoration and verification.

---

## 2. Online Backup Mechanism (`sqlite3.backup`)

Rather than copying database files directly (which carries severe corruption risks if a write occurs concurrently), the platform uses the official Python SQLite Online Backup API:

```python
source_conn = sqlite3.connect(source_db_path)
dest_conn = sqlite3.connect(target_backup_path)
try:
    # Copies 100 pages per step without blocking writer transactions
    source_conn.backup(dest_conn, pages=100)
    dest_conn.commit()
finally:
    dest_conn.close()
    source_conn.close()
```

### 2.1 File Naming & Location Conventions
- **Backup Directory:** Configured via `BACKUP_DIR` (Default: `backend/backups/`)
- **Naming Pattern:** `genovex_backup_{label}_{YYYYMMDD_HHMMSS}.db`
  - Examples:
    - `genovex_backup_scheduled_auto_20261120_200000.db`
    - `genovex_backup_manual_admin_20261120_201500.db`
    - `genovex_backup_pre_migration_20261120_210000.db`
- **Companion Checksum File:** Every backup produces an associated `.sha256` digest file for tamper and corruption detection.

---

## 3. Automated Integrity Verification

Immediately upon creation, every backup undergoes mandatory structural and cryptographic verification:
1. **SQLite Structural Check:**
   - Connects to the freshly generated backup file.
   - Executes `PRAGMA integrity_check;`.
   - Requires an exact return of `"ok"`.
   - Confirms table count > 0 against `sqlite_master`.
2. **Cryptographic SHA-256 Digesting:**
   - Reads the file in 64 KB blocks and computes the SHA-256 hash.
   - Saves `<backup_filename>.sha256` containing `<hash>  <filename>`.

---

## 4. Backup Retention & Rotation Policy

To prevent storage exhaustion:
- The system retains the **10 most recent valid backups** (`BACKUP_RETENTION_COUNT=10`).
- Pruning runs automatically after every backup execution.
- Expired `.db` files and their corresponding `.sha256` files are unlinked cleanly.

---

## 5. Step-by-Step Disaster Recovery Procedure

In the event of physical disk corruption, accidental data deletion, or operational disaster:

### Step 1: Stop the Application Service
```bash
# Gracefully stop backend server to release open file descriptors
killall uvicorn
# OR on Windows PowerShell:
Stop-Process -Name "python" -Force
```

### Step 2: Select and Verify Target Backup Snapshot
```bash
# Navigate to backups directory
cd backend/backups/

# Inspect available backups
ls -la genovex_backup_*.db

# Verify SHA-256 checksum against saved digest
sha256sum -c genovex_backup_manual_admin_20261120_201500.db.sha256
```

### Step 3: Run SQLite PRAGMA Integrity Check
```bash
sqlite3 genovex_backup_manual_admin_20261120_201500.db "PRAGMA integrity_check;"
# Expected output: ok
```

### Step 4: Archive Corrupted Database (Forensic Isolation)
```bash
mv ../genovex.db ../genovex_corrupted_$(date +%s).db.bak
rm -f ../genovex.db-wal ../genovex.db-shm
```

### Step 5: Restore Verified Snapshot
```bash
cp genovex_backup_manual_admin_20261120_201500.db ../genovex.db
```

### Step 6: Verify Database Initialization and Restart Service
```bash
sqlite3 ../genovex.db "SELECT count(*) FROM users; SELECT count(*) FROM medical_conditions;"
uvicorn main:app --host 0.0.0.0 --port 8000
```
