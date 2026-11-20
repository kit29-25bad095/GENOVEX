import os
import sqlite3
import hashlib
import glob
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("backup_service")

class BackupService:
    """
    Automated SQLite Online Backup, Verification, and Disaster Recovery Service.
    Uses SQLite's native online backup API (`sqlite3.backup`), ensuring zero lock contention
    and zero corruption during active read/write operations.
    """

    @classmethod
    def get_backup_directory(cls) -> str:
        backup_dir = os.path.abspath(settings.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @classmethod
    def get_database_path(cls) -> str:
        clean_url = settings.DATABASE_URL.replace("sqlite:///", "")
        return os.path.abspath(clean_url)

    @classmethod
    def calculate_checksum(cls, filepath: str) -> str:
        """Calculates SHA-256 checksum of a file for integrity verification."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def verify_backup_integrity(cls, backup_path: str) -> Dict[str, Any]:
        """
        Executes PRAGMA integrity_check on the backup file.
        Returns status 'ok' and row count if database structure is valid.
        """
        if not os.path.exists(backup_path):
            return {"valid": False, "error": "Backup file does not exist"}

        try:
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            is_ok = result and result[0] == "ok"

            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()

            return {
                "valid": is_ok,
                "integrity_result": result[0] if result else "unknown",
                "table_count": table_count,
                "file_size_bytes": os.path.getsize(backup_path)
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    @classmethod
    def create_backup(cls, label: str = "scheduled") -> Dict[str, Any]:
        """
        Executes a safe online backup using Python's native sqlite3.backup API.
        Verifies integrity, calculates checksum, and prunes expired backups.
        """
        source_db_path = cls.get_database_path()
        if not os.path.exists(source_db_path):
            raise FileNotFoundError(f"Source database not found at {source_db_path}")

        backup_dir = cls.get_backup_directory()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"genovex_backup_{label}_{timestamp}.db"
        target_backup_path = os.path.join(backup_dir, backup_filename)

        logger.info(f"Starting online database backup to {target_backup_path}...")

        # Execute online backup
        source_conn = sqlite3.connect(source_db_path)
        dest_conn = sqlite3.connect(target_backup_path)
        try:
            source_conn.backup(dest_conn, pages=100)
            dest_conn.commit()
        finally:
            dest_conn.close()
            source_conn.close()

        # Integrity verification
        verification = cls.verify_backup_integrity(target_backup_path)
        if not verification["valid"]:
            logger.error(f"Backup integrity verification failed for {target_backup_path}: {verification}")
            raise RuntimeError(f"Backup integrity check failed: {verification.get('error')}")

        checksum = cls.calculate_checksum(target_backup_path)

        # Write checksum file
        checksum_path = target_backup_path + ".sha256"
        with open(checksum_path, "w") as f:
            f.write(f"{checksum}  {backup_filename}\n")

        # Rotate older backups
        cls.prune_old_backups(keep_count=settings.BACKUP_RETENTION_COUNT)

        logger.info(f"Backup {backup_filename} created and verified successfully. Checksum: {checksum[:12]}...")

        return {
            "success": True,
            "backup_filename": backup_filename,
            "backup_path": target_backup_path,
            "checksum_sha256": checksum,
            "size_bytes": verification["file_size_bytes"],
            "table_count": verification["table_count"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def prune_old_backups(cls, keep_count: int = 7) -> List[str]:
        """Retains the latest N backups and removes older backup files and checksums."""
        backup_dir = cls.get_backup_directory()
        backup_files = sorted(glob.glob(os.path.join(backup_dir, "genovex_backup_*.db")), key=os.path.getmtime)

        pruned = []
        if len(backup_files) > keep_count:
            files_to_remove = backup_files[:-keep_count]
            for f in files_to_remove:
                try:
                    os.remove(f)
                    checksum_f = f + ".sha256"
                    if os.path.exists(checksum_f):
                        os.remove(checksum_f)
                    pruned.append(os.path.basename(f))
                except Exception as e:
                    logger.error(f"Failed to prune old backup {f}: {e}")
        return pruned

    @classmethod
    def list_backups(cls) -> List[Dict[str, Any]]:
        """Lists all existing backups with metadata and verification status."""
        backup_dir = cls.get_backup_directory()
        backup_files = sorted(glob.glob(os.path.join(backup_dir, "genovex_backup_*.db")), key=os.path.getmtime, reverse=True)

        results = []
        for bf in backup_files:
            fname = os.path.basename(bf)
            size = os.path.getsize(bf)
            mtime = datetime.fromtimestamp(os.path.getmtime(bf), timezone.utc).isoformat()
            has_checksum = os.path.exists(bf + ".sha256")
            results.append({
                "filename": fname,
                "size_bytes": size,
                "created_at": mtime,
                "has_checksum": has_checksum
            })
        return results
