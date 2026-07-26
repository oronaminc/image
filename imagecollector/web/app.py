"""FastAPI 기반 웹 뷰어."""
from __future__ import annotations

import math
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import db
from ..config import Config, load_config

HERE = Path(__file__).parent
PAGE_SIZE = 60


def human_size(num: int | None) -> str:
    if not num:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def create_app(config: Config | None = None) -> FastAPI:
    config = config or load_config()
    config.ensure_dirs()
    db.init_db(config.db_path)

    app = FastAPI(title="Image Collector")
    templates = Jinja2Templates(directory=str(HERE / "templates"))
    templates.env.filters["human_size"] = human_size

    # 정적 파일 마운트
    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
    app.mount("/media/images", StaticFiles(directory=str(config.images_dir)), name="images")
    app.mount("/media/thumbnails", StaticFiles(directory=str(config.thumbnails_dir)), name="thumbnails")

    def conn():
        return db.connect(config.db_path)

    def media_urls(row) -> dict:
        d = dict(row)
        d["image_url"] = f"/media/images/{row['filepath']}"
        d["thumb_url"] = (
            f"/media/thumbnails/{row['thumbnail_path']}" if row["thumbnail_path"]
            else f"/media/images/{row['filepath']}"
        )
        return d

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, category: str = "", source: str = "",
              license: str = "", q: str = "", favorite: int = 0,
              order: str = "recent", page: int = 1):
        c = conn()
        try:
            filters = dict(
                category=category or None,
                source=source or None,
                license_code=license or None,
                favorite=bool(favorite),
                search=q or None,
            )
            total = db.count_images(c, **filters)
            pages = max(1, math.ceil(total / PAGE_SIZE))
            page = max(1, min(page, pages))
            rows = db.query_images(
                c, **filters, order=order,
                limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE,
            )
            items = [media_urls(r) for r in rows]
            context = {
                "request": request,
                "items": items,
                "total": total,
                "page": page,
                "pages": pages,
                "categories": db.distinct_values(c, "category"),
                "sources": db.distinct_values(c, "source"),
                "licenses": db.distinct_values(c, "license"),
                "f": {"category": category, "source": source, "license": license,
                      "q": q, "favorite": favorite, "order": order},
                "stats": db.stats(c),
            }
            return templates.TemplateResponse("index.html", context)
        finally:
            c.close()

    @app.get("/image/{image_id}", response_class=HTMLResponse)
    def detail(request: Request, image_id: int):
        c = conn()
        try:
            row = db.get_image(c, image_id)
            if not row:
                return HTMLResponse("<h1>이미지를 찾을 수 없습니다</h1>", status_code=404)
            return templates.TemplateResponse(
                "detail.html", {"request": request, "img": media_urls(row)}
            )
        finally:
            c.close()

    @app.post("/api/image/{image_id}/favorite")
    def toggle_favorite(image_id: int, value: int = Form(...)):
        c = conn()
        try:
            db.set_favorite(c, image_id, bool(value))
            return JSONResponse({"ok": True, "favorite": bool(value)})
        finally:
            c.close()

    @app.post("/api/image/{image_id}/rating")
    def set_rating(image_id: int, value: int = Form(...)):
        c = conn()
        try:
            db.set_rating(c, image_id, value)
            return JSONResponse({"ok": True, "rating": value})
        finally:
            c.close()

    @app.post("/api/image/{image_id}/delete")
    def delete(image_id: int):
        c = conn()
        try:
            row = db.delete_image(c, image_id)
            if row:
                (config.images_dir / row["filepath"]).unlink(missing_ok=True)
                if row["thumbnail_path"]:
                    (config.thumbnails_dir / row["thumbnail_path"]).unlink(missing_ok=True)
            return JSONResponse({"ok": True})
        finally:
            c.close()

    @app.get("/api/count")
    def api_count(category: str = "", source: str = "", license: str = "",
                  q: str = "", favorite: int = 0):
        """현재 필터 기준 총 개수 (라이브 갱신 폴링용)."""
        c = conn()
        try:
            n = db.count_images(
                c, category=category or None, source=source or None,
                license_code=license or None, favorite=bool(favorite),
                search=q or None,
            )
            return JSONResponse({"count": n})
        finally:
            c.close()

    @app.post("/api/fetch")
    def api_fetch(keyword: str = Form(...), limit: int = Form(12)):
        """낱말(한국어 OK) 로 관련된 **새 사진**을 인터넷에서 찾아 라이브러리에 추가.

        '지원금' 처럼 스톡 사이트에 없는 추상 개념은 translate.py 가 눈에 보이는
        영어 검색어들로 바꿔 준다.
        """
        from ..collector import Collector  # 무거운 임포트 지연
        word = (keyword or "").strip()
        if not word:
            return JSONResponse({"ok": False, "error": "낱말을 입력하세요."}, status_code=400)
        collector = Collector(config)
        try:
            result = collector.fetch_new(word, limit=max(1, min(int(limit or 12), 50)))
        except RuntimeError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        finally:
            collector.close()
        return JSONResponse({
            "ok": True,
            "keyword": result["keyword"],
            "added": result["added"],
            "seen": result["seen"],
            "already": result["already"],
            "queries": result["queries"],
            "category": result["category"],
            "matched": result["matched"],
            "via": result["via"],
        })

    @app.get("/stats", response_class=HTMLResponse)
    def stats_page(request: Request):
        c = conn()
        try:
            return templates.TemplateResponse(
                "stats.html", {"request": request, "stats": db.stats(c)}
            )
        finally:
            c.close()

    @app.get("/attributions", response_class=HTMLResponse)
    def attributions(request: Request):
        c = conn()
        try:
            rows = [media_urls(r) for r in db.attribution_rows(c)]
            return templates.TemplateResponse(
                "attributions.html", {"request": request, "rows": rows}
            )
        finally:
            c.close()

    @app.get("/attributions.md", response_class=PlainTextResponse)
    def attributions_md():
        c = conn()
        try:
            return PlainTextResponse(build_attributions_md(db.attribution_rows(c)))
        finally:
            c.close()

    return app


def build_attributions_md(rows) -> str:
    lines = ["# 이미지 저작자 표기 (Attributions)", ""]
    lines.append("아래 이미지는 라이선스에 따라 저작자 표기가 필요합니다.")
    lines.append("퍼블릭 도메인(CC0/PDM) 이미지는 표기 의무가 없어 목록에서 제외됩니다.")
    lines.append("")
    current = None
    for r in rows:
        if r["category"] != current:
            current = r["category"]
            lines.append(f"\n## {current}\n")
        attr = r["attribution"] or f'{r["title"]} — {r["license"]}'
        lines.append(f"- **{r['filename']}**: {attr}")
    return "\n".join(lines) + "\n"


# uvicorn 임포트 문자열용 (python -m imagecollector serve 는 factory 사용)
app = create_app()
