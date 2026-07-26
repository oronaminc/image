"""한국어 낱말 → 스톡 사진에서 실제로 잘 잡히는 영어 검색어로 변환.

왜 필요한가:
  '지원금' 을 직역한 `welfare benefit` 으로 Pixabay 를 검색하면 **동물 복지
  (animal welfare)** 사진 — 다람쥐·알파카 — 이 나온다. 스톡 사이트는 추상적인
  정책·제도 개념을 색인하지 않기 때문이다. 그래서 추상 개념은 **눈에 보이는
  사물/장면** 검색어 여러 개로 바꿔서 찾는다. (지원금 → 돈 건네는 손, 현금 봉투,
  서류 작성 …)

우선순위:
  1. CONCEPT_KO  : 손으로 고른 개념 → 시각적 검색어 목록
  2. korean.QUERY_KO 역방향 : 이미 쓰던 한국어 검색어 문구
  3. korean.CATEGORY_KO 역방향 : 한국어 카테고리명 → config.yaml 의 그 카테고리 검색어
  4. 부분 일치 (예: '청년지원금' 안에 '지원금')
  5. 영어 입력은 그대로
  6. 사전에 없는 한국어는 **위키백과 언어링크**로 영어 표제어를 얻는다
     (엔화 → Japanese yen, 청산 → Liquidation). 키가 필요 없다.
  7. 그것도 실패하면 Pixabay 한국어 색인(lang=ko). 오탐이 많아 최후 수단
     ('엔화' 로 치면 베트남 지명 Hung Yen 이 나온다)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .korean import CATEGORY_KO, QUERY_KO

# 한국어 개념 → 시각적으로 잘 잡히는 영어 검색어들 (Pixabay 결과 확인 후 선정)
CONCEPT_KO: dict[str, list[str]] = {
    # --- 돈/정책 (직역이 가장 잘 실패하는 영역) ---
    "지원금": ["money hand giving", "cash envelope", "financial aid money",
             "government document form", "money korean won"],
    "보조금": ["money hand giving", "grant money finance", "document signing money"],
    "복지": ["social security card", "helping hands people", "elderly care support"],
    "수당": ["money hand giving", "salary envelope", "child money family"],
    "재난지원금": ["cash envelope", "money hand giving", "emergency support money"],
    "정책": ["government building", "parliament assembly hall", "signing agreement officials"],
    "세금": ["tax calculation", "tax form document", "calculator money desk"],
    "환급": ["tax refund money", "calculator money desk", "receipt money"],
    "대출": ["loan money house", "bank counter", "mortgage document signing"],
    "이자": ["interest rate concept", "calculator money desk", "bank savings"],
    "금리": ["interest rate concept", "bank building", "stock market screen"],
    "적금": ["saving money jar", "piggy bank saving", "savings account book"],
    "연금": ["pension retirement fund", "elderly couple money", "retirement life"],
    "월세": ["apartment key rent", "rent contract signing", "house money"],
    "전세": ["house key contract", "apartment complex city", "real estate investment"],
    "부동산": ["real estate investment", "apartment complex city", "house model key"],
    "물가": ["consumer price shopping cart", "inflation price rising", "supermarket aisle"],
    "청약": ["apartment complex city", "house key contract", "real estate investment"],
    "보험": ["insurance contract", "family protection concept", "document signing desk"],
    "투자": ["stock trading chart", "investment portfolio laptop", "stock market screen"],
    "주식": ["stock market screen", "stock trading chart", "financial chart laptop"],
    "코인": ["cryptocurrency bitcoin", "bitcoin coin", "crypto trading chart"],
    "환율": ["currency exchange money", "dollar bills", "money exchange counter"],
    "카드": ["credit card payment", "credit card hand", "payment kiosk"],
    "통장": ["savings account book", "bank counter", "bank book money"],
    "엔화": ["japanese yen money", "yen banknote", "japan currency cash"],
    "달러": ["dollar bills", "us dollar money", "dollar banknote"],
    "유로": ["euro banknote", "euro money coins", "european currency"],
    "원화": ["money korean won", "korean money cash", "won banknote"],
    "위안화": ["chinese yuan money", "yuan banknote", "china currency cash"],
    "청산": ["debt settlement money", "bankruptcy document", "calculator money desk"],
    "파산": ["bankruptcy document", "empty wallet", "debt stress money"],
    "부채": ["debt stress money", "credit card debt", "loan document signing"],
    "예금": ["savings account book", "bank counter", "saving money jar"],
    "인출": ["atm machine", "withdraw money atm", "cash in hand atm"],
    "송금": ["online banking phone", "money transfer app", "bank counter"],
    "자산": ["investment portfolio laptop", "real estate investment", "gold investment"],
    "채권": ["bond certificate document", "financial chart laptop", "bank building"],
    "증시": ["stock market screen", "stock trading chart", "financial chart laptop"],
    "경기침체": ["stock market crash", "empty wallet", "closed shop shutter"],
    "실업": ["empty office desk", "job seeker young", "unemployment concept"],
    "월급": ["salary envelope", "payslip document", "money hand giving"],

    # --- 사람/생활 ---
    "청년": ["young professionals team", "college students campus", "generation z"],
    "취업": ["job interview", "resume cv document", "job fair booth"],
    "이직": ["job interview", "career planning notebook", "office worker portrait"],
    "면접": ["job interview", "handshake hiring", "online interview laptop"],
    "퇴사": ["office desk box leaving", "resignation letter", "empty office desk"],
    "창업": ["young entrepreneur", "startup team", "small business owner shop"],
    "육아": ["parenting baby", "mother and child", "baby sleeping"],
    "출산": ["newborn baby", "pregnant woman", "baby hands mother"],
    "결혼": ["wedding ceremony", "wedding rings", "bride bouquet"],
    "이혼": ["divorce document signing", "sad couple", "wedding ring removed"],
    "노후": ["retirement life", "elderly couple", "senior citizen smiling"],
    "은퇴": ["retirement life", "pension retirement fund", "elderly couple"],
    "다이어트": ["weight scale diet", "healthy food plate", "gym workout weights"],
    "운동": ["gym workout weights", "running exercise outdoor", "yoga stretching"],
    "건강": ["healthy lifestyle", "medical checkup", "healthy food plate"],
    "병원": ["hospital ward", "doctor stethoscope", "hospital corridor"],
    "약": ["medicine pills", "pharmacy medicine shelf", "vitamins supplement"],
    "우울": ["lonely person window", "sad depressed person", "mental health"],
    "스트레스": ["stress headache", "deadline stress", "tired exhausted"],
    "공부": ["studying notes highlighter", "library books study", "online class laptop"],
    "수능": ["exam test paper", "school classroom desk", "studying notes highlighter"],
    "여행": ["passport airport", "mountain hiking trail", "beach vacation umbrella"],
    "맛집": ["restaurant food table", "korean bbq", "street food"],
    "카페": ["coffee cafe", "coffee dessert cafe", "cafe interior"],
    "반려동물": ["cute dog", "kitten cat", "dog and owner"],
    "자동차": ["electric car", "car dashboard interior", "highway driving"],
    "전기차": ["electric car", "car charging station", "electric charging tech"],
    "날씨": ["cloudy sky weather", "rainy day umbrella", "sunny blue sky"],
    "장마": ["monsoon rain window", "rainy day umbrella", "heavy rain street"],
    "폭염": ["heat wave sun", "summer beach sun", "hot sun sky"],
    "미세먼지": ["yellow dust fine dust city", "air pollution city", "wearing mask city"],
    "환경": ["tree planting", "recycling waste", "solar energy panel"],
    "인공지능": ["artificial intelligence robot", "ai technology brain", "data center server"],
    "선거": ["ballot box vote", "election campaign", "voting hand"],
    "국회": ["parliament assembly hall", "government building", "public hearing"],
    "재판": ["courtroom", "judge gavel", "justice scale"],
    "경찰": ["police officer", "police car", "security guard cctv"],
}

# 개념 → 저장할 카테고리 (config.yaml 의 카테고리 슬러그).
# 없으면 'search' 로 간다. 한국어는 슬러그로 못 만들기 때문에 꼭 필요하다.
CONCEPT_CATEGORY: dict[str, str] = {
    "지원금": "subsidy", "보조금": "subsidy", "복지": "subsidy", "수당": "subsidy",
    "재난지원금": "subsidy", "정책": "politics", "선거": "politics", "국회": "politics",
    "세금": "money", "환급": "money", "카드": "money", "통장": "money", "환율": "money",
    "엔화": "money", "달러": "money", "유로": "money", "원화": "money", "위안화": "money",
    "예금": "money", "인출": "money", "송금": "money", "월급": "money",
    "청산": "finance-invest", "파산": "finance-invest", "부채": "finance-invest",
    "자산": "finance-invest", "채권": "finance-invest", "증시": "finance-invest",
    "경기침체": "economy", "실업": "job-career",
    "대출": "finance-invest", "이자": "finance-invest", "금리": "finance-invest",
    "적금": "finance-invest", "연금": "finance-invest", "보험": "finance-invest",
    "투자": "finance-invest", "주식": "finance-invest", "코인": "finance-invest",
    "월세": "interior", "전세": "interior", "부동산": "finance-invest", "청약": "interior",
    "물가": "economy",
    "청년": "youth", "취업": "job-career", "이직": "job-career", "면접": "job-career",
    "퇴사": "job-career", "창업": "business",
    "육아": "family", "출산": "family", "결혼": "wedding", "이혼": "family",
    "노후": "senior", "은퇴": "senior",
    "다이어트": "health", "운동": "sports", "건강": "health",
    "병원": "medical", "약": "medical",
    "우울": "emotion", "스트레스": "emotion",
    "공부": "education", "수능": "education",
    "여행": "travel", "맛집": "food", "카페": "coffee-cafe",
    "반려동물": "pet", "자동차": "car", "전기차": "car",
    "날씨": "season-weather", "장마": "season-weather", "폭염": "season-weather",
    "미세먼지": "environment", "환경": "environment",
    "인공지능": "technology",
    "재판": "law-justice", "경찰": "law-justice",
}

# 흔한 접미/수식어 — 부분 일치 전에 떼어내면 적중률이 오른다
_SUFFIX = ("신청", "제도", "혜택", "정보", "방법", "안내", "사진", "이미지")


@dataclass
class Plan:
    """번역 결과: 어떤 영어 검색어로 어디에 담을지."""
    keyword: str
    queries: list[str] = field(default_factory=list)
    category: str = "search"
    lang: str | None = None      # Pixabay lang 파라미터 (매핑 실패 시 'ko')
    matched: bool = False        # 검색어를 제대로 만들었는지 (UI 안내용)
    via: str = "dictionary"      # 어떻게 만들었는지: dictionary | wikipedia | asis


_QUERY_KO_REV = {v: k for k, v in QUERY_KO.items()}
_CATEGORY_KO_REV = {v: k for k, v in CATEGORY_KO.items()}


def _is_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def _slug(text: str) -> str:
    """영어면 슬러그, 한국어(=ASCII 로 못 만드는 말)면 'search' 카테고리."""
    from .images import slugify
    slug = slugify(text, 40)
    return "search" if slug == "untitled" else slug


def _category_for(word: str) -> str:
    """개념에 맞는 카테고리 슬러그. 한국어 카테고리명 → 슬러그도 여기서 처리."""
    return _CATEGORY_KO_REV.get(word) or CONCEPT_CATEGORY.get(word) or _slug(word)


def to_queries(keyword: str, config=None) -> Plan:
    """낱말 하나를 실제 검색에 쓸 영어 검색어 목록으로 바꾼다."""
    kw = (keyword or "").strip()
    if not kw:
        return Plan(keyword=kw)

    # 1) 개념 사전 (정확 일치)
    if kw in CONCEPT_KO:
        return Plan(kw, list(CONCEPT_KO[kw]), category=_category_for(kw), matched=True)

    # 2) 기존 한국어 검색어 문구 (예: '아동 수당' → 'child allowance')
    if kw in _QUERY_KO_REV:
        return Plan(kw, [_QUERY_KO_REV[kw]], category=_slug(kw), matched=True)

    # 3) 한국어 카테고리명 (예: '반려동물' → pet 카테고리의 검색어 전부)
    if kw in _CATEGORY_KO_REV:
        slug = _CATEGORY_KO_REV[kw]
        cat_queries = list((getattr(config, "categories", {}) or {}).get(slug, []))
        if cat_queries:
            return Plan(kw, cat_queries, category=slug, matched=True)

    # 4) 부분 일치 — 접미어를 떼거나, 개념어를 포함하는 경우
    stem = kw
    for suf in _SUFFIX:
        if stem.endswith(suf) and len(stem) > len(suf):
            stem = stem[: -len(suf)].strip()
    for concept, queries in CONCEPT_KO.items():
        if concept in (stem or kw):
            return Plan(kw, list(queries), category=_category_for(concept), matched=True)

    # 5) 영어면 그대로
    if not _is_korean(kw):
        return Plan(kw, [kw], category=_slug(kw), matched=False, via="asis")

    # 6) 사전에 없는 한국어 → 위키백과 언어링크로 영어 표제어를 얻는다.
    #    (엔화 → Japanese yen, 청산 → Liquidation) Pixabay 한국어 색인은
    #    오탐이 많아서('엔화' → 베트남 Hung Yen) 번역을 먼저 시도한다.
    english = wiki_translate(kw, config)
    if english:
        # 맥락 단어를 덧붙이면(예: '+ business money') 엉뚱한 쪽으로 끌려간다.
        # ('치과' → Dentistry business money → 동전 사진) 번역어만 그대로 쓴다.
        # 뜻이 여러 개인 추상어는 CONCEPT_KO 에 직접 넣어서 해결한다.
        return Plan(kw, [english], category=_slug(kw), matched=True, via="wikipedia")

    # 7) 번역도 실패하면 Pixabay 한국어 색인으로라도 시도
    return Plan(kw, [kw], category=_slug(kw), lang="ko", matched=False, via="asis")


# --- 위키백과 언어링크 번역 (키 불필요) ---

WIKI_API = "https://ko.wikipedia.org/w/api.php"
_CACHE_NAME = ".translate_cache.json"
_memory_cache: dict[str, str | None] = {}


def _cache_path(config) -> Path | None:
    base = getattr(config, "base_dir", None)
    return Path(base) / _CACHE_NAME if base else None


def wiki_translate(word: str, config=None) -> str | None:
    """한국어 낱말 → 영어 위키백과 표제어. 실패하면 None.

    같은 낱말을 여러 번 조회하지 않도록 결과(실패 포함)를 파일에 캐시한다.
    """
    if word in _memory_cache:
        return _memory_cache[word]

    path = _cache_path(config)
    cache: dict = {}
    if path and path.exists():
        try:
            cache = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
        if word in cache:
            _memory_cache[word] = cache[word]
            return cache[word]

    english: str | None = None
    try:
        resp = requests.get(
            WIKI_API,
            params={"action": "query", "titles": word, "prop": "langlinks",
                    "lllang": "en", "redirects": 1, "format": "json"},
            headers={"User-Agent": getattr(config, "user_agent", "ImageCollector/1.0")},
            timeout=15,
        )
        pages = ((resp.json().get("query") or {}).get("pages") or {})
        for page in pages.values():
            for link in page.get("langlinks") or []:
                english = (link.get("*") or "").strip() or None
    except Exception:
        english = None

    _memory_cache[word] = english
    if path:
        cache[word] = english
        try:
            path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass
    return english
