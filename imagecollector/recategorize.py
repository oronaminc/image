"""원본 태그를 근거로 카테고리를 다시 매긴다.

수집이 '최신순' 으로 돌던 시기에 검색어와 느슨하게 걸린 사진이 많이 섞였다.
classify.audit() 판정에 따라 파일을 옮기고 DB(카테고리·경로·한국어 태그)를 고친다.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from . import classify, db, korean
from .config import Config


def _retag(old_tags: str | None, old_cat: str, new_cat: str, query: str | None) -> str:
    """카테고리 태그만 새 카테고리로 바꾸고, 사용자가 붙인 낱말 태그는 남긴다."""
    generated_before = {t.strip() for t in korean.korean_tags(old_cat, query).split(",") if t.strip()}
    kept = [t.strip() for t in (old_tags or "").split(",")
            if t.strip() and t.strip() not in generated_before]
    new_parts = [t.strip() for t in korean.korean_tags(new_cat, query).split(",") if t.strip()]
    for tag in kept:
        if tag not in new_parts:
            new_parts.append(tag)
    return ", ".join(new_parts)


def _move(src: Path, dest: Path) -> bool:
    """파일 이동. 같은 이름이 있으면 뒤에 -2, -3 을 붙인다."""
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    final = dest
    n = 2
    while final.exists():
        final = dest.with_name(f"{dest.stem}-{n}{dest.suffix}")
        n += 1
    src.rename(final)
    return True


def run(config: Config, *, apply: bool = False, category: str | None = None,
        limit: int | None = None) -> dict:
    """점검 결과 요약을 돌려준다. apply=False 면 아무것도 바꾸지 않는다."""
    conn = db.connect(config.db_path)
    try:
        sql = ("SELECT id, category, query, filename, filepath, thumbnail_path, "
               "source_tags, tags FROM images")
        params: list = []
        if category:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY id"
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = list(conn.execute(sql, params))
        # 라이브러리 전체 기준으로 '너무 흔한 태그' 를 먼저 골라낸다
        generic = classify.build_generic_tags(conn)

        summary = {
            "total": len(rows),
            "ok": 0,
            "moved": 0,
            "unclear": 0,
            "no_tags": 0,
            "moves": Counter(),      # (from, to) -> 개수
            "unclear_by_cat": Counter(),
        }

        for row in rows:
            tags = row["source_tags"]
            if not tags or tags in ("-", "(삭제됨)"):
                summary["no_tags"] += 1
                continue

            verdict = classify.audit(tags, row["category"], generic)
            if verdict["ok"]:
                summary["ok"] += 1
                continue
            if verdict["unclear"] or not verdict["suggested"]:
                summary["unclear"] += 1
                summary["unclear_by_cat"][row["category"]] += 1
                continue

            new_cat = verdict["suggested"]
            summary["moved"] += 1
            summary["moves"][(row["category"], new_cat)] += 1
            if not apply:
                continue

            # 파일 이동 → DB 갱신
            old_rel = Path(row["filepath"])
            new_rel = Path(new_cat) / old_rel.name
            moved = _move(config.images_dir / old_rel, config.images_dir / new_rel)

            new_thumb_rel = None
            if row["thumbnail_path"]:
                old_thumb = Path(row["thumbnail_path"])
                new_thumb_rel = Path(new_cat) / old_thumb.name
                if not _move(config.thumbnails_dir / old_thumb,
                             config.thumbnails_dir / new_thumb_rel):
                    new_thumb_rel = None

            conn.execute(
                "UPDATE images SET category=?, filepath=?, thumbnail_path=?, tags=? WHERE id=?",
                (
                    new_cat,
                    str(new_rel) if moved else row["filepath"],
                    str(new_thumb_rel) if new_thumb_rel else row["thumbnail_path"],
                    _retag(row["tags"], row["category"], new_cat, row["query"]),
                    row["id"],
                ),
            )

        if apply:
            conn.commit()
        return summary
    finally:
        conn.close()
