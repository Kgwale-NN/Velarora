"""Reclaim idle WAL log space without removing any saved exam records."""
from contextlib import closing
from pathlib import Path
import sqlite3
from backend.db import _core

MIN_WAL_BYTES=64*1024*1024


def checkpoint_if_idle():
    path=Path(_core.DB_PATH)
    wal=Path(str(path)+'-wal')
    if not path.exists() or not wal.exists() or wal.stat().st_size<MIN_WAL_BYTES:
        return False
    # A separate short-lived connection must not inherit a caller's transaction.
    # Give up quickly if an exam starts or another writer needs the database.
    with closing(sqlite3.connect(str(path),timeout=.2)) as c:
        if c.execute("SELECT 1 FROM monitoring_run WHERE status='running' LIMIT 1").fetchone():
            return False
        return c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0]==0
