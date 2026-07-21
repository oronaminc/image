"""수집 오케스트레이션: 검색 -> 라이선스/크기 필터 -> 다운로드 -> 중복검사 -> 저장."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from . import db, dedup, images, licenses
from .config import Config
from .models import ImageResult
from .sources import get_source

console = Console()


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
                status = self._process(result, category, query)
                if status == "ok":
                    got += 1
                    console.print(f"  [green]✓[/green] {got}/{limit}  {result.title[:60] or result.source_id}")
        except Exception as exc:  # 소스 오류가 전체를 멈추지 않도록
            console.print(f"  [red]소스 오류:[/red] {exc}")

        if got == 0:
            console.print("  [yellow](수집된 이미지 없음)[/yellow]")

    def _process(self, r: ImageResult, category: str, query: str) -> str:
        coll = self.config.collection

        # 1) 이미 있는 항목(같은 소스+id) 건너뜀
        if db.exists_source_id(self.conn, r.source, r.source_id):
            self.stats["skipped_dup"] += 1
            return "dup"

        # 2) 상업적 사용 안전장치
        if coll.get("license_type", "commercial").startswith("commercial"):
            if not licenses.is_commercial_ok(r.license) and r.source in ("openverse", "wikimedia"):
                self.stats["skipped_filter"] += 1
                return "filter"

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
            return "filter"

        # 5) 다운로드 (임시 이름 → 검증 후 확정)
        filename = images.make_filename(category, r.title, r.source, r.source_id, ext)
        rel_path = Path(category) / filename
        dest = self.config.images_dir / rel_path
        try:
            sha, size, content_type = images.download(self.session, r.url, dest)
        except Exception:
            self.stats["errors"] += 1
            return "error"

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
            return "dup"

        # 7) 실제 이미지 검증 + 크기/포맷
        probe = images.probe_image(dest)
        if probe is None:
            dest.unlink(missing_ok=True)
            self.stats["errors"] += 1
            return "error"
        width, height, fmt = probe
        if (min_w and width < min_w) or (min_h and height < min_h):
            dest.unlink(missing_ok=True)
            self.stats["skipped_filter"] += 1
            return "filter"

        # 8) 지각적 해시 + (옵션) 유사중복 스킵
        phash = dedup.dhash(dest)
        threshold = int(coll.get("near_dup_threshold", 0) or 0)
        if threshold > 0 and phash:
            for _id, existing in db.all_phashes(self.conn):
                if dedup.hamming(phash, existing) <= threshold:
                    dest.unlink(missing_ok=True)
                    self.stats["skipped_dup"] += 1
                    return "dup"

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
            "tags": ", ".join(r.tags) if r.tags else None,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            db.insert_image(self.conn, record)
        except sqlite3.IntegrityError:
            dest.unlink(missing_ok=True)
            self.stats["skipped_dup"] += 1
            return "dup"

        self.stats["downloaded"] += 1
        return "ok"

    def _print_summary(self) -> None:
        s = self.stats
        console.print(
            f"\n[bold green]완료[/bold green] · 신규 {s['downloaded']}장 · "
            f"중복 스킵 {s['skipped_dup']} · 필터 제외 {s['skipped_filter']} · 오류 {s['errors']}"
        )
