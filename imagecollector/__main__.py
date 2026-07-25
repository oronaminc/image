"""명령줄 인터페이스.

사용 예:
  python -m imagecollector init
  python -m imagecollector collect
  python -m imagecollector collect --source openverse --category nature --limit 30
  python -m imagecollector collect --query "cyberpunk city" --category custom
  python -m imagecollector serve
  python -m imagecollector stats
  python -m imagecollector export-attributions
  python -m imagecollector dedup --threshold 5
  python -m imagecollector sources
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import db
from .config import load_config
from .sources import all_sources, available_source_names

console = Console()
PKG_DIR = Path(__file__).parent
PROJECT_ROOT = PKG_DIR.parent


def cmd_init(args) -> None:
    """config.yaml / .env / 폴더 생성."""
    root = Path(args.dir).resolve() if args.dir else Path.cwd()
    for name in ("config.yaml", ".env"):
        src = PROJECT_ROOT / (name if name == "config.yaml" else ".env.example")
        dst = root / name
        if dst.exists():
            console.print(f"[yellow]이미 존재:[/yellow] {dst}")
            continue
        if src.exists():
            shutil.copy(src, dst)
            console.print(f"[green]생성:[/green] {dst}")
    config = load_config(root / "config.yaml")
    config.ensure_dirs()
    db.init_db(config.db_path)
    console.print(f"[green]폴더/DB 준비 완료:[/green] {config.images_dir}, {config.db_path}")
    console.print("\n다음 단계: [bold]python -m imagecollector collect[/bold]")


def cmd_collect(args) -> None:
    from .collector import Collector  # 무거운 임포트 지연
    config = load_config(args.config)
    collector = Collector(config)
    try:
        collector.run(
            source_name=args.source,
            categories=[args.category] if args.category else None,
            queries=args.query or None,
            limit=args.limit,
        )
    finally:
        collector.close()


def cmd_search(args) -> None:
    """키워드로 상업적 사용 가능 이미지 몇 장을 찾아 다운로드.

    --json 을 주면 결과를 JSON 으로 출력(다른 프로그램/AI 가 파싱하기 좋음).
    """
    import json
    from .collector import Collector
    config = load_config(args.config)
    collector = Collector(config)
    try:
        results = collector.search(
            keyword=args.keyword,
            limit=args.limit,
            category=args.category,
            source_name=args.source,
            attribution_free=args.no_attribution,
        )
    finally:
        collector.close()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        console.print(f"[yellow]'{args.keyword}' 에 대해 새로 받은 이미지가 없습니다.[/yellow] "
                      "(이미 수집됐거나 결과가 없을 수 있어요)")
        return
    console.print(f"\n[bold green]'{args.keyword}' · {len(results)}장 다운로드[/bold green]")
    for r in results:
        attr = "표기필요" if r["attribution_required"] else "표기불필요"
        console.print(f"  [green]✓[/green] {r['path']}")
        console.print(f"      [{r['license'].upper()}] {attr} · {r['width']}×{r['height']} · {r['source']}")
        if r["attribution_required"] and r["attribution"]:
            console.print(f"      표기: {r['attribution']}")


def cmd_serve(args) -> None:
    import uvicorn
    config = load_config(args.config)
    console.print(f"[bold cyan]웹 뷰어 시작[/bold cyan] → http://{args.host}:{args.port}")
    console.print(f"이미지 폴더: {config.images_dir}")
    # factory 로 config 를 넘기기 위해 환경변수 대신 직접 app 사용
    from .web.app import create_app
    app = create_app(config)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


def cmd_stats(args) -> None:
    config = load_config(args.config)
    db.init_db(config.db_path)
    conn = db.connect(config.db_path)
    try:
        s = db.stats(conn)
    finally:
        conn.close()
    console.print(f"\n[bold]전체:[/bold] {s['total']}장 · "
                  f"상업적 사용 가능 {s['commercial']} · 즐겨찾기 {s['favorites']} · "
                  f"총 {s['total_size']/1_048_576:.1f} MB\n")

    def table(title, rows):
        t = Table(title=title, title_style="bold cyan")
        t.add_column("이름"); t.add_column("개수", justify="right")
        for name, n in rows:
            t.add_row(str(name or "unknown"), str(n))
        console.print(t)

    table("카테고리별", s["by_category"])
    table("소스별", s["by_source"])
    table("라이선스별", s["by_license"])


def cmd_export_attr(args) -> None:
    from .web.app import build_attributions_md
    config = load_config(args.config)
    conn = db.connect(config.db_path)
    try:
        rows = db.attribution_rows(conn)
    finally:
        conn.close()
    out = Path(args.out) if args.out else (config.base_dir / "ATTRIBUTIONS.md")
    out.write_text(build_attributions_md(rows), encoding="utf-8")
    console.print(f"[green]저작자 표기 {len(rows)}건 저장:[/green] {out}")


def cmd_dedup(args) -> None:
    from . import dedup as dedup_mod
    config = load_config(args.config)
    conn = db.connect(config.db_path)
    try:
        hashes = db.all_phashes(conn)
        pairs = dedup_mod.find_near_duplicates(hashes, args.threshold)
        if not pairs:
            console.print("[green]유사 중복 없음.[/green]")
            return
        console.print(f"[yellow]유사 중복 {len(pairs)}쌍 발견 (임계값 {args.threshold})[/yellow]")
        to_delete = set()
        for a, b, dist in pairs:
            console.print(f"  #{a} ~ #{b}  (거리 {dist})")
            to_delete.add(b)  # 나중에 수집된 쪽 삭제 후보
        if args.delete:
            for image_id in sorted(to_delete):
                row = db.delete_image(conn, image_id)
                if row:
                    (config.images_dir / row["filepath"]).unlink(missing_ok=True)
                    if row["thumbnail_path"]:
                        (config.thumbnails_dir / row["thumbnail_path"]).unlink(missing_ok=True)
            console.print(f"[green]{len(to_delete)}장 삭제 완료.[/green]")
        else:
            console.print("실제 삭제하려면 [bold]--delete[/bold] 를 추가하세요.")
    finally:
        conn.close()


def cmd_prune(args) -> None:
    """조건에 맞는 이미지를 라이브러리+디스크에서 삭제.

    예:
      prune --source openverse            # 특정 소스 전부 삭제
      prune --category politics           # 특정 카테고리 삭제
      prune --source pixabay --max-source-id 8000000   # 오래된 Pixabay(저ID) 삭제
    """
    config = load_config(args.config)
    conn = db.connect(config.db_path)
    try:
        where, params = [], []
        if args.source:
            where.append("source = ?"); params.append(args.source)
        if args.category:
            where.append("category = ?"); params.append(args.category)
        if args.max_source_id is not None:
            where.append("CAST(source_id AS INTEGER) < ?"); params.append(args.max_source_id)
        if not where:
            console.print("[red]최소 하나의 필터가 필요합니다: --source / --category / --max-source-id[/red]")
            return
        clause = " AND ".join(where)
        rows = conn.execute(
            f"SELECT id, filepath, thumbnail_path FROM images WHERE {clause}", params
        ).fetchall()
        console.print(f"삭제 대상: [bold]{len(rows)}장[/bold]  (조건: {clause})")
        if not rows:
            return
        if args.dry_run:
            console.print("[yellow]--dry-run: 실제로는 삭제하지 않았습니다.[/yellow]")
            return
        n = 0
        for r in rows:
            (config.images_dir / r["filepath"]).unlink(missing_ok=True)
            if r["thumbnail_path"]:
                (config.thumbnails_dir / r["thumbnail_path"]).unlink(missing_ok=True)
            conn.execute("DELETE FROM images WHERE id = ?", (r["id"],))
            n += 1
        conn.commit()
        console.print(f"[green]{n}장 삭제 완료.[/green]")
    finally:
        conn.close()


def cmd_sources(args) -> None:
    config = load_config(args.config)
    t = Table(title="이미지 소스", title_style="bold cyan")
    t.add_column("소스"); t.add_column("상태"); t.add_column("설명")
    for src in all_sources(config):
        ok, note = src.available()
        status = "[green]사용 가능[/green]" if ok else "[red]키 필요[/red]"
        t.add_row(f"{src.name} ({src.label})", status, note)
    console.print(t)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="imagecollector",
                                description="상업적 사용 가능 무료 이미지 수집기 + 웹 뷰어")
    p.add_argument("--config", help="config.yaml 경로 (기본: ./config.yaml)")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("init", help="설정/폴더 초기화")
    sp.add_argument("--dir", help="초기화할 디렉터리 (기본: 현재 폴더)")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("collect", help="이미지 수집")
    sp.add_argument("--source", choices=available_source_names(), help="소스 (기본: config)")
    sp.add_argument("--category", help="특정 카테고리만 수집")
    sp.add_argument("--query", action="append", help="검색어 직접 지정 (여러 번 가능)")
    sp.add_argument("--limit", type=int, help="검색어당 이미지 수")
    sp.set_defaults(func=cmd_collect)

    sp = sub.add_parser("search", help="키워드로 이미지 검색·다운로드 (JSON 출력 가능)")
    sp.add_argument("keyword", help="검색 키워드 (예: \"government building\")")
    sp.add_argument("--limit", type=int, default=5, help="받을 이미지 수 (기본 5)")
    sp.add_argument("--category", help="저장 카테고리 (기본: 키워드 슬러그)")
    sp.add_argument("--source", choices=available_source_names(), help="소스 (기본: config)")
    sp.add_argument("--no-attribution", action="store_true",
                    help="저작자 표기 불필요(CC0/PDM 등) 이미지만")
    sp.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("serve", help="웹 뷰어 실행")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("stats", help="라이브러리 통계")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("export-attributions", help="저작자 표기 Markdown 내보내기")
    sp.add_argument("--out", help="출력 파일 (기본: ATTRIBUTIONS.md)")
    sp.set_defaults(func=cmd_export_attr)

    sp = sub.add_parser("dedup", help="지각적 해시로 유사 중복 탐지/삭제")
    sp.add_argument("--threshold", type=int, default=5, help="해밍거리 임계값 (작을수록 엄격)")
    sp.add_argument("--delete", action="store_true", help="실제로 삭제")
    sp.set_defaults(func=cmd_dedup)

    sp = sub.add_parser("prune", help="조건(소스/카테고리/ID)으로 이미지 삭제")
    sp.add_argument("--source", help="이 소스의 이미지 삭제 (예: openverse)")
    sp.add_argument("--category", help="이 카테고리의 이미지 삭제")
    sp.add_argument("--max-source-id", type=int,
                    help="source_id 가 이 값 미만인 것 삭제 (Pixabay 오래된 업로드 정리용)")
    sp.add_argument("--dry-run", action="store_true", help="삭제하지 않고 대상 수만 표시")
    sp.set_defaults(func=cmd_prune)

    sp = sub.add_parser("sources", help="사용 가능한 소스 목록")
    sp.set_defaults(func=cmd_sources)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]중단됨.[/yellow]")
        return 130
    except Exception as exc:
        console.print(f"[red]오류:[/red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
