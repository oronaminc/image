"""Pixabay 소스 — 사진/일러스트/벡터. 무료 API 키 필요(PIXABAY_API_KEY).

Pixabay Content License: 상업적 사용 무료, 저작자 표기 불필요. https://pixabay.com/service/license-summary/
"""
from __future__ import annotations

from typing import Iterator

from ..models import ImageResult
from .base import Source

API = "https://pixabay.com/api/"


class PixabaySource(Source):
    name = "pixabay"
    label = "Pixabay"
    commercial_safe = True
    rate_delay = 0.8  # 100회/분 허용 → 빠르게

    def available(self) -> tuple[bool, str]:
        if self.config.env("PIXABAY_API_KEY"):
            return True, "PIXABAY_API_KEY 설정됨"
        return False, "PIXABAY_API_KEY 필요 (https://pixabay.com/api/docs/)"

    def search(self, query: str, limit: int) -> Iterator[ImageResult]:
        key = self.config.env("PIXABAY_API_KEY")
        if not key:
            return
        safe = "true" if self.config.collection.get("safe_search", True) else "false"
        per_page = min(max(limit, 20), 200)
        page = 1
        yielded = 0
        while yielded < limit and page <= 50:
            params = {
                "key": key,
                "q": query,
                "image_type": "photo",
                "safesearch": safe,
                "per_page": per_page,
                "page": page,
                # popular(인기순, 기본) | latest(최신 업로드순)
                "order": self.config.collection.get("order", "popular"),
            }
            try:
                resp = self._get(API, params=params)
            except Exception:
                break
            data = resp.json()
            hits = data.get("hits") or []
            if not hits:
                break
            for hit in hits:
                url = hit.get("largeImageURL") or hit.get("webformatURL")
                if not url:
                    continue
                creator = hit.get("user")
                landing = hit.get("pageURL")
                tags = [t.strip() for t in (hit.get("tags") or "").split(",") if t.strip()]
                yield ImageResult(
                    source=self.name,
                    source_id=str(hit.get("id")),
                    url=url,
                    title=(tags[0] if tags else query),
                    thumbnail_url=hit.get("webformatURL") or hit.get("previewURL"),
                    foreign_landing_url=landing,
                    width=hit.get("imageWidth"),
                    height=hit.get("imageHeight"),
                    filesize=hit.get("imageSize"),
                    filetype="jpg",
                    license="pixabay",
                    license_version=None,
                    license_url="https://pixabay.com/service/license-summary/",
                    creator=creator,
                    creator_url=f"https://pixabay.com/users/{creator}-{hit.get('user_id')}/" if creator else None,
                    attribution=f'Image by {creator} from Pixabay' if creator else None,
                    provider="Pixabay",
                    tags=tags,
                )
                yielded += 1
                if yielded >= limit:
                    return
            total = data.get("totalHits", 0)
            if page * per_page >= total:
                break
            page += 1
