"""
Transaction script to archive R-RBAC rules in the live genovex.db database.
Ensures exactly 8 rules are updated from PUBLISHED to ARCHIVED,
leaving 14 canonical published rules and 22 total clinical rules.
"""

import sqlite3
import sys

def archive_rbac_rules(db_path: str):
    print(f"Connecting to live database at: {db_path}")
    conn = sqlite3.connect(db_path, isolation_level=None)
    cur = conn.cursor()

    try:
        cur.execute("BEGIN TRANSACTION;")
        
        # Check initial state
        cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE rule_code LIKE 'R-RBAC-%' AND status = 'PUBLISHED';")
        initial_rbac_published = cur.fetchone()[0]
        print(f"Initial PUBLISHED R-RBAC rules: {initial_rbac_published}")
        assert initial_rbac_published == 8, f"Expected 8 PUBLISHED R-RBAC rules, found {initial_rbac_published}"

        # Execute targeted update
        cur.execute("UPDATE clinical_rules SET status = 'ARCHIVED' WHERE rule_code LIKE 'R-RBAC-%';")
        rc = cur.rowcount
        print(f"Updated rowcount: {rc}")
        assert rc == 8, f"Expected 8 rows updated, got {rc}"

        # Verify counts
        cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'PUBLISHED';")
        pub_count = cur.fetchone()[0]
        print(f"Verified PUBLISHED rules count: {pub_count}")
        assert pub_count == 14, f"Expected 14 PUBLISHED rules, got {pub_count}"

        cur.execute("SELECT COUNT(*) FROM clinical_rules WHERE status = 'ARCHIVED';")
        arch_count = cur.fetchone()[0]
        print(f"Verified ARCHIVED rules count: {arch_count}")
        assert arch_count == 8, f"Expected 8 ARCHIVED rules, got {arch_count}"

        cur.execute("SELECT COUNT(*) FROM clinical_rules;")
        total_count = cur.fetchone()[0]
        print(f"Verified total rules count: {total_count}")
        assert total_count == 22, f"Expected 22 total rules, got {total_count}"

        cur.execute("COMMIT;")
        print("Archival transaction successfully committed.")
        return True

    except Exception as e:
        print(f"Archival failed: {e}")
        try:
            cur.execute("ROLLBACK;")
        except Exception:
            pass
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "genovex.db"
    archive_rbac_rules(db_path)
