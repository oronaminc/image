"""Openverse 소스 — CC/퍼블릭도메인 이미지 통합 검색. API 키 불필요.

문서: https://api.openverse.org/v1/
- license_type=commercial 로 상업적 사용 가능 이미지만 요청.
- 선택적으로 OPENVERSE_CLIENT_ID/SECRET 이 있으면 토큰을 받아 rate limit 상향.
"""
from __future__ import annotations

import time
from typing import Iterator

from .. import licenses
from ..models import ImageResult
from .base import Source

API_BASE = "https://api.openverse.org/v1"


class OpenverseSource(Source):
    name = "openverse"
    label = "Openverse"
    commercial_safe = True

    def __init__(self, config):
        super().__init__(config)
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def available(self) -> tuple[bool, str]:
        return True, "키 없이 사용 가능 (클라이언트 등록 시 rate limit 상향)"

    def _ensure_token(self) -> None:
        cid = self.config.env("OPENVERSE_CLIENT_ID")
        secret = self.config.env("OPENVERSE_CLIENT_SECRET")
        if not cid or not secret:
            return
        # 유효 토큰이 있으면 재사용
        if self._token and time.monotonic() < self._token_expiry - 30:
            return
        try:
            resp = self.session.post(
                f"{API_BASE}/auth_tokens/token/",
                data={
                    "grant_type": "client_credentials",
                    "client_id": cid,
                    "client_secret": secret,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data.get("access_token")
            self._token_expiry = time.monotonic() + float(data.get("expires_in", 3600))
        except Exception:
            self._token = None  # 실패 시 익명으로 진행

    def _headers(self) -> dict:
        self._ensure_token()
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def search(self, query: str, limit: int) -> Iterator[ImageResult]:
        coll = self.config.collection
        license_type = coll.get("license_type", "commercial")
        mature = "false" if coll.get("safe_search", True) else "true"
        page_size = min(max(limit, 20), 100)

        yielded = 0
        page = 1
        while yielded < limit and page <= 20:
            params = {
                "q": query,
                "page": page,
                "page_size": page_size,
                "mature": mature,
            }
            # attribution-free 검색 등에서 특정 라이선스만 요청(예: cc0,pdm)
            license_override = getattr(self, "license_override", None)
            if license_override:
                params["license"] = license_override
            else:
                params["license_type"] = license_type
            try:
                resp = self._get(f"{API_BASE}/images/", params=params,
                                 headers=self._headers())
            except Exception:
                break
            data = resp.json()
            results = data.get("results") or []
            if not results:
                break
            for item in results:
                result = self._to_result(item, query)
                if result is None:
                    continue
                yield result
                yielded += 1
                if yielded >= limit:
                    break
            if not data.get("page_count") or page >= data["page_count"]:
                break
            page += 1

    def _to_result(self, item: dict, query: str) -> ImageResult | None:
        url = item.get("url")
        if not url:
            return None
        code = item.get("license")
        version = item.get("license_version")
        # 상업적 사용 불가 라이선스는 안전장치로 한 번 더 걸러냄
        if not licenses.is_commercial_ok(code):
            return None
        info = licenses.summarize(code, version, item.get("license_url"))
        tags = [t.get("name") for t in (item.get("tags") or []) if t.get("name")]
        attribution = item.get("attribution") or licenses.build_attribution(
            item.get("title"), item.get("creator"), code, version,
            item.get("foreign_landing_url"), info["license_url"],
        )
        return ImageResult(
            source=self.name,
            source_id=str(item.get("id")),
            url=url,
            title=item.get("title") or "",
            thumbnail_url=item.get("thumbnail"),
            foreign_landing_url=item.get("foreign_landing_url"),
            width=item.get("width"),
            height=item.get("height"),
            filesize=item.get("filesize"),
            filetype=item.get("filetype"),
            license=info["license"],
            license_version=version,
            license_url=info["license_url"],
            creator=item.get("creator"),
            creator_url=item.get("creator_url"),
            attribution=attribution,
            provider=item.get("provider") or item.get("source"),
            tags=tags,
        )
