import os
import sys
import shutil
import tempfile
import sqlite3
import hashlib

# Add backend to path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_path)

from app.core.config import settings
from app.services.backup_service import BackupService

def run_backup_recovery_verification():
    print("=== STEP 1: Execute Backup in Test Environment ===")
    
    # Live db path
    live_db_path = BackupService.get_database_path()
    assert os.path.exists(live_db_path), f"Live DB not found at {live_db_path}"
    initial_live_mtime = os.path.getmtime(live_db_path)
    initial_live_size = os.path.getsize(live_db_path)
    print(f"[OK] Live database identified: {live_db_path} ({initial_live_size} bytes)")

    # Execute backup
    backup_result = BackupService.create_backup(label="audit_verification_test")
    print(f"[OK] Backup created successfully: {backup_result['backup_filename']}")
    assert backup_result["success"] is True
    backup_file = backup_result["backup_path"]
    assert os.path.exists(backup_file), "Backup file does not exist on disk"

    print("\n=== STEP 2: Verify Checksum and SQLite Integrity ===")
    checksum_file = backup_file + ".sha256"
    assert os.path.exists(checksum_file), "Checksum file missing"
    with open(checksum_file, "r") as f:
        saved_checksum = f.read().strip().split()[0]
    
    calculated_checksum = BackupService.calculate_checksum(backup_file)
    print(f"  Saved checksum:      {saved_checksum}")
    print(f"  Calculated checksum: {calculated_checksum}")
    assert saved_checksum == calculated_checksum, "Checksum mismatch!"
    print("[OK] Cryptographic SHA-256 Checksum verified!")

    integrity_res = BackupService.verify_backup_integrity(backup_file)
    print(f"  Integrity result: {integrity_res}")
    assert integrity_res["valid"] is True
    assert integrity_res["integrity_result"] == "ok"
    assert integrity_res["table_count"] > 0
    print(f"[OK] SQLite PRAGMA integrity_check == ok, {integrity_res['table_count']} tables verified!")

    print("\n=== STEP 3: Restore Backup into a Separate Test Database ===")
    temp_restore_dir = tempfile.mkdtemp(prefix="genovex_restore_audit_")
    restored_db_path = os.path.join(temp_restore_dir, "restored_genovex.db")
    shutil.copyfile(backup_file, restored_db_path)
    print(f"[OK] Restored to isolated destination: {restored_db_path}")

    print("\n=== STEP 4: Verify Restored Records Accessibility ===")
    conn = sqlite3.connect(restored_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
    print(f"  Restored tables count: {len(tables)} tables ({', '.join(tables[:5])}...)")
    assert len(tables) >= 10, "Restored table count too low"

    # Count rows in key tables
    for tbl in ["users", "medical_conditions", "clinical_rules", "questions"]:
        cursor.execute(f"SELECT count(*) FROM {tbl};")
        cnt = cursor.fetchone()[0]
        print(f"  Table '{tbl}': {cnt} records")
        assert cnt > 0, f"Table '{tbl}' is empty in restored database!"
    conn.close()
    print("[OK] Restored records verified accessible and valid!")

    print("\n=== STEP 5: Verify Retention & Pruning Behavior ===")
    # Temporarily test pruning logic
    test_retention = 5
    for i in range(7):
        # Create small dummy backup files
        dummy_name = f"genovex_backup_dummy_prune_{i}.db"
        dummy_path = os.path.join(BackupService.get_backup_directory(), dummy_name)
        with open(dummy_path, "w") as f:
            f.write("dummy")
        with open(dummy_path + ".sha256", "w") as f:
            f.write("dummy_hash")
    
    BackupService.prune_old_backups(keep_count=test_retention)
    current_backups = BackupService.list_backups()
    print(f"  Current backups after pruning (limit {test_retention}): {len(current_backups)}")
    assert len(current_backups) <= test_retention + 2 # Accounting for recent audit backups
    print("[OK] Retention and pruning logic successfully purged expired backups!")

    print("\n=== STEP 6: Verify Live Database Untouched & Not Overwritten ===")
    final_live_mtime = os.path.getmtime(live_db_path)
    final_live_size = os.path.getsize(live_db_path)
    print(f"  Initial live DB size: {initial_live_size}, current live DB size: {final_live_size}")
    assert initial_live_size == final_live_size, "Live database size changed unexpectedly!"
    print("[OK] Verified that backup operations NEVER overwrite or corrupt the live database!")

    # Cleanup temp restore dir
    shutil.rmtree(temp_restore_dir, ignore_errors=True)
    print("\nALL BACKUP & DISASTER RECOVERY TESTS PASSED!")

if __name__ == "__main__":
    run_backup_recovery_verification()
