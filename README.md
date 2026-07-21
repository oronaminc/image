# 🖼️ Image Collector

상업적 사용에 안전한 **무료 이미지 수집기 + 웹 뷰어**입니다.
카테고리별로 이미지를 로컬에 모으고, 라이선스·저작자 정보를 자동으로 관리하며,
브라우저에서 갤러리처럼 볼 수 있습니다.

> AI 이미지 생성이 어려울 때, 상업적으로 써도 되는 무료 이미지를 체계적으로 모아
> 나만의 이미지 라이브러리를 만드는 것이 목표입니다.

---

## ✨ 핵심 기능

| 기능 | 설명 |
|------|------|
| 📋 **라이선스 추적 + 상업적 사용 필터** | NC(비영리)/ND(변형금지) 자동 판별. 상업적 사용 가능 이미지만 수집(기본값) |
| 📝 **저작자 표기 자동 생성** | CC-BY 등 표기가 필요한 이미지의 attribution 문자열 자동 생성·내보내기 |
| 🔁 **중복 제거** | SHA-256(정확 중복) + 지각적 해시 dhash(유사 중복) |
| 🏷️ **메타데이터 관리** | 카테고리·검색어·태그·해상도·저작자·출처를 SQLite DB로 관리, 깔끔한 파일명 규칙 |
| 🖼️ **웹 뷰어** | 갤러리·필터·검색·즐겨찾기·삭제·통계·저작자표기 페이지 |
| 🔌 **멀티 소스(플러그인)** | Openverse·Wikimedia(키 불필요) + Pexels·Pixabay·Unsplash(키 추가 시) |
| ♻️ **증분 수집** | 이미 받은 이미지는 자동 건너뜀. 썸네일 자동 생성 |

---

## 🚀 빠른 시작

```bash
# 1) 가상환경 + 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) (선택) 설정/폴더 초기화 — 저장소에 이미 config.yaml 이 있어 생략 가능
python -m imagecollector init

# 3) 이미지 수집 (config.yaml 의 카테고리·검색어대로)
python -m imagecollector collect

# 4) 웹 뷰어 실행 → 브라우저에서 http://127.0.0.1:8000
python -m imagecollector serve
```

키 없이 **Openverse**로 바로 시작됩니다.

---

## 🧰 명령어

```bash
# 전체 수집 (config.yaml 기준)
python -m imagecollector collect

# 특정 소스/카테고리/개수 지정
python -m imagecollector collect --source openverse --category nature --limit 30

# 검색어 직접 지정 (config 무시)
python -m imagecollector collect --query "cyberpunk city" --query "neon street" --category custom

# 웹 뷰어
python -m imagecollector serve --host 0.0.0.0 --port 8000

# 통계
python -m imagecollector stats

# 저작자 표기 파일 내보내기 (ATTRIBUTIONS.md)
python -m imagecollector export-attributions

# 유사 중복 탐지 (거리 작을수록 엄격). --delete 로 실제 삭제
python -m imagecollector dedup --threshold 5
python -m imagecollector dedup --threshold 5 --delete

# 사용 가능한 소스 / 키 상태 확인
python -m imagecollector sources
```

---

## 🔑 이미지 소스와 라이선스

| 소스 | API 키 | 라이선스 | 상업적 사용 |
|------|--------|----------|-------------|
| **Openverse** | 불필요 | CC0/PDM/CC-BY/CC-BY-SA 등 | ✅ (NC/ND 자동 제외) |
| **Wikimedia Commons** | 불필요 | 퍼블릭도메인/CC | ✅ (NC 자동 제외) |
| **Pexels** | 무료 키 | Pexels License | ✅ 표기 불필요 |
| **Pixabay** | 무료 키 | Pixabay License | ✅ 표기 불필요 |
| **Unsplash** | 무료 키 | Unsplash License | ✅ (API 가이드라인 준수 필요) |

키가 필요한 소스는 `.env.example` 을 복사해 `.env` 에 키를 넣으면 활성화됩니다.

```bash
cp .env.example .env
# .env 파일을 열어 PEXELS_API_KEY 등을 채우세요
```

### ⚖️ 상업적 사용에 대한 안내 (중요)

- 기본 설정(`license_type: commercial`)은 **상업적 사용이 허용된 라이선스만** 수집합니다.
  소스가 준 라이선스 코드를 `licenses.py` 에서 한 번 더 규칙으로 검증합니다.
- **CC-BY / CC-BY-SA** 는 상업적 사용은 가능하지만 **저작자 표기가 필수**입니다.
  `python -m imagecollector export-attributions` 또는 웹의 `/attributions` 페이지에서
  표기 문구를 받아 실제 사용처(웹사이트·영상·인쇄물 등)에 함께 표기하세요.
- **CC-BY-SA** 는 2차 저작물에 동일 라이선스를 적용해야 할 수 있습니다(ShareALike).
- 표기가 전혀 필요 없는 것만 원하면 `config.yaml` 에서
  카테고리를 CC0/퍼블릭도메인 위주 소스로 좁히거나, 수집 후 라이선스로 필터하세요.
- 이 도구는 편의를 위한 것이며 **법률 자문이 아닙니다.** 최종 사용 전 각 이미지의
  라이선스 원문(상세 페이지의 "라이선스 전문" 링크)을 확인하는 것을 권장합니다.

---

## ⚙️ 설정 (`config.yaml`)

```yaml
storage:
  images_dir: images          # 원본 저장 폴더
  thumbnails_dir: thumbnails
  database: library.db
  thumbnail_size: 400

collection:
  default_source: openverse
  license_type: commercial     # commercial | commercial,modification
  safe_search: true
  per_category_limit: 40       # 검색어당 수집 개수
  min_width: 600               # 최소 해상도 (0=제한없음)
  min_height: 400
  near_dup_threshold: 0        # 수집 중 유사중복 스킵(해밍거리). 0=끔

categories:
  nature:
    - forest landscape
    - mountain sunrise
  business:
    - modern office workspace
```

`categories` 아래에 원하는 만큼 카테고리와 검색어를 추가하세요.

---

## 📁 프로젝트 구조

```
image/
├── config.yaml               # 카테고리·검색어·수집 설정
├── .env.example              # (선택) API 키 템플릿
├── requirements.txt
├── images/<category>/...     # 원본 이미지 (git 제외)
├── thumbnails/<category>/... # 썸네일 (git 제외)
├── library.db                # 메타데이터 SQLite (git 제외)
└── imagecollector/
    ├── __main__.py           # CLI (collect/serve/stats/dedup/...)
    ├── config.py             # 설정 로딩
    ├── licenses.py           # 라이선스 판별(상업/변형/표기)
    ├── dedup.py              # sha256 + dhash 중복 제거
    ├── db.py                 # SQLite 스키마·쿼리
    ├── images.py             # 다운로드·파일명·썸네일
    ├── collector.py          # 수집 오케스트레이션
    ├── sources/              # 소스 플러그인
    │   ├── openverse.py  wikimedia.py
    │   └── pexels.py  pixabay.py  unsplash.py
    └── web/                  # FastAPI 웹 뷰어 (templates/static)
```

---

## 💡 팁

- **로컬 데이터는 git에 올라가지 않습니다.** `images/`, `thumbnails/`, `library.db`, `.env`
  는 `.gitignore` 에 있습니다. 코드·설정만 커밋됩니다.
- 매일/주기적으로 `collect` 를 돌리면 새 이미지만 증분으로 쌓입니다.
- 웹 뷰어에서 마음에 드는 이미지를 ⭐즐겨찾기 하고, 필요 없는 건 🗑삭제할 수 있습니다.
- 새 소스를 추가하려면 `imagecollector/sources/base.py` 의 `Source` 를 상속해
  `sources/__init__.py` 레지스트리에 등록하면 됩니다.
