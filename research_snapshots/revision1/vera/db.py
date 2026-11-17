"""Private SQLite storage for contributed, attributed family memories."""
from __future__ import annotations
import os
import json
import uuid
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    contributor TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('story','photo_note','recording_note','letter','recipe','other')),
    content TEXT NOT NULL,
    media_path TEXT,
    created_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title, contributor, content,
    content='memories', content_rowid='id',
    tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid,title,contributor,content)
  VALUES (new.id,new.title,new.contributor,new.content);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts,rowid,title,contributor,content)
  VALUES ('delete',old.id,old.title,old.contributor,old.content);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts,rowid,title,contributor,content)
  VALUES ('delete',old.id,old.title,old.contributor,old.content);
  INSERT INTO memories_fts(rowid,title,contributor,content)
  VALUES (new.id,new.title,new.contributor,new.content);
END;
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    parent_existed = db_path.parent.exists()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Back up an existing archive before the additive metadata migration.
    if db_path.exists():
        with closing(sqlite3.connect(db_path)) as old:
            migrated = old.execute("SELECT 1 FROM sqlite_master WHERE name='memory_details'").fetchone()
            if not migrated:
                backup_dir = db_path.parent / 'backups'
                backup_dir.mkdir(mode=0o700, exist_ok=True)
                target = backup_dir / (db_path.name + '.' + uuid.uuid4().hex + '.sqlite3')
                with closing(sqlite3.connect(target)) as backup:
                    old.backup(backup)
                    if backup.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Archive backup failed integrity verification')
                target.chmod(0o600)
    if os.name == 'posix' and not parent_existed:
        db_path.parent.chmod(0o700)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    con.execute("""CREATE TABLE IF NOT EXISTS memory_details (
        memory_id INTEGER PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
        metadata TEXT NOT NULL DEFAULT '{}',
        supersedes INTEGER REFERENCES memories(id),
        retired INTEGER NOT NULL DEFAULT 0 CHECK(retired IN (0,1)))""")
    con.execute('INSERT OR IGNORE INTO memory_details(memory_id) SELECT id FROM memories')
    con.commit()
    if os.name == 'posix':
        db_path.chmod(0o600)
    return con


def insert_memory(con: sqlite3.Connection, *, title: str, contributor: str, kind: str,
                  content: str, media_path: str | None = None, metadata: dict | None = None,
                  supersedes: int | None = None, commit: bool = True) -> int:
    for value in (title, contributor, content):
        if not value or not value.strip():
            raise ValueError('Title, contributor, and content are required')
    if kind not in {'story','photo_note','recording_note','letter','recipe','other'}:
        raise ValueError('Unknown source type')
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError('Metadata must be an object')
    for key in ('events', 'people'):
        value = (metadata or {}).get(key, [])
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
            raise ValueError(f'{key} must contain stable text identifiers')
    encoded = json.dumps(metadata or {}, ensure_ascii=False)
    if supersedes is not None and not con.execute('SELECT 1 FROM memories WHERE id=?', (supersedes,)).fetchone():
        raise ValueError('Original memory does not exist')
    cur = con.execute(
        'INSERT INTO memories(title,contributor,kind,content,media_path,created_at) VALUES(?,?,?,?,?,?)',
        (title.strip(), contributor.strip(), kind, content, media_path,
         datetime.now(timezone.utc).isoformat()))
    con.execute('INSERT INTO memory_details(memory_id,metadata,supersedes) VALUES(?,?,?)',
                (cur.lastrowid, encoded, supersedes))
    if supersedes is not None:
        con.execute('UPDATE memory_details SET retired=1 WHERE memory_id=?', (supersedes,))
    if commit:
        con.commit()
    return int(cur.lastrowid)


def list_memories(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(con.execute('SELECT id,title,contributor,kind FROM memories WHERE id NOT IN (SELECT memory_id FROM memory_details WHERE retired=1) ORDER BY id'))


def get_memories(con: sqlite3.Connection, ids: list[int]) -> list[sqlite3.Row]:
    if not ids:
        return []
    placeholders = ','.join('?' for _ in ids)
    results = {r['id']: r for r in con.execute(f"SELECT memories.*, coalesce(d.metadata, '{{}}') AS metadata FROM memories LEFT JOIN memory_details d ON d.memory_id=memories.id WHERE coalesce(d.retired,0)=0 AND id IN ({placeholders})", ids)}
    return [results[id_] for id_ in ids if id_ in results]


def delete_memory(con: sqlite3.Connection, memory_id: int) -> None:
    """Delete a contribution; external original media are never removed."""
    if con.execute('SELECT 1 FROM memory_details WHERE supersedes=?', (memory_id,)).fetchone():
        raise ValueError('Delete corrections before deleting their original contribution')
    con.execute('DELETE FROM memories WHERE id=?', (memory_id,))
    con.commit()
