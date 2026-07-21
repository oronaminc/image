"""중복 제거용 해시.

- sha256: 바이트 단위 정확한 중복 판별 (다운로드 중 계산)
- dhash: 지각적 해시(difference hash)로 유사 중복 판별. numpy/scipy 없이 순수 파이썬.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image


def dhash(path: str | Path, size: int = 8) -> str | None:
    """이미지의 64비트 difference hash 를 16진 문자열로 반환. 실패 시 None."""
    try:
        with Image.open(path) as img:
            small = img.convert("L").resize((size + 1, size), Image.LANCZOS)
        pixels = list(small.getdata())
        bits = 0
        width = size + 1
        for row in range(size):
            base = row * width
            for col in range(size):
                left = pixels[base + col]
                right = pixels[base + col + 1]
                bits = (bits << 1) | (1 if left < right else 0)
        return f"{bits:016x}"
    except Exception:
        return None


def hamming(a: str | None, b: str | None) -> int:
    """두 16진 해시 사이 해밍 거리(다른 비트 수). 하나라도 없으면 64(최대)."""
    if not a or not b:
        return 64
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


def find_near_duplicates(hashes: list[tuple[int, str]], threshold: int = 5
                         ) -> list[tuple[int, int, int]]:
    """(id, phash) 목록에서 해밍거리 <= threshold 인 쌍을 찾아 반환.

    반환: (id_a, id_b, distance) 리스트. id_a < id_b.
    """
    pairs: list[tuple[int, int, int]] = []
    items = [(i, h) for i, h in hashes if h]
    for x in range(len(items)):
        id_a, ha = items[x]
        for y in range(x + 1, len(items)):
            id_b, hb = items[y]
            dist = hamming(ha, hb)
            if dist <= threshold:
                lo, hi = sorted((id_a, id_b))
                pairs.append((lo, hi, dist))
    return pairs
