"""소스 레지스트리."""
from __future__ import annotations

from ..config import Config
from .base import Source
from .openverse import OpenverseSource
from .pexels import PexelsSource
from .pixabay import PixabaySource
from .unsplash import UnsplashSource
from .wikimedia import WikimediaSource

_REGISTRY = {
    OpenverseSource.name: OpenverseSource,
    WikimediaSource.name: WikimediaSource,
    PexelsSource.name: PexelsSource,
    PixabaySource.name: PixabaySource,
    UnsplashSource.name: UnsplashSource,
}


def available_source_names() -> list[str]:
    return list(_REGISTRY.keys())


def get_source(name: str, config: Config) -> Source:
    key = (name or "").lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"알 수 없는 소스: {name!r}. 사용 가능: {', '.join(_REGISTRY)}"
        )
    return _REGISTRY[key](config)


def all_sources(config: Config) -> list[Source]:
    return [cls(config) for cls in _REGISTRY.values()]
