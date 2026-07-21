"""소스 간 공통으로 쓰는 정규화된 데이터 구조."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImageResult:
    """어떤 소스에서 오든 이 형태로 정규화한다."""
    source: str                       # 'openverse', 'wikimedia', ...
    source_id: str                    # 소스 내 고유 id
    url: str                          # 원본 이미지 URL
    title: str = ""
    thumbnail_url: str | None = None
    foreign_landing_url: str | None = None   # 원본 페이지 URL
    width: int | None = None
    height: int | None = None
    filesize: int | None = None
    filetype: str | None = None       # 'jpg', 'png', ...
    license: str = ""                 # 정규화된 코드: cc0, by, by-sa, pdm ...
    license_version: str | None = None
    license_url: str | None = None
    creator: str | None = None
    creator_url: str | None = None
    attribution: str | None = None    # 완성형 저작자 표기 문자열
    provider: str | None = None       # 상위 제공처(flickr, wikimedia 등)
    tags: list[str] = field(default_factory=list)
