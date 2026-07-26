"""영어 카테고리/검색어 → 한국어 태그 매핑.

Pixabay 등 소스의 영어 태그는 부정확하므로, 신뢰도 높은 category + query 를
한국어로 변환해 태그로 사용한다.
"""
from __future__ import annotations

CATEGORY_KO = {
    "beauty": "뷰티", "business": "비즈니스", "car": "자동차", "city-life": "도시생활",
    "coffee-cafe": "카페", "countryside": "시골", "culture-art": "문화예술",
    "daily-life": "일상", "economy": "경제", "education": "교육", "emotion": "감정",
    "entertainment": "연예", "environment": "환경", "family": "가족", "fashion": "패션",
    "finance-invest": "투자금융", "food": "음식", "health": "건강", "interior": "인테리어",
    "job-career": "취업", "korea-politics": "한국정치", "law-justice": "법",
    "love-couple": "연애", "medical": "의료", "money": "돈", "nature": "자연",
    "pet": "반려동물", "politics": "정치", "science": "과학", "season-weather": "계절날씨",
    "senior": "시니어", "shopping": "쇼핑", "sports": "스포츠", "subsidy": "지원금",
    "technology": "기술", "travel": "여행", "wedding": "결혼", "work": "직장", "youth": "청년",
}

QUERY_KO = {
    "Lee Jae-myung": "이재명", "Oh Se-hoon": "오세훈",
    "anxiety fear": "불안", "aquarium fish": "수족관 물고기", "art museum gallery": "미술관",
    "atm machine": "ATM 현금인출기", "autumn foliage": "단풍", "autumn harvest": "가을 수확",
    "awards show": "시상식", "baby infant": "아기", "backpacker traveler": "배낭여행객",
    "bakery bread": "베이커리 빵", "ballet dance": "발레", "ballot box vote": "투표함",
    "basketball": "농구", "basketball game": "농구 경기", "benefit document": "수급 서류",
    "blood pressure check": "혈압 측정", "bride bouquet": "신부 부케", "budget planning": "예산 계획",
    "business growth": "사업 성장", "business meeting": "비즈니스 미팅",
    "business negotiation": "비즈니스 협상", "business networking": "비즈니스 네트워킹",
    "busy crosswalk": "붐비는 횡단보도", "car charging station": "전기차 충전소",
    "car dashboard interior": "자동차 대시보드", "career growth ladder": "커리어 성장",
    "chemistry experiment": "화학 실험", "cherry blossom spring": "봄 벚꽃",
    "child allowance": "아동 수당", "children learning": "어린이 학습", "city commute": "도시 출퇴근",
    "city financial district": "도시 금융가", "city hall building": "시청 건물",
    "city sightseeing": "도시 관광", "city skyline": "도시 스카이라인", "city skyline night": "도시 야경",
    "cleaning house": "집 청소", "clear blue sky": "파란 하늘", "climate change": "기후 변화",
    "cloud computing": "클라우드 컴퓨팅", "coffee cafe": "커피 카페", "college students": "대학생",
    "concert stage": "콘서트 무대", "cooking ingredients": "요리 재료", "corporate building": "기업 빌딩",
    "couple hug": "커플 포옹", "coworking space": "공유 오피스", "cozy bedroom": "아늑한 침실",
    "crying tears": "눈물", "cryptocurrency bitcoin": "암호화폐 비트코인", "cute dog": "귀여운 강아지",
    "cybersecurity": "사이버 보안", "dance performance": "댄스 공연", "date night dinner": "데이트 저녁",
    "deadline stress": "마감 스트레스", "delivery courier package": "택배 배송", "dental care": "치아 관리",
    "desert sand dune": "사막 모래언덕", "dessert cake": "디저트 케이크", "diplomacy meeting": "외교 회담",
    "discount sale tag": "할인 세일", "doctor patient": "의사 환자", "doctor stethoscope": "의사 청진기",
    "dog walking": "강아지 산책", "doing laundry": "빨래", "dollar bills": "달러 지폐",
    "economic growth arrow": "경제 성장 화살표", "economic growth chart": "경제 성장 차트",
    "elderly couple": "노부부", "election campaign": "선거 캠페인", "election voting": "선거 투표",
    "electric car": "전기차", "engagement couple": "약혼 커플", "entrepreneur working": "창업가",
    "exam test paper": "시험지", "excited celebration joy": "환호 축하", "factory production": "공장 생산",
    "family dinner table": "가족 식사", "family picnic": "가족 피크닉", "family together": "가족",
    "family vacation": "가족 휴가", "farm barn": "농장 헛간", "fashion outfit": "패션 코디",
    "film production": "영화 제작", "financial advisor": "재무 상담사", "financial help hand": "재정 지원",
    "foggy morning": "안개 낀 아침", "fresh fruit": "신선한 과일", "generation z": "Z세대",
    "gift box present": "선물 상자", "global economy": "글로벌 경제", "gold investment": "금 투자",
    "golf course": "골프장", "government grant document": "정부 지원금 서류", "government policy": "정부 정책",
    "graduation": "졸업", "graduation ceremony": "졸업식", "grandmother portrait": "할머니 초상",
    "grandparents": "조부모", "green forest path": "숲길", "groom suit": "신랑 정장",
    "hair styling salon": "헤어살롱", "handbag purse": "핸드백", "handshake business deal": "사업 악수",
    "handshake hiring": "채용 악수", "healthy lifestyle": "건강한 생활", "highway driving": "고속도로 운전",
    "holding hands": "손잡기", "home cooking": "집밥 요리", "hospital ward": "병원 병동",
    "inflation price rising": "물가 상승", "jewelry accessories": "주얼리 액세서리",
    "job interview": "취업 면접", "justice scale": "정의의 저울", "kitchen interior": "주방 인테리어",
    "kitten cat": "새끼 고양이", "korean bbq": "한식 바비큐", "korean won money": "원화",
    "laboratory research": "실험실 연구", "laughing joy": "웃음", "lawyer office": "변호사 사무실",
    "legal contract signing": "법률 계약 서명", "live band concert": "라이브 밴드 공연",
    "love affection": "사랑", "luxury car": "럭셔리 자동차", "makeup cosmetics": "화장품 메이크업",
    "manicure nails": "네일 매니큐어", "marriage proposal": "청혼", "martial arts": "무술",
    "medical checkup": "건강 검진", "medicine pills": "알약", "mental health": "정신 건강",
    "microphone singer": "마이크 가수", "microscope": "현미경", "minimalist decor": "미니멀 인테리어",
    "modern living room": "모던 거실", "morning routine": "아침 루틴", "mountain hiking": "등산",
    "mountain landscape": "산 풍경", "mountain scenery": "산 경치", "northern lights aurora": "오로라",
    "nurse patient care": "간호 돌봄", "nursing home": "요양원", "ocean sunset": "바다 노을",
    "office desk": "사무실 책상", "office teamwork": "사무실 팀워크", "oil painting": "유화",
    "online class laptop": "온라인 수업", "online learning": "온라인 학습", "online shopping": "온라인 쇼핑",
    "orchestra concert": "오케스트라 공연", "packing suitcase": "여행 짐싸기", "parenting baby": "육아",
    "parliament congress": "국회", "passport airport": "여권 공항", "pension retirement fund": "연금 은퇴자금",
    "perfume bottle": "향수병", "pet food bowl": "반려동물 사료", "pet grooming": "반려동물 미용",
    "physics formula": "물리 공식", "plastic pollution ocean": "해양 플라스틱 오염",
    "politics debate": "정치 토론", "rain umbrella": "비 우산", "rainy day umbrella": "비 오는 날 우산",
    "real estate investment": "부동산 투자", "recycling waste": "재활용", "red carpet event": "레드카펫 행사",
    "remote work home": "재택근무", "resume cv document": "이력서", "retail store": "소매점",
    "retirement life": "은퇴 생활", "rice field": "논", "river stream": "강 시냇물",
    "road trip car": "자동차 로드트립", "romantic couple": "로맨틱 커플",
    "runway fashion model": "런웨이 패션모델", "rural village": "시골 마을", "saving money jar": "저금통",
    "scandinavian interior": "북유럽 인테리어", "science project": "과학 프로젝트",
    "scrolling smartphone": "스마트폰 스크롤", "sculpture statue": "조각상",
    "senior citizen smiling": "웃는 노인", "senior health care": "시니어 건강관리", "shopping mall": "쇼핑몰",
    "siblings playing": "형제자매 놀이", "skincare routine": "스킨케어", "sky clouds": "하늘 구름",
    "skyscraper building": "고층 빌딩", "sleeping rest": "수면 휴식", "smart home device": "스마트홈 기기",
    "smartphone app": "스마트폰 앱", "sneakers shoes": "운동화", "snow winter": "겨울 눈",
    "soccer match": "축구 경기", "social security card": "사회보장 카드",
    "software developer coding": "개발자 코딩", "solar energy panel": "태양광 패널",
    "spa treatment": "스파 관리", "space galaxy stars": "우주 은하", "spotlight performance": "스포트라이트 공연",
    "stage spotlight": "무대 조명", "startup team": "스타트업 팀", "stock market crash": "증시 폭락",
    "stock trading chart": "주식 차트", "street art graffiti": "거리 예술 그래피티", "street food": "길거리 음식",
    "streetwear style": "스트리트 패션", "students studying together": "함께 공부하는 학생들",
    "subway station": "지하철역", "summer beach sun": "여름 해변", "sunset sky": "노을 하늘",
    "supply chain logistics": "공급망 물류", "surgery operation": "수술", "surprise shock face": "놀란 표정",
    "sushi japanese food": "초밥 일식", "taking notes": "필기", "tax calculation": "세금 계산",
    "teacher lecture": "교사 강의", "team brainstorming": "팀 브레인스토밍", "team meeting": "팀 회의",
    "tennis player": "테니스 선수", "tired exhausted": "피곤함", "tractor farming": "트랙터 농사",
    "traffic jam": "교통 체증", "train journey": "기차 여행", "tree planting": "나무 심기",
    "tropical resort": "열대 리조트", "tv studio": "TV 스튜디오", "unemployment support": "실업 지원",
    "university campus": "대학 캠퍼스", "urban street": "도심 거리", "vaccine injection": "백신 주사",
    "valentine heart": "발렌타인 하트", "vegetable garden": "채소밭", "vegetarian salad": "채식 샐러드",
    "video conference call": "화상 회의", "vintage classic car": "빈티지 클래식카",
    "virtual reality headset": "VR 헤드셋", "vitamins supplement": "비타민 영양제",
    "watching television": "TV 시청", "waterfall": "폭포", "wedding ceremony": "결혼식",
    "wedding rings": "결혼반지", "wedding venue decoration": "결혼식장 장식", "welfare benefit": "복지 혜택",
    "wild animals": "야생동물", "wind turbine": "풍력 터빈", "winter snow": "겨울 눈",
    "young entrepreneur": "청년 창업가", "young professionals team": "젊은 직장인 팀",
    "youth culture street": "청년 문화 거리",
    # search 명령으로 들어온 것들
    "korean young people": "한국 청년", "young people group": "청년 그룹",
    "asian young woman": "아시아 젊은 여성", "job seeker interview": "구직자 면접",
    "young adults friends": "청년 친구들", "korean youth": "한국 청년",
    "young people": "청년", "asian students": "아시아 학생",
}


def category_ko(category: str | None) -> str:
    return CATEGORY_KO.get((category or "").strip(), (category or "").strip())


def query_ko(query: str | None) -> str:
    q = (query or "").strip()
    return QUERY_KO.get(q, q)


def korean_tags(category: str | None, query: str | None) -> str:
    """카테고리+검색어를 한국어 태그 문자열로. 예: '정치, 국회'"""
    parts = []
    ck = category_ko(category)
    if ck:
        parts.append(ck)
    qk = query_ko(query)
    if qk and qk != ck:
        parts.append(qk)
    return ", ".join(parts)
