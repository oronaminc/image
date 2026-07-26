"""Wikimedia Commons 소스 — 퍼블릭도메인/CC 이미지. API 키 불필요.

문서: https://commons.wikimedia.org/w/api.php
generator=search 로 파일을 찾고 imageinfo(extmetadata)로 라이선스를 읽는다.
"""
from __future__ import annotations

import re
from typing import Iterator

from .. import licenses
from ..models import ImageResult
from .base import Source

API = "https://commons.wikimedia.org/w/api.php"

# 가장 구체적인 코드부터 검사 (cc-by-sa 를 cc-by 보다 먼저)
_LICENSE_KEYS = (
    "cc-by-nc-sa", "cc-by-nc-nd", "cc-by-nc", "cc-by-nd", "cc-by-sa", "cc-by",
)


def _extract_year(*texts: str | None) -> int | None:
    """날짜/제목 문자열들에서 첫 4자리 연도(19xx/20xx)를 추출."""
    for t in texts:
        if not t:
            continue
        clean = re.sub(r"<[^>]+>", " ", t)
        m = re.search(r"(?:19|20)\d{2}", clean)
        if m:
            return int(m.group(0))
    return None


def _norm_license(short_name: str | None) -> str:
    """Wikimedia 의 LicenseShortName(예: 'CC BY 4.0', 'CC0', 'Public domain')을 정규화."""
    s = (short_name or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)          # 공백/언더스코어 -> 하이픈
    if "cc0" in s or "cc-zero" in s:
        return "cc0"
    if "public-domain" in s or s == "pd" or "publicdomain" in s:
        return "pdm"
    for key in _LICENSE_KEYS:
        if s.startswith(key):
            return key.replace("cc-", "")   # cc-by-sa -> by-sa
    return s


class WikimediaSource(Source):
    name = "wikimedia"
    label = "Wikimedia Commons"
    commercial_safe = True
    rate_delay = 0.6  # 넉넉한 편

    def available(self) -> tuple[bool, str]:
        return True, "키 없이 사용 가능"

    def search(self, query: str, limit: int) -> Iterator[ImageResult]:
        coll = self.config.collection
        batch = min(max(limit, 10), 50)
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,          # File:
            "gsrlimit": batch,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata|user",
            "iiurlwidth": 800,
        }
        yielded = 0
        while yielded < limit:
            try:
                resp = self._get(API, params=params)
            except Exception:
                break
            data = resp.json()
            pages = (data.get("query") or {}).get("pages") or {}
            if not pages:
                break
            for page in pages.values():
                result = self._to_result(page)
                if result is None:
                    continue
                yield result
                yielded += 1
                if yielded >= limit:
                    return
            cont = data.get("continue")
            if not cont:
                break
            params.update(cont)

    def _to_result(self, page: dict) -> ImageResult | None:
        infos = page.get("imageinfo") or []
        if not infos:
            return None
        info = infos[0]
        meta = info.get("extmetadata") or {}

        def mval(key: str) -> str | None:
            v = meta.get(key)
            return v.get("value") if isinstance(v, dict) else None

        code = _norm_license(mval("LicenseShortName"))
        if not licenses.is_commercial_ok(code):
            return None  # NC 등 상업적 사용 불가 제외

        title = (page.get("title") or "").replace("File:", "")

        # 연도 필터 (예: 2024 이후만). 연도 불명이면 엄격히 제외.
        min_year = int(self.config.collection.get("min_year", 0) or 0)
        if min_year:
            year = _extract_year(mval("DateTimeOriginal"), mval("DateTime"), title)
            if not year or year < min_year:
                return None
        creator = mval("Artist")
        if creator:
            creator = re.sub(r"<[^>]+>", "", creator).strip()  # HTML 태그 제거

        summary = licenses.summarize(code, None, mval("LicenseUrl"))
        landing = info.get("descriptionurl")
        attribution = licenses.build_attribution(
            title, creator, code, None, landing, summary["license_url"]
        )
        return ImageResult(
            source=self.name,
            source_id=str(page.get("pageid")),
            url=info.get("url"),
            title=title,
            thumbnail_url=info.get("thumburl"),
            foreign_landing_url=landing,
            width=info.get("width"),
            height=info.get("height"),
            filesize=info.get("size"),
            filetype=(info.get("mime") or "").split("/")[-1] or None,
            license=summary["license"],
            license_version=None,
            license_url=summary["license_url"],
            creator=creator,
            creator_url=None,
            attribution=attribution,
            provider="Wikimedia Commons",
            tags=[],
        )
