# AGENTS.md — 블로그 포스팅 AI를 위한 이미지 사용 가이드

이 저장소는 **블로그 포스팅에 넣을 상업적 사용 가능 무료 이미지**를 찾아 주는 도구입니다.
블로그 글을 쓰는 AI(다른 Claude)는 아래 한 줄 명령으로 이미지를 얻으면 됩니다.

---

## 🚀 이미지가 필요할 때 실행할 명령 (이것만 알면 됨)

```bash
cd /Users/1113177/Desktop/github/image
source .venv/bin/activate
python -m imagecollector search "<키워드>" --limit 3 --json
```

- **기본 소스는 Pixabay** → 반환 이미지는 대부분 **저작자 표기 불필요**(`attribution_required: false`),
  그리고 **2024년 이후 최신** 사진입니다. 블로그에 크레딧 없이 바로 넣을 수 있습니다.
- **새로 다운로드**할 땐 `<키워드>`를 **영어**로 (Pixabay 결과가 많음).
  이미 모아둔 라이브러리 검색은 **한국어**도 됩니다(태그가 한국어라 매칭됨).
- 항상 **최대 `--limit` 개**를 돌려줍니다. 새 다운로드가 부족하면 라이브러리에서 채워
  결과가 비지 않습니다.

### 표기 없이 쓰고 싶으면 (가장 안전)

```bash
python -m imagecollector search "<키워드>" --limit 3 --no-attribution --json
```

`--no-attribution` = CC0/퍼블릭도메인 등 **표기 불필요**만 반환.

### 실존 인물(정치인·유명인)은 Wikimedia 에서

```bash
python -m imagecollector search "Lee Jae-myung" --source wikimedia --category korea-politics --json
```

스톡(Pixabay)에는 특정 실존 인물이 없습니다. Wikimedia 는 CC/공공누리(KOGL) 사진을 제공하며,
`min_year` 설정에 따라 2024년 이후 사진만 나옵니다. 이 경우 `attribution_required: true` 가
많으니 `attribution` 문구를 함께 표기하세요.

---

## 📦 반환 JSON 형식

```json
[
  {
    "id": 1234,
    "title": "coffee",
    "category": "coffee-cafe",
    "keyword": "coffee cafe",
    "path": "/Users/1113177/Desktop/github/image/images/coffee-cafe/coffee__pixabay-10391990.jpg",
    "thumbnail": "/Users/.../thumbnails/coffee-cafe/coffee__pixabay-10391990.jpg",
    "width": 1920, "height": 1280, "format": "jpeg",
    "source": "pixabay",
    "source_url": "https://pixabay.com/photos/....",
    "license": "pixabay",
    "license_url": "https://pixabay.com/service/license-summary/",
    "commercial_use": true,
    "modification_allowed": true,
    "attribution_required": false,
    "attribution": null,
    "creator": "Alexas_Fotos"
  }
]
```

| 필드 | 블로그에서 하는 일 |
|------|-------------------|
| `path` | 블로그에 넣을 **로컬 이미지 절대경로**. 이 파일을 업로드/삽입 |
| `commercial_use` | `true` 여야 상업적 사용 가능 (도구가 기본으로 `true`만 수집) |
| `attribution_required` | `true` 면 `attribution` 문구를 포스트에 표기 |
| `attribution` | 표기가 필요할 때 그대로 넣을 저작자 표기 문구 |
| `source_url` | 원본 출처 페이지 |

---

## ⚖️ 규칙 (반드시 지킬 것)

1. **`commercial_use: true` 인 이미지만 사용.**
2. **`attribution_required: true` 이면** 포스트에 `attribution` 문구를 표기.
3. 표기가 번거로우면 `--no-attribution` 으로 표기 불필요 이미지만 받기.
4. 확신이 안 서면 `license_url` 원문 확인. (이 도구는 법률 자문이 아님)

---

## 🗂️ 블로그 주제별 추천 키워드 (새 다운로드용, 영어)

| 주제 | 추천 키워드 |
|------|------------|
| 정치 | `government policy`, `election voting`, `parliament congress` |
| 연예 | `concert stage`, `microphone singer`, `awards show` |
| 지원금 | `welfare benefit`, `financial help hand`, `government grant document` |
| 돈 | `dollar bills`, `saving money jar`, `atm machine` |
| 경제 | `stock trading chart`, `global economy`, `inflation price rising` |
| 일상 | `morning routine`, `city commute`, `cleaning house` |
| 감정 | `laughing joy`, `crying tears`, `anxiety fear` |
| 청년 | `generation z`, `young professionals team`, `college students` |

이미 **37개 카테고리로 7천 8백여 장**을 모아 두었으니(정확한 수치는 `stats`), 위 키워드로
`search` 하면 대개 **네트워크 없이 즉시** 라이브러리에서 결과가 나옵니다.

---

## 🔎 라이브러리 둘러보기

```bash
python -m imagecollector serve   # http://127.0.0.1:8765 (라이브 갤러리, 보통 항상 켜져 있음)
python -m imagecollector stats   # 카테고리/소스/라이선스별 통계
```

> 허브(`hub up image`)로 띄운 경우 뷰어는 **8020** 에 있습니다. 자체 기본은 8765.

직접 DB를 읽으려면 `library.db`(SQLite) `images` 테이블을 조회하세요.
주요 컬럼: `filepath`, `category`, `tags`(한국어), `license`, `commercial_use`,
`attribution_required`, `attribution`.

---

## ⚙️ 참고

- 저장소 루트(`/Users/1113177/Desktop/github/image`)에서 `.venv` 활성화 후 실행.
- 원본은 `images/<카테고리>/`, 썸네일은 `thumbnails/<카테고리>/`.
- 새 키워드로 받은 이미지는 라이브러리에 누적됩니다(중복 자동 제거, 태그 자동 한국어).
