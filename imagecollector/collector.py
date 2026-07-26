"""수집 오케스트레이션: 검색 -> 라이선스/크기 필터 -> 다운로드 -> 중복검사 -> 저장."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from . import classify, db, dedup, images, korean, licenses, translate
from .config import Config
from .models import ImageResult
from .sources import get_source

console = Console()


def _merge_tags(korean_tags: str | None, extra: str | None,
                source_tags: str | None) -> str | None:
    """한국어 태그 + 사용자가 친 낱말을 합친다.

    둘 다 없을 때만 소스의 영어 태그로 대체한다(영어 태그는 부정확해서 후순위).
    """
    merged: list[str] = []
    for part in (korean_tags, extra):
        for tag in (t.strip() for t in (part or "").split(",")):
            if tag and tag not in merged:
                merged.append(tag)
    if merged:
        return ", ".join(merged)
    return source_tags or None


class Collector:
    def __init__(self, config: Config):
        self.config = config
        config.ensure_dirs()
        db.init_db(config.db_path)
        self.conn = db.connect(config.db_path)
        self.session = images.make_session(config.user_agent)
        self.stats = {"downloaded": 0, "skipped_dup": 0, "skipped_filter": 0, "errors": 0}

    def close(self) -> None:
        self.conn.close()

    # --- 카테고리/검색어 해석 ---
    def resolve_targets(self, categories=None, queries=None) -> list[tuple[str, str]]:
        """반환: (category, query) 튜플 목록."""
        targets: list[tuple[str, str]] = []
        cfg_categories = self.config.categories
        if queries:
            cat = (categories[0] if categories else "custom")
            for q in queries:
                targets.append((cat, q))
            return targets
        selected = categories or list(cfg_categories.keys())
        for cat in selected:
            for q in cfg_categories.get(cat, []) or []:
                targets.append((cat, q))
        return targets

    # --- 메인 진입점 ---
    def run(self, source_name: str | None = None, categories=None, queries=None,
            limit: int | None = None) -> dict:
        coll = self.config.collection
        source_name = source_name or coll.get("default_source", "openverse")
        limit = limit or int(coll.get("per_category_limit", 40))
        source = get_source(source_name, self.config)

        ok, note = source.available()
        if not ok:
            console.print(f"[red]소스 '{source_name}' 사용 불가:[/red] {note}")
            return self.stats

        targets = self.resolve_targets(categories, queries)
        if not targets:
            console.print("[yellow]수집할 카테고리/검색어가 없습니다. config.yaml 을 확인하세요.[/yellow]")
            return self.stats

        console.print(f"[bold cyan]■ 소스:[/bold cyan] {source.label}  "
                      f"[bold cyan]라이선스:[/bold cyan] {coll.get('license_type')}  "
                      f"[bold cyan]카테고리당 목표:[/bold cyan] {limit}")

        for category, query in targets:
            self._collect_one(source, category, query, limit)

        self._print_summary()
        return self.stats

    def _collect_one(self, source, category: str, query: str, limit: int) -> None:
        got = 0
        console.print(f"\n[bold]▸ {category} / \"{query}\"[/bold]")
        try:
            for result in source.search(query, limit * 2):  # 필터 감안해 여유있게 요청
                if got >= limit:
                    break
                status, _image_id = self._process(result, category, query)
                if status == "ok":
                    got += 1
                    console.print(f"  [green]✓[/green] {got}/{limit}  {result.title[:60] or result.source_id}")
        except Exception as exc:  # 소스 오류가 전체를 멈추지 않도록
            console.print(f"  [red]소스 오류:[/red] {exc}")

        if got == 0:
            console.print("  [yellow](수집된 이미지 없음)[/yellow]")

    def _process(self, r: ImageResult, category: str, query: str,
                 attribution_free: bool = False, ignore_recency: bool = False,
                 extra_tags: str | None = None) -> tuple[str, int | None]:
        coll = self.config.collection

        # 1) 이미 있는 항목(같은 소스+id) 건너뜀
        if db.exists_source_id(self.conn, r.source, r.source_id):
            self.stats["skipped_dup"] += 1
            return "dup", None

        # 2) 상업적 사용 안전장치
        if coll.get("license_type", "commercial").startswith("commercial"):
            if not licenses.is_commercial_ok(r.license) and r.source in ("openverse", "wikimedia"):
                self.stats["skipped_filter"] += 1
                return "filter", None

        # 2-b) 저작자 표기 불필요 이미지만 원할 때 (다운로드 전 필터 → 낭비 없음)
        if attribution_free and licenses.is_attribution_required(r.license):
            self.stats["skipped_filter"] += 1
            return "filter", None

        # 2-c) Pixabay 최신 필터: source_id(=업로드순 ID)가 기준 미만이면 제외 (예: 2024+ 만)
        #      낱말 검색(fetch_new)은 '최신'보다 '관련도'가 중요하므로 이 필터를 끈다.
        min_sid = 0 if ignore_recency else int(coll.get("min_source_id", 0) or 0)
        if min_sid and r.source == "pixabay":
            try:
                if int(r.source_id) < min_sid:
                    self.stats["skipped_filter"] += 1
                    return "filter", None
            except (ValueError, TypeError):
                pass

        # 3) 확장자 판별 (svg 등 미지원 제외)
        ext = images.guess_ext(r.url, None, r.filetype)
        if not ext:
            # content-type 은 다운로드 시 확인 → 일단 진행하되 뒤에서 검증
            ext = "jpg"

        # 4) 최소 해상도 (메타 기준 1차 필터)
        min_w = int(coll.get("min_width", 0) or 0)
        min_h = int(coll.get("min_height", 0) or 0)
        if r.width and r.height and (r.width < min_w or r.height < min_h):
            self.stats["skipped_filter"] += 1
            return "filter", None

        # 5) 다운로드 (임시 이름 → 검증 후 확정)
        filename = images.make_filename(category, r.title, r.source, r.source_id, ext)
        rel_path = Path(category) / filename
        dest = self.config.images_dir / rel_path
        try:
            sha, size, content_type = images.download(self.session, r.url, dest)
        except Exception:
            self.stats["errors"] += 1
            return "error", None

        # content-type 으로 확장자 보정
        real_ext = images.guess_ext(r.url, content_type, r.filetype)
        if real_ext and real_ext != ext:
            new_name = images.make_filename(category, r.title, r.source, r.source_id, real_ext)
            new_rel = Path(category) / new_name
            new_dest = self.config.images_dir / new_rel
            try:
                dest.rename(new_dest)
                dest, rel_path, filename = new_dest, new_rel, new_name
            except OSError:
                pass

        # 6) 정확 중복(sha256) 검사
        if db.exists_sha256(self.conn, sha):
            dest.unlink(missing_ok=True)
            self.stats["skipped_dup"] += 1
            return "dup", None

        # 7) 실제 이미지 검증 + 크기/포맷
        probe = images.probe_image(dest)
        if probe is None:
            dest.unlink(missing_ok=True)
            self.stats["errors"] += 1
            return "error", None
        width, height, fmt = probe
        if (min_w and width < min_w) or (min_h and height < min_h):
            dest.unlink(missing_ok=True)
            self.stats["skipped_filter"] += 1
            return "filter", None

        # 8) 지각적 해시 + (옵션) 유사중복 스킵
        phash = dedup.dhash(dest)
        threshold = int(coll.get("near_dup_threshold", 0) or 0)
        if threshold > 0 and phash:
            for _id, existing in db.all_phashes(self.conn):
                if dedup.hamming(phash, existing) <= threshold:
                    dest.unlink(missing_ok=True)
                    self.stats["skipped_dup"] += 1
                    return "dup", None

        # 9) 썸네일 (항상 .jpg)
        thumb_rel = Path(category) / (Path(filename).with_suffix(".jpg").name)
        thumb_dest = self.config.thumbnails_dir / thumb_rel
        thumb_ok = images.make_thumbnail(dest, thumb_dest, self.config.thumbnail_size)

        # 10) 저장
        info = licenses.summarize(r.license, r.license_version, r.license_url)
        record = {
            "source": r.source,
            "source_id": r.source_id,
            "category": category,
            "query": query,
            "title": r.title,
            "filename": filename,
            "filepath": str(rel_path),
            "thumbnail_path": str(thumb_rel) if thumb_ok else None,
            "url": r.url,
            "foreign_landing_url": r.foreign_landing_url,
            "width": width,
            "height": height,
            "filesize": size,
            "format": fmt or real_ext,
            "license": info["license"],
            "license_version": r.license_version,
            "license_url": info["license_url"],
            "commercial_use": 1 if info["commercial_use"] else 0,
            "modification": 1 if info["modification"] else 0,
            "attribution_required": 1 if info["attribution_required"] else 0,
            "creator": r.creator,
            "creator_url": r.creator_url,
            "attribution": r.attribution,
            "provider": r.provider,
            "sha256": sha,
            "phash": phash,
            "tags": _merge_tags(korean.korean_tags(category, query), extra_tags,
                                ", ".join(r.tags) if r.tags else None),
            # 소스가 준 원본(영어) 태그 — 카테고리 검수/재분류의 근거로 남긴다
            "source_tags": ", ".join(r.tags) if r.tags else None,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            image_id = db.insert_image(self.conn, record)
        except sqlite3.IntegrityError:
            dest.unlink(missing_ok=True)
            self.stats["skipped_dup"] += 1
            return "dup", None

        self.stats["downloaded"] += 1
        return "ok", image_id

    def _print_summary(self) -> None:
        s = self.stats
        console.print(
            f"\n[bold green]완료[/bold green] · 신규 {s['downloaded']}장 · "
            f"중복 스킵 {s['skipped_dup']} · 필터 제외 {s['skipped_filter']} · 오류 {s['errors']}"
        )

    # --- 낱말로 새 사진 찾기 (웹 뷰어 '새 사진 찾기' 버튼) ---
    def fetch_new(self, keyword: str, limit: int = 12, source_name: str | None = None,
                  category: str | None = None) -> dict:
        """한국어/영어 낱말을 받아 **관련도 높은 새 사진**을 내려받는다.

        수집(collect)과 다른 점:
          - 한국어 낱말을 시각적인 영어 검색어 여러 개로 번역 (translate.py)
          - 최신순이 아니라 **인기순**(관련도가 훨씬 좋다)
          - '2024년 이후' 연식 필터를 끈다 (관련도 우선)
          - 사용자가 친 낱말을 태그로 붙여, 다음부터는 로컬 검색으로 바로 나온다
        """
        plan = translate.to_queries(keyword, self.config)
        if not plan.queries:
            return {"keyword": keyword, "added": 0, "queries": [], "category": "",
                    "matched": False, "items": []}

        source_name = source_name or self.config.collection.get("default_source", "pixabay")
        source = get_source(source_name, self.config)
        ok, note = source.available()
        if not ok:
            raise RuntimeError(f"소스 '{source_name}' 사용 불가: {note}")

        # 관련도 우선 옵션 (pixabay 가 읽는다)
        setattr(source, "order_override", "popular")
        if plan.lang:
            setattr(source, "lang_override", plan.lang)

        category = category or plan.category
        # 낱말에 맞는 카테고리를 모를 때는('search') 사진 태그를 보고 알아서 배치한다.
        # (반도체 → technology, 치과 → medical)
        auto_category = category == "search"
        collected: list[dict] = []
        seen = already = 0     # 소스가 준 결과 수 / 그중 이미 갖고 있던 수
        per_query = max(2, -(-limit // len(plan.queries)))  # 검색어별로 고르게

        for query in plan.queries:
            if len(collected) >= limit:
                break
            got = 0
            try:
                for result in source.search(query, per_query * 5):
                    if got >= per_query or len(collected) >= limit:
                        break
                    seen += 1
                    target = category
                    if auto_category and result.tags:
                        ranked = classify.best_categories(classify.tag_set(", ".join(result.tags)))
                        # 근거가 약하면(1점) 억지로 배치하지 않고 search 에 둔다
                        if ranked and ranked[0][1] >= 2:
                            target = ranked[0][0]
                    status, image_id = self._process(
                        result, target, query,
                        ignore_recency=True, extra_tags=plan.keyword,
                    )
                    if status == "dup":
                        already += 1
                    elif status == "ok" and image_id:
                        rec = self.record_json(image_id)
                        if rec:
                            collected.append(rec)
                            got += 1
            except Exception as exc:
                console.print(f"[yellow]'{query}' 검색 중 경고:[/yellow] {exc}")

        return {
            "keyword": plan.keyword,
            "added": len(collected),
            "seen": seen,
            "already": already,
            "queries": plan.queries,
            "category": ("자동 분류" if auto_category else category),
            "matched": plan.matched,
            "via": plan.via,
            "items": collected,
        }

    # --- 키워드 검색 & 다운로드 (다른 Claude/자동화용) ---
    def search(self, keyword: str, limit: int = 5, category: str | None = None,
               source_name: str | None = None,
               attribution_free: bool = False) -> list[dict]:
        """키워드로 상업적 사용 가능 이미지를 limit 장 받아 저장하고, 각 이미지의
        메타데이터(dict) 목록을 반환. 이미 있는 이미지는 건너뛰고 새로 채운다."""
        coll = self.config.collection
        source_name = source_name or coll.get("default_source", "openverse")
        source = get_source(source_name, self.config)
        ok, note = source.available()
        if not ok:
            raise RuntimeError(f"소스 '{source_name}' 사용 불가: {note}")

        # 저작자 표기 불필요 이미지만 원하면 Openverse 라이선스도 CC0/PDM 로 좁힘
        if attribution_free:
            setattr(source, "license_override", "cc0,pdm")

        category = category or images.slugify(keyword, 40) or "search"
        collected: list[dict] = []
        seen_ids: set[int] = set()

        # 1) 새로 다운로드 시도 (넉넉히 요청 — 중복/필터로 빠지는 경우 대비)
        try:
            for result in source.search(keyword, max(limit * 4, limit + 8)):
                if len(collected) >= limit:
                    break
                status, image_id = self._process(
                    result, category, keyword, attribution_free=attribution_free
                )
                if status == "ok" and image_id:
                    rec = self.record_json(image_id)
                    if rec:
                        collected.append(rec)
                        seen_ids.add(image_id)
        except Exception as exc:
            console.print(f"[yellow]다운로드 중 경고:[/yellow] {exc}")

        # 2) 부족하면 라이브러리의 기존 이미지로 채움 (항상 사용 가능하도록)
        if len(collected) < limit:
            candidates = list(db.query_images(
                self.conn, category=category, commercial_only=True, limit=limit * 4
            ))
            # 키워드 텍스트 매칭도 보강
            candidates += list(db.query_images(
                self.conn, search=keyword, commercial_only=True, limit=limit * 4
            ))
            for row in candidates:
                if len(collected) >= limit:
                    break
                if row["id"] in seen_ids:
                    continue
                if attribution_free and row["attribution_required"]:
                    continue
                rec = self.record_json(row["id"])
                if rec:
                    collected.append(rec)
                    seen_ids.add(row["id"])

        return collected[:limit]

    def record_json(self, image_id: int) -> dict | None:
        """이미지 한 건을 기계가 읽기 좋은 dict 로 변환(절대경로 포함)."""
        row = db.get_image(self.conn, image_id)
        if not row:
            return None
        img_path = (self.config.images_dir / row["filepath"]).resolve()
        thumb = None
        if row["thumbnail_path"]:
            thumb = str((self.config.thumbnails_dir / row["thumbnail_path"]).resolve())
        return {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "keyword": row["query"],
            "path": str(img_path),
            "thumbnail": thumb,
            "width": row["width"],
            "height": row["height"],
            "format": row["format"],
            "source": row["source"],
            "source_url": row["foreign_landing_url"],
            "license": row["license"],
            "license_url": row["license_url"],
            "commercial_use": bool(row["commercial_use"]),
            "modification_allowed": bool(row["modification"]),
            "attribution_required": bool(row["attribution_required"]),
            "attribution": row["attribution"],
            "creator": row["creator"],
        }
