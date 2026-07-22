"""Unsplash 소스 — 고품질 사진. 무료 API 키 필요(UNSPLASH_ACCESS_KEY).

Unsplash License: 상업적 사용 무료. 단, API 가이드라인상 저작자 표기가 강력히 권장되며
데모/재배포 관련 제약이 있으니 https://unsplash.com/license 및 API 약관을 확인하세요.
"""
from __future__ import annotations

from typing import Iterator

from ..models import ImageResult
from .base import Source

API = "https://api.unsplash.com/search/photos"


class UnsplashSource(Source):
    name = "unsplash"
    label = "Unsplash"
    commercial_safe = True
    rate_delay = 2.0  # 데모 50회/시 · 승인 후 상향

    def available(self) -> tuple[bool, str]:
        if self.config.env("UNSPLASH_ACCESS_KEY"):
            return True, "UNSPLASH_ACCESS_KEY 설정됨"
        return False, "UNSPLASH_ACCESS_KEY 필요 (https://unsplash.com/developers)"

    def search(self, query: str, limit: int) -> Iterator[ImageResult]:
        key = self.config.env("UNSPLASH_ACCESS_KEY")
        if not key:
            return
        headers = {"Authorization": f"Client-ID {key}",
                   "Accept-Version": "v1"}
        content_filter = "high" if self.config.collection.get("safe_search", True) else "low"
        per_page = min(max(limit, 10), 30)
        page = 1
        yielded = 0
        while yielded < limit and page <= 50:
            params = {"query": query, "per_page": per_page, "page": page,
                      "content_filter": content_filter}
            try:
                resp = self._get(API, params=params, headers=headers)
            except Exception:
                break
            data = resp.json()
            results = data.get("results") or []
            if not results:
                break
            for photo in results:
                urls = photo.get("urls") or {}
                url = urls.get("raw") or urls.get("full") or urls.get("regular")
                if not url:
                    continue
                user = photo.get("user") or {}
                creator = user.get("name")
                landing = (photo.get("links") or {}).get("html")
                yield ImageResult(
                    source=self.name,
                    source_id=str(photo.get("id")),
                    url=url,
                    title=photo.get("description") or photo.get("alt_description") or query,
                    thumbnail_url=urls.get("small") or urls.get("thumb"),
                    foreign_landing_url=landing,
                    width=photo.get("width"),
                    height=photo.get("height"),
                    filesize=None,
                    filetype="jpg",
                    license="unsplash",
                    license_version=None,
                    license_url="https://unsplash.com/license",
                    creator=creator,
                    creator_url=(user.get("links") or {}).get("html"),
                    attribution=f'Photo by {creator} on Unsplash ({landing})' if creator else None,
                    provider="Unsplash",
                    tags=[t.get("title") for t in (photo.get("tags") or []) if t.get("title")],
                )
                yielded += 1
                if yielded >= limit:
                    return
            total_pages = data.get("total_pages", 0)
            if page >= total_pages:
                break
            page += 1
