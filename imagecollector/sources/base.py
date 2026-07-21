"""이미지 소스 공통 인터페이스."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Iterator

import requests

from ..config import Config
from ..models import ImageResult


class Source(ABC):
    #: 소스 식별자 (DB 에 저장됨)
    name: str = "base"
    #: 사람이 읽는 이름
    label: str = "Base"
    #: 이 소스가 상업적 사용 가능 이미지를 제공하는지
    commercial_safe: bool = True

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

    @abstractmethod
    def available(self) -> tuple[bool, str]:
        """(사용 가능 여부, 설명). 키가 필요한데 없으면 (False, 안내)."""

    @abstractmethod
    def search(self, query: str, limit: int) -> Iterator[ImageResult]:
        """검색어로 이미지 결과를 순회 반환."""

    # --- helpers ---
    def _get(self, url: str, params: dict | None = None, headers: dict | None = None,
             timeout: int = 30, max_retries: int = 3):
        """429/5xx 재시도 + Retry-After 존중."""
        delay = float(self.config.collection.get("request_delay", 0.6))
        for attempt in range(max_retries):
            resp = self.session.get(url, params=params, headers=headers, timeout=timeout)
            # 429(rate limit), 401/403(스로틀링 시 발생), 5xx 는 백오프 후 재시도
            if resp.status_code in (401, 403, 429) or resp.status_code >= 500:
                wait = resp.headers.get("Retry-After")
                sleep_for = float(wait) if wait and wait.isdigit() else (delay * (2 ** attempt) + 1)
                time.sleep(min(sleep_for, 30))
                continue
            resp.raise_for_status()
            if delay:
                time.sleep(delay)
            return resp
        resp.raise_for_status()
        return resp
