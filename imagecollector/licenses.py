"""라이선스 코드 -> 상업적 사용/변형/저작자표기 여부 판별.

상용 안전성의 핵심 모듈. 소스가 준 라이선스 코드를 신뢰하되,
여기서 한 번 더 규칙으로 검증해서 잘못된 수집을 막는다.
"""
from __future__ import annotations

# 사람이 읽는 이름
_PRETTY = {
    "cc0": "CC0 (퍼블릭 도메인)",
    "pdm": "Public Domain Mark",
    "publicdomain": "Public Domain",
    "by": "CC BY",
    "by-sa": "CC BY-SA",
    "by-nd": "CC BY-ND",
    "by-nc": "CC BY-NC",
    "by-nc-sa": "CC BY-NC-SA",
    "by-nc-nd": "CC BY-NC-ND",
    "sampling+": "CC Sampling+",
    "pixabay": "Pixabay License",
    "pexels": "Pexels License",
    "unsplash": "Unsplash License",
    "kogl-type-1": "공공누리 제1유형",
    "kogl-type-2": "공공누리 제2유형",
    "kogl-type-3": "공공누리 제3유형",
    "kogl-type-4": "공공누리 제4유형",
}

# 퍼블릭 도메인류 (저작자 표기 불필요)
_PUBLIC_DOMAIN = {"cc0", "pdm", "publicdomain"}

# 저작자 표기가 필요 없는 라이선스 (퍼블릭 도메인 + 자체 라이선스 스톡)
#  - Unsplash 는 라이선스상 표기 의무는 없으나 API 가이드라인상 권장됨(README 참고)
_NO_ATTRIBUTION = _PUBLIC_DOMAIN | {"pixabay", "pexels", "unsplash"}


def normalize(code: str | None) -> str:
    return (code or "").strip().lower()


def parts(code: str) -> set[str]:
    return set(normalize(code).split("-"))


def is_commercial_ok(code: str | None) -> bool:
    """NC(비영리) 조항이 없으면 상업적 사용 가능. 공공누리(KOGL)는 제1·2유형만 허용."""
    c = normalize(code)
    if c.startswith("kogl"):
        return not ("type-3" in c or "type-4" in c)  # 3·4유형은 상업 불가
    p = parts(c)
    if not p or p == {""}:
        return False
    return "nc" not in p


def is_modification_ok(code: str | None) -> bool:
    """ND(변형금지) 조항이 없으면 수정/변형 가능. KOGL 제2·4유형은 변형 불가."""
    c = normalize(code)
    if c.startswith("kogl"):
        return not ("type-2" in c or "type-4" in c)
    return "nd" not in parts(c)


def is_attribution_required(code: str | None) -> bool:
    """표기 불필요 라이선스(퍼블릭도메인/Pixabay/Pexels 등)가 아니면 표기 필요."""
    return normalize(code) not in _NO_ATTRIBUTION


def pretty_name(code: str | None, version: str | None = None) -> str:
    c = normalize(code)
    name = _PRETTY.get(c, c.upper() if c else "Unknown")
    if version and c not in _PUBLIC_DOMAIN:
        return f"{name} {version}"
    return name


def license_url(code: str | None, version: str | None, given: str | None) -> str | None:
    if given:
        return given
    c = normalize(code)
    if c == "cc0":
        return "https://creativecommons.org/publicdomain/zero/1.0/"
    if c in ("pdm", "publicdomain"):
        return "https://creativecommons.org/publicdomain/mark/1.0/"
    if c and c not in _PUBLIC_DOMAIN:
        v = version or "4.0"
        return f"https://creativecommons.org/licenses/{c}/{v}/"
    return None


def build_attribution(title: str | None, creator: str | None,
                      code: str | None, version: str | None,
                      landing_url: str | None, l_url: str | None) -> str:
    """CC 권장 형식에 가까운 저작자 표기 문자열 생성."""
    t = f'"{title}"' if title else "이미지"
    by = f" by {creator}" if creator else ""
    lic = pretty_name(code, version)
    src = f" ({landing_url})" if landing_url else ""
    lu = f" — {l_url}" if l_url else ""
    return f"{t}{by}{src} is licensed under {lic}{lu}"


def summarize(code: str | None, version: str | None = None,
              given_url: str | None = None) -> dict:
    """수집/저장/표시에 필요한 라이선스 정보 한 번에."""
    c = normalize(code)
    return {
        "license": c,
        "license_version": version,
        "license_url": license_url(c, version, given_url),
        "pretty": pretty_name(c, version),
        "commercial_use": is_commercial_ok(c),
        "modification": is_modification_ok(c),
        "attribution_required": is_attribution_required(c),
    }
