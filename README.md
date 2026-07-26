# 🖼️ Image Collector

상업적 사용에 안전한 **무료 이미지 수집기 + 웹 뷰어**입니다.
블로그 포스팅 등에 쓸 이미지를 카테고리별로 로컬에 모으고, 라이선스·저작자·태그를
자동으로 관리하며, 브라우저 갤러리에서 라이브로 볼 수 있습니다.

> AI 이미지 생성이 어려울 때, 상업적으로 써도 되는 무료 이미지를 체계적으로 모아
> 나만의 이미지 라이브러리를 만드는 것이 목표입니다.

---

## ✨ 핵심 기능

| 기능 | 설명 |
|------|------|
| 📋 **라이선스 필터** | 상업적 사용 가능(NC/ND 제외)만 수집. CC·공공누리(KOGL)·Pixabay/Pexels 라이선스 판별 |
| 📝 **저작자 표기 자동 생성** | 표기가 필요한 이미지의 attribution 문구 자동 생성·내보내기 |
| 🆕 **최신 사진만** | Pixabay 최신 업로드순 + 2024년 이후만 수집(연도 필터) |
| 🏷️ **한국어 태그** | 카테고리·검색어를 한국어 태그로 자동 부여 |
| 🔁 **중복 제거** | SHA-256(정확 중복) + 지각적 해시 dhash(유사 중복) |
| 🖼️ **라이브 웹 뷰어** | 갤러리·필터·검색·즐겨찾기·삭제·통계 + 새 이미지 실시간 감지 |
| 🔌 **멀티 소스(플러그인)** | Pixabay·Pexels·Unsplash(키) + Openverse·Wikimedia(키 불필요) |
| ♻️ **증분 수집** | 이미 받은 이미지는 자동 건너뜀. 썸네일 자동 생성 |

---

## 🚀 빠른 시작

```bash
# 1) 가상환경 + 의존성 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) API 키 설정 (기본 소스 Pixabay 사용 시)
cp .env.example .env
#  → .env 의 PIXABAY_API_KEY 에 무료 키 입력 (https://pixabay.com/api/docs/)
#  키 없이 시작하려면 config.yaml 의 default_source 를 openverse 로 바꾸세요(키 불필요).

# 3) 이미지 수집 (config.yaml 의 카테고리·검색어대로)
python -m imagecollector collect

# 4) 웹 뷰어 실행 → http://127.0.0.1:8765
python -m imagecollector serve
```

> **포트 주의.** 이 프로젝트의 기본 포트는 **8765** 지만, 옆의 `hub` 관제탑이 띄울 때는
> **8020** 을 쓴다 (`hub/registry.json`). `hub up image` 로 켰다면 8020 으로 접속하세요.

> 🤖 **블로그 포스팅 AI(다른 Claude)가 이 도구를 쓴다면** → [`AGENTS.md`](AGENTS.md) 참고.
> 핵심은 `python -m imagecollector search "<키워드>" --limit 3 --json` 한 줄입니다.

---

## 🧰 명령어

```bash
# 키워드로 이미지 검색·다운로드 (블로그용 핵심). --json 으로 기계가 읽는 출력
python -m imagecollector search "coffee cafe" --limit 5
python -m imagecollector search "money" --limit 5 --no-attribution --json   # 표기 불필요만

# 실존 인물 등은 Wikimedia 에서 (스톡엔 없음)
python -m imagecollector search "Lee Jae-myung" --source wikimedia --category korea-politics

# 전체 수집 (config.yaml 기준) / 소스·카테고리·개수 지정
python -m imagecollector collect
python -m imagecollector collect --source pixabay --category nature --limit 30

# 웹 뷰어 (기본 포트 8765)
python -m imagecollector serve --port 8765

# 통계 / 저작자 표기 내보내기(ATTRIBUTIONS.md)
python -m imagecollector stats
python -m imagecollector export-attributions

# 유사 중복 탐지·삭제
python -m imagecollector dedup --threshold 5 --delete

# 이미지 삭제 (소스/카테고리/업로드ID 기준)
python -m imagecollector prune --source openverse                    # 특정 소스 전부
python -m imagecollector prune --source pixabay --max-source-id 9000000  # 오래된 것
python -m imagecollector prune --category politics --dry-run          # 미리보기

# 모든 태그를 한국어로 재설정
python -m imagecollector retag

# 소스/키 상태 확인
python -m imagecollector sources
```

---

## 🔑 이미지 소스와 라이선스

| 소스 | API 키 | 상업 사용 | 저작자 표기 | 특징 |
|------|--------|-----------|-------------|------|
| **Pixabay** (기본·추천) | 무료 키 | ✅ | **불필요** | 사진+일러스트, 최신순·품질 일관 |
| **Pexels** | 무료 키 | ✅ | **불필요** | 고급 사진 |
| **Unsplash** | 무료 키 | ✅ | 권장 | 예술적 사진(API 약관 유의) |
| **Openverse** | 불필요 | ✅ | 대부분 필요 | CC 아카이브(다양·옛날 많음) |
| **Wikimedia** | 불필요 | ✅ | 라이선스별 | 실존 인물·장소·자료(CC/공공누리) |

키가 필요한 소스는 `.env.example` 을 `.env` 로 복사해 키를 채우면 활성화됩니다.

### ⚖️ 상업적 사용 안내 (중요)

- 기본값 `license_type: commercial` → **상업적 사용 가능 라이선스만** 수집하고,
  `licenses.py` 에서 규칙(NC/ND, 공공누리 유형 등)으로 한 번 더 검증합니다.
- **Pixabay/Pexels/CC0/PDM** = 저작자 표기 불필요 → 블로그에 바로 사용.
- **CC-BY / CC-BY-SA / 공공누리 제1·2유형** = 상업 가능하나 **표기 필수**.
  `export-attributions` 또는 웹 `/attributions` 에서 문구를 받아 표기하세요.
- 이 도구는 편의용이며 **법률 자문이 아닙니다.** 최종 사용 전 각 이미지의 라이선스 원문 확인 권장.

---

## 🆕 최신 사진만 (2024년 이후)

- **Pixabay**: `order: latest`(최신 업로드순) + `min_source_id`(업로드ID 기준 필터).
  ID 9,000,000 ≈ 2024년 → `min_source_id: 9000000` 이면 2024년 이후만 수집.
- **Wikimedia**: `min_year: 2024` → 촬영연도(또는 파일명 연도)가 2024 미만이거나
  연도 불명이면 제외.
- 이미 쌓인 옛날 이미지는 `prune --source pixabay --max-source-id 9000000` 로 정리.

## 🏷️ 한국어 태그

수집·검색 시 각 이미지에 **`한국어 카테고리, 한국어 검색어`** 형태의 태그가 자동으로 붙습니다
(예: `정치, 국회` / `반려동물, 새끼 고양이`). 매핑은 `imagecollector/korean.py` 에 있고,
기존 이미지는 `python -m imagecollector retag` 로 일괄 변경합니다.

## 🖥️ 라이브 웹 뷰어 · 항상 켜두기

- 갤러리는 **6초마다 새 이미지를 감지**해 "🆕 새 이미지 도착" 배너를 띄웁니다(라이브).
- 서버를 **항상 켜두는 방법**은 [`deploy/README.md`](deploy/README.md) 참고
  (권장: `nohup bash run_viewer.sh 8765 &` — 죽으면 자동 재시작).
- 여러 프로젝트를 한꺼번에 관리한다면 허브에서 `hub up image` (포트 8020).

---

## ⚙️ 설정 (`config.yaml`)

```yaml
collection:
  default_source: pixabay      # pixabay | openverse | wikimedia | pexels | unsplash
  license_type: commercial     # 상업 사용 가능만
  order: latest                # (Pixabay) latest 최신순 | popular 인기순
  min_source_id: 9000000       # (Pixabay) 이 업로드ID 이상 = 약 2024+. 0=제한없음
  min_year: 2024               # (Wikimedia) 이 연도 이후만. 0=제한없음
  safe_search: true
  per_category_limit: 40       # 검색어당 수집 개수
  min_width: 600               # 최소 해상도 (0=제한없음)
  min_height: 400
  request_delay: 1.0           # 폴백(소스별 rate_delay 우선)
  near_dup_threshold: 0        # 수집 중 유사중복 스킵(해밍거리). 0=끔

categories:
  politics: [government policy, election voting, ...]
  money:    [dollar bills, coins stack, ...]
  # ... 원하는 만큼 카테고리·검색어 추가
```

---

## 📁 프로젝트 구조

```
image/
├── config.yaml               # 카테고리·검색어·수집 설정
├── .env.example / .env       # API 키 (.env 는 git 제외)
├── requirements.txt
├── run_viewer.sh             # 뷰어 항상 켜두기(자동 재시작)
├── deploy/                   # launchd 서비스 + 항상 켜두기 가이드
├── images/ thumbnails/       # 원본·썸네일 (git 제외)
├── library.db                # 메타데이터 SQLite (git 제외)
└── imagecollector/
    ├── __main__.py           # CLI (collect/search/serve/prune/retag/...)
    ├── config.py licenses.py dedup.py db.py images.py korean.py
    ├── collector.py          # 수집 오케스트레이션
    ├── sources/              # openverse·wikimedia·pixabay·pexels·unsplash
    └── web/                  # FastAPI 웹 뷰어 (templates/static)
```

---

## 💡 팁

- **로컬 데이터는 git에 안 올라갑니다.** `images/`, `thumbnails/`, `library.db`, `.env`,
  `.viewer.log` 는 `.gitignore` 에 있습니다. 코드·설정만 커밋됩니다.
- 실존 인물(정치인·유명인)은 스톡에 없으니 `--source wikimedia` 로 찾으세요.
- 새 소스를 추가하려면 `sources/base.py` 의 `Source` 를 상속해 `sources/__init__.py` 에 등록.
