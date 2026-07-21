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

- `<키워드>`는 **영어**가 결과가 훨씬 많습니다. (예: 정치→`government building`, 지원금→`financial support`)
- `--json` 을 붙이면 아래 형식의 JSON 배열이 stdout 으로 나옵니다. 이걸 파싱해서 쓰세요.
- 항상 **최대 `--limit` 개의 사용 가능한 이미지**를 돌려줍니다.
  (새로 다운로드가 부족하면 이미 모아둔 라이브러리에서 채워 줍니다. → 결과가 비지 않음)

### 저작자 표기가 부담되면 (권장: 표기 없이 쓰고 싶을 때)

```bash
python -m imagecollector search "<키워드>" --limit 3 --no-attribution --json
```

`--no-attribution` 을 붙이면 **CC0/퍼블릭도메인**만 반환합니다.
→ 블로그에 저작자 표기 없이 그냥 넣어도 됩니다. **가장 안전하고 편합니다.**

---

## 📦 반환 JSON 형식

```json
[
  {
    "id": 75,
    "title": "Money Coins",
    "keyword": "money coins",
    "path": "/Users/1113177/Desktop/github/image/images/money-coins/money-coins__openverse-....jpg",
    "thumbnail": "/Users/.../thumbnails/money-coins/....jpg",
    "width": 960, "height": 640, "format": "jpeg",
    "source": "openverse",
    "source_url": "https://stocksnap.io/photo/....",
    "license": "cc0",
    "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "commercial_use": true,
    "modification_allowed": true,
    "attribution_required": false,
    "attribution": "\"Money Coins\" by Negative Space is marked with CC0 1.0. ...",
    "creator": "Negative Space"
  }
]
```

### 각 필드 사용법
| 필드 | 블로그에서 하는 일 |
|------|-------------------|
| `path` | 블로그에 넣을 **로컬 이미지 파일의 절대경로**. 이 파일을 업로드/삽입하세요. |
| `commercial_use` | `true` 여야 상업적 사용 가능 (도구가 이미 `true`만 수집하지만 재확인용) |
| `attribution_required` | `true` 면 아래 `attribution` 문구를 포스트에 반드시 표기 |
| `attribution` | 표기가 필요할 때 그대로 넣을 저작자 표기 문구 |
| `source_url` | 원본 출처 페이지 (표기 시 함께 링크하면 좋음) |

---

## ⚖️ 규칙 (반드시 지킬 것)

1. **`commercial_use: true` 인 이미지만 사용** — 도구가 기본으로 이것만 수집하지만, 직접 파일을
   가져다 쓸 때도 이 값을 확인하세요.
2. **`attribution_required: true` 이면** 포스트 하단 등에 `attribution` 문구를 표기하세요.
   예: `이미지 출처: "Money Coins" by Negative Space (CC BY 2.0)`
3. **표기가 번거로우면 `--no-attribution` 으로 CC0만 받으세요.** 표기 없이 자유롭게 사용 가능.
4. 확신이 서지 않으면 `license_url` 의 라이선스 원문을 확인하세요. (이 도구는 법률 자문이 아님)

---

## 🗂️ 블로그 주제별 추천 키워드

| 주제 | 추천 영어 키워드 |
|------|------------------|
| 정치 | `government building`, `election voting`, `parliament`, `national flag` |
| 연예 | `concert stage`, `microphone singer`, `movie theater`, `spotlight` |
| 지원금 | `financial support`, `cash money hand`, `government welfare`, `benefit` |
| 돈 | `money banknotes`, `coins stack`, `piggy bank savings`, `wallet` |
| 경제 | `stock market chart`, `financial graph`, `business trading` |
| 일상 | `morning coffee`, `city commute`, `home living room` |
| 감정 | `happy smile`, `sad lonely`, `calm meditation`, `stressed worried` |

이미 `config.yaml` 의 카테고리로 수백~천 장을 미리 모아 두었으니,
위 키워드로 `search` 하면 대개 **네트워크 없이 즉시** 결과가 나옵니다.

---

## 🔎 이미 모아둔 라이브러리를 둘러보려면

```bash
# 사람이 브라우저로 보기
python -m imagecollector serve            # http://127.0.0.1:8000

# 통계 (카테고리/소스/라이선스별 개수)
python -m imagecollector stats
```

프로그램에서 직접 DB를 읽고 싶으면 `library.db`(SQLite)의 `images` 테이블을 조회하세요.
주요 컬럼: `filepath`, `category`, `license`, `commercial_use`, `attribution_required`, `attribution`.

---

## ⚙️ 참고

- 반드시 저장소 루트(`/Users/1113177/Desktop/github/image`)에서 `.venv` 를 활성화하고 실행하세요.
- 이미지 원본은 `images/<카테고리>/`, 썸네일은 `thumbnails/<카테고리>/` 에 있습니다.
- 새 키워드로 받은 이미지는 자동으로 라이브러리에 누적됩니다(중복은 자동 제거).
