"""SQLite 메타데이터 저장소."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    source               TEXT NOT NULL,
    source_id            TEXT NOT NULL,
    category             TEXT NOT NULL,
    query                TEXT,
    title                TEXT,
    filename             TEXT NOT NULL,
    filepath             TEXT NOT NULL,
    thumbnail_path       TEXT,
    url                  TEXT,
    foreign_landing_url  TEXT,
    width                INTEGER,
    height               INTEGER,
    filesize             INTEGER,
    format               TEXT,
    license              TEXT,
    license_version      TEXT,
    license_url          TEXT,
    commercial_use       INTEGER DEFAULT 0,
    modification         INTEGER DEFAULT 0,
    attribution_required INTEGER DEFAULT 0,
    creator              TEXT,
    creator_url          TEXT,
    attribution          TEXT,
    provider             TEXT,
    sha256               TEXT,
    phash                TEXT,
    tags                 TEXT,
    favorite             INTEGER DEFAULT 0,
    rating               INTEGER DEFAULT 0,
    collected_at         TEXT,
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_category ON images(category);
CREATE INDEX IF NOT EXISTS idx_source   ON images(source);
CREATE INDEX IF NOT EXISTS idx_license  ON images(license);
CREATE INDEX IF NOT EXISTS idx_sha256   ON images(sha256);
CREATE INDEX IF NOT EXISTS idx_favorite ON images(favorite);
"""

INSERT_FIELDS = [
    "source", "source_id", "category", "query", "title", "filename", "filepath",
    "thumbnail_path", "url", "foreign_landing_url", "width", "height", "filesize",
    "format", "license", "license_version", "license_url", "commercial_use",
    "modification", "attribution_required", "creator", "creator_url", "attribution",
    "provider", "sha256", "phash", "tags", "collected_at",
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: str | Path) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# --- 존재 확인 (중복 방지) ---

def exists_source_id(conn: sqlite3.Connection, source: str, source_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM images WHERE source=? AND source_id=? LIMIT 1",
        (source, source_id),
    ).fetchone()
    return row is not None


def exists_sha256(conn: sqlite3.Connection, sha256: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM images WHERE sha256=? LIMIT 1", (sha256,)
    ).fetchone()
    return row is not None


def all_phashes(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    rows = conn.execute(
        "SELECT id, phash FROM images WHERE phash IS NOT NULL"
    ).fetchall()
    return [(r["id"], r["phash"]) for r in rows]


# --- 쓰기 ---

def insert_image(conn: sqlite3.Connection, data: dict) -> int:
    cols = ", ".join(INSERT_FIELDS)
    placeholders = ", ".join(f":{f}" for f in INSERT_FIELDS)
    payload = {f: data.get(f) for f in INSERT_FIELDS}
    cur = conn.execute(
        f"INSERT INTO images ({cols}) VALUES ({placeholders})", payload
    )
    conn.commit()
    return cur.lastrowid


def set_favorite(conn: sqlite3.Connection, image_id: int, value: bool) -> None:
    conn.execute("UPDATE images SET favorite=? WHERE id=?", (1 if value else 0, image_id))
    conn.commit()


def set_rating(conn: sqlite3.Connection, image_id: int, value: int) -> None:
    conn.execute("UPDATE images SET rating=? WHERE id=?", (max(0, min(5, value)), image_id))
    conn.commit()


def delete_image(conn: sqlite3.Connection, image_id: int) -> sqlite3.Row | None:
    row = conn.execute("SELECT * FROM images WHERE id=?", (image_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM images WHERE id=?", (image_id,))
        conn.commit()
    return row


# --- 읽기 / 조회 ---

def get_image(conn: sqlite3.Connection, image_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM images WHERE id=?", (image_id,)).fetchone()


def query_images(
    conn: sqlite3.Connection,
    *,
    category: str | None = None,
    source: str | None = None,
    license_code: str | None = None,
    favorite: bool | None = None,
    commercial_only: bool = False,
    search: str | None = None,
    order: str = "recent",
    limit: int = 60,
    offset: int = 0,
) -> list[sqlite3.Row]:
    where = []
    params: list = []
    if category:
        where.append("category = ?")
        params.append(category)
    if source:
        where.append("source = ?")
        params.append(source)
    if license_code:
        where.append("license = ?")
        params.append(license_code)
    if favorite:
        where.append("favorite = 1")
    if commercial_only:
        where.append("commercial_use = 1")
    if search:
        where.append("(title LIKE ? OR tags LIKE ? OR creator LIKE ? OR query LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like, like])

    clause = ("WHERE " + " AND ".join(where)) if where else ""
    order_sql = {
        "recent": "collected_at DESC, id DESC",
        "oldest": "collected_at ASC, id ASC",
        "title": "title ASC",
        "rating": "rating DESC, id DESC",
        "size": "filesize DESC",
    }.get(order, "collected_at DESC, id DESC")

    sql = f"SELECT * FROM images {clause} ORDER BY {order_sql} LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return conn.execute(sql, params).fetchall()


def count_images(conn: sqlite3.Connection, **filters) -> int:
    """query_images 와 동일한 필터로 총 개수."""
    where = []
    params: list = []
    if filters.get("category"):
        where.append("category = ?"); params.append(filters["category"])
    if filters.get("source"):
        where.append("source = ?"); params.append(filters["source"])
    if filters.get("license_code"):
        where.append("license = ?"); params.append(filters["license_code"])
    if filters.get("favorite"):
        where.append("favorite = 1")
    if filters.get("commercial_only"):
        where.append("commercial_use = 1")
    if filters.get("search"):
        where.append("(title LIKE ? OR tags LIKE ? OR creator LIKE ? OR query LIKE ?)")
        like = f"%{filters['search']}%"
        params.extend([like, like, like, like])
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    row = conn.execute(f"SELECT COUNT(*) AS n FROM images {clause}", params).fetchone()
    return row["n"] if row else 0


def distinct_values(conn: sqlite3.Connection, column: str) -> list[str]:
    allowed = {"category", "source", "license"}
    if column not in allowed:
        return []
    rows = conn.execute(
        f"SELECT DISTINCT {column} AS v FROM images WHERE {column} IS NOT NULL "
        f"AND {column} != '' ORDER BY {column}"
    ).fetchall()
    return [r["v"] for r in rows]


def stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS n FROM images").fetchone()["n"]
    size = conn.execute("SELECT COALESCE(SUM(filesize),0) AS s FROM images").fetchone()["s"]
    by_cat = conn.execute(
        "SELECT category, COUNT(*) AS n FROM images GROUP BY category ORDER BY n DESC"
    ).fetchall()
    by_src = conn.execute(
        "SELECT source, COUNT(*) AS n FROM images GROUP BY source ORDER BY n DESC"
    ).fetchall()
    by_lic = conn.execute(
        "SELECT license, COUNT(*) AS n FROM images GROUP BY license ORDER BY n DESC"
    ).fetchall()
    commercial = conn.execute(
        "SELECT COUNT(*) AS n FROM images WHERE commercial_use=1"
    ).fetchone()["n"]
    favorites = conn.execute(
        "SELECT COUNT(*) AS n FROM images WHERE favorite=1"
    ).fetchone()["n"]
    return {
        "total": total,
        "total_size": size,
        "commercial": commercial,
        "favorites": favorites,
        "by_category": [(r["category"], r["n"]) for r in by_cat],
        "by_source": [(r["source"], r["n"]) for r in by_src],
        "by_license": [(r["license"], r["n"]) for r in by_lic],
    }


def attribution_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """저작자 표기가 필요한 이미지들."""
    return conn.execute(
        "SELECT * FROM images WHERE attribution_required=1 "
        "ORDER BY category, source, id"
    ).fetchall()
