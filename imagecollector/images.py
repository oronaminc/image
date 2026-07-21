"""이미지 다운로드 · 파일명 규칙 · 썸네일 생성."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import requests
from PIL import Image, ImageOps

# Pillow 로 열 수 있는(=썸네일 가능한) 포맷만 취급. svg 등은 제외.
SUPPORTED_EXT = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"}

_CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/tiff": "tiff",
}


def slugify(text: str, max_len: int = 50) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    if not text:
        text = "untitled"
    return text[:max_len].strip("-") or "untitled"


def guess_ext(url: str, content_type: str | None, filetype: str | None) -> str | None:
    if filetype:
        ft = filetype.lower().lstrip(".")
        if ft == "jpeg":
            ft = "jpg"
        if ft in SUPPORTED_EXT:
            return ft
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if ct in _CONTENT_TYPE_EXT:
            return _CONTENT_TYPE_EXT[ct]
    # url 확장자
    tail = url.split("?")[0].rsplit(".", 1)
    if len(tail) == 2:
        ext = tail[1].lower()
        if ext == "jpeg":
            ext = "jpg"
        if ext in SUPPORTED_EXT:
            return ext
    return None


def make_filename(category: str, title: str, source: str, source_id: str, ext: str) -> str:
    base = slugify(title, 50)
    sid = re.sub(r"[^a-zA-Z0-9]+", "", str(source_id))[-16:] or "0"
    return f"{base}__{source}-{sid}.{ext}"


def make_session(user_agent: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": user_agent, "Accept": "image/*,*/*"})
    return s


def download(session: requests.Session, url: str, dest: Path,
             timeout: int = 30) -> tuple[str, int, str | None]:
    """스트리밍 다운로드하며 sha256 계산.

    반환: (sha256, bytes, content_type)
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    hasher = hashlib.sha256()
    total = 0
    with session.get(url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type")
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(65536):
                if chunk:
                    hasher.update(chunk)
                    total += len(chunk)
                    fh.write(chunk)
    return hasher.hexdigest(), total, content_type


def probe_image(path: Path) -> tuple[int, int, str] | None:
    """실제 이미지 크기/포맷 확인. 열 수 없으면 None."""
    try:
        with Image.open(path) as img:
            img.verify()  # 손상 여부 확인
        with Image.open(path) as img:
            w, h = img.size
            fmt = (img.format or "").lower()
        return w, h, fmt
    except Exception:
        return None


def make_thumbnail(src: Path, dest: Path, size: int = 400) -> bool:
    """긴 변 기준 size 픽셀 썸네일(JPEG) 생성."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((size, size), Image.LANCZOS)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                rgba = img.convert("RGBA")
                background.paste(rgba, mask=rgba.split()[-1])
                img = background
            else:
                img = img.convert("RGB")
            img.save(dest, "JPEG", quality=82, optimize=True)
        return True
    except Exception:
        return False
