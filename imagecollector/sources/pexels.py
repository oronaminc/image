"""Pexels 소스 — 고품질 사진. 무료 API 키 필요(PEXELS_API_KEY).

Pexels License: 상업적 사용 무료, 저작자 표기 불필요(권장). https://www.pexels.com/license/
"""
from __future__ import annotations

from typing import Iterator

from ..models import ImageResult
from .base import Source

API = "https://api.pexels.com/v1/search"


class PexelsSource(Source):
    name = "pexels"
    label = "Pexels"
    commercial_safe = True

    def available(self) -> tuple[bool, str]:
        if self.config.env("PEXELS_API_KEY"):
            return True, "PEXELS_API_KEY 설정됨"
        return False, "PEXELS_API_KEY 필요 (https://www.pexels.com/api/)"

    def search(self, query: str, limit: int) -> Iterator[ImageResult]:
        key = self.config.env("PEXELS_API_KEY")
        if not key:
            return
        headers = {"Authorization": key}
        per_page = min(max(limit, 15), 80)
        page = 1
        yielded = 0
        while yielded < limit and page <= 50:
            params = {"query": query, "per_page": per_page, "page": page}
            try:
                resp = self._get(API, params=params, headers=headers)
            except Exception:
                break
            data = resp.json()
            photos = data.get("photos") or []
            if not photos:
                break
            for photo in photos:
                src = photo.get("src") or {}
                url = src.get("original") or src.get("large2x") or src.get("large")
                if not url:
                    continue
                creator = photo.get("photographer")
                landing = photo.get("url")
                yield ImageResult(
                    source=self.name,
                    source_id=str(photo.get("id")),
                    url=url,
                    title=photo.get("alt") or query,
                    thumbnail_url=src.get("medium") or src.get("small"),
                    foreign_landing_url=landing,
                    width=photo.get("width"),
                    height=photo.get("height"),
                    filesize=None,
                    filetype="jpg",
                    license="pexels",
                    license_version=None,
                    license_url="https://www.pexels.com/license/",
                    creator=creator,
                    creator_url=photo.get("photographer_url"),
                    attribution=f'Photo by {creator} on Pexels ({landing})' if creator else None,
                    provider="Pexels",
                    tags=[],
                )
                yielded += 1
                if yielded >= limit:
                    return
            if not data.get("next_page"):
                break
            page += 1
