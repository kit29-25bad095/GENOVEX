import os
import tempfile
import pytest
from sqlalchemy import create_engine, event, text, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
from app.core.database import engine as app_engine, set_sqlite_pragma

def test_sqlite_pool_concurrent_connections_fk_enabled():
    """
    Verify application SQLite connection pool:
    1. Holds two connections simultaneously from app_engine.
    2. Verifies separate underlying DBAPI connections.
    3. Confirms PRAGMA foreign_keys=1 on both.
    4. Disposes the pool and verifies a newly created connection also reports foreign_keys=1.
    """
    with app_engine.connect() as conn1:
        with app_engine.connect() as conn2:
            # Verify distinct underlying DBAPI connections
            dbapi1 = conn1.connection.dbapi_connection
            dbapi2 = conn2.connection.dbapi_connection
            assert dbapi1 is not dbapi2, "Expected distinct DBAPI connections for concurrent checkouts"

            # Verify foreign_keys=1 on both connections
            fk1 = conn1.execute(text("PRAGMA foreign_keys;")).scalar()
            fk2 = conn2.execute(text("PRAGMA foreign_keys;")).scalar()
            assert fk1 == 1, f"Expected foreign_keys=1 on conn1, got {fk1}"
            assert fk2 == 1, f"Expected foreign_keys=1 on conn2, got {fk2}"

    # Dispose pool and verify a fresh connection still executes listener
    app_engine.dispose()
    with app_engine.connect() as conn3:
        fk3 = conn3.execute(text("PRAGMA foreign_keys;")).scalar()
        assert fk3 == 1, f"Expected foreign_keys=1 on conn3 after pool dispose, got {fk3}"

def test_sqlite_foreign_key_enforcement_rejects_invalid_insert():
    """
    Verify that SQLite rejects invalid foreign keys with IntegrityError
    when using the app's set_sqlite_pragma listener on a disposable file database.
    """
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_fk_enforcement.db")
    temp_db_url = f"sqlite:///{temp_db_path}"

    temp_engine = create_engine(temp_db_url, connect_args={"check_same_thread": False})
    event.listen(temp_engine, "connect", set_sqlite_pragma)

    TestBase = declarative_base()

    class Parent(TestBase):
        __tablename__ = "test_parents"
        id = Column(Integer, primary_key=True)
        name = Column(String(50), nullable=False)

    class Child(TestBase):
        __tablename__ = "test_children"
        id = Column(Integer, primary_key=True)
        parent_id = Column(Integer, ForeignKey("test_parents.id", ondelete="CASCADE"), nullable=False)

    TestBase.metadata.create_all(temp_engine)

    TestSession = sessionmaker(bind=temp_engine)
    session = TestSession()

    try:
        # Inserting child with nonexistent parent must raise IntegrityError
        invalid_child = Child(id=1, parent_id=9999)
        session.add(invalid_child)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # Valid insert must succeed
        parent = Parent(id=1, name="Valid Parent")
        session.add(parent)
        session.commit()

        valid_child = Child(id=1, parent_id=1)
        session.add(valid_child)
        session.commit()

        assert session.query(Child).count() == 1
    finally:
        session.close()
        temp_engine.dispose()
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        os.rmdir(temp_dir)
