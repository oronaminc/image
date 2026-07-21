"""설정 로딩: config.yaml + .env 를 읽어 Config 객체로 제공."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

DEFAULTS: dict = {
    "storage": {
        "images_dir": "images",
        "thumbnails_dir": "thumbnails",
        "database": "library.db",
        "thumbnail_size": 400,
    },
    "collection": {
        "default_source": "openverse",
        "license_type": "commercial",
        "safe_search": True,
        "per_category_limit": 40,
        "min_width": 0,
        "min_height": 0,
        "request_delay": 0.6,
        "near_dup_threshold": 0,
        "user_agent": "ImageCollector/1.0 (+https://github.com/oronaminc/image)",
    },
    "categories": {},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class Config:
    base_dir: Path
    raw: dict

    # --- storage paths (absolute) ---
    @property
    def images_dir(self) -> Path:
        return self.base_dir / self.raw["storage"]["images_dir"]

    @property
    def thumbnails_dir(self) -> Path:
        return self.base_dir / self.raw["storage"]["thumbnails_dir"]

    @property
    def db_path(self) -> Path:
        return self.base_dir / self.raw["storage"]["database"]

    @property
    def thumbnail_size(self) -> int:
        return int(self.raw["storage"]["thumbnail_size"])

    # --- sections ---
    @property
    def collection(self) -> dict:
        return self.raw["collection"]

    @property
    def categories(self) -> dict:
        return self.raw.get("categories") or {}

    @property
    def user_agent(self) -> str:
        return self.collection.get("user_agent") or DEFAULTS["collection"]["user_agent"]

    def env(self, key: str, default: str | None = None) -> str | None:
        value = os.environ.get(key, default)
        return value if value else default

    def ensure_dirs(self) -> None:
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)


DEFAULT_CONFIG_NAME = "config.yaml"


def find_config(path: str | os.PathLike | None = None) -> Path:
    """config.yaml 위치를 찾는다. 없으면 cwd 기준 경로를 반환(생성용)."""
    if path:
        return Path(path).resolve()
    cwd_cfg = Path.cwd() / DEFAULT_CONFIG_NAME
    return cwd_cfg.resolve()


def load_config(path: str | os.PathLike | None = None) -> Config:
    cfg_path = find_config(path)
    base_dir = cfg_path.parent
    raw = dict(DEFAULTS)
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as fh:
            user_cfg = yaml.safe_load(fh) or {}
        raw = _deep_merge(DEFAULTS, user_cfg)
    # .env (base_dir 우선, 없으면 cwd)
    env_path = base_dir / ".env"
    load_dotenv(env_path if env_path.exists() else None)
    return Config(base_dir=base_dir, raw=raw)
