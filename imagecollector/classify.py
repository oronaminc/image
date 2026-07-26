"""원본(영어) 태그로 이미지가 그 카테고리에 맞는지 판정한다.

왜 필요한가:
  수집이 '최신순 + 2024년 이후' 로 돌아서, 검색어와 느슨하게 걸린 사진이 많이
  섞여 들어왔다. (지원금 카테고리에 다람쥐 = `welfare benefit` 이 `animal welfare`
  를 잡은 것) 소스가 준 원본 태그를 카테고리 어휘와 대조하면 이런 오분류를
  기계적으로 걸러낼 수 있다.

판정:
  점수 = (이미지 태그 ∩ 카테고리 어휘) 개수.
  현재 카테고리 점수가 0이면 '불일치'. 다른 카테고리가 점수를 얻으면 그쪽을 제안하고,
  아무 카테고리도 점수를 못 얻으면 '판정 불가'(사람이 보거나 삭제).
"""
from __future__ import annotations

import re

CATEGORY_VOCAB: dict[str, set[str]] = {
    "politics": {
        "politics", "political", "government", "parliament", "congress", "senate",
        "election", "vote", "voting", "ballot", "democracy", "president", "minister",
        "flag", "capitol", "city hall", "town hall", "podium", "speech", "protest",
        "demonstration", "rally", "diplomacy", "summit", "policy", "politician",
        "campaign", "referendum", "law", "state", "nation", "national",
    },
    "entertainment": {
        "concert", "stage", "band", "singer", "music", "microphone", "musician",
        "performance", "dance", "dancing", "dancer", "theater", "theatre", "cinema",
        "movie", "film", "camera", "studio", "spotlight", "award", "festival",
        "audience", "guitar", "drums", "show", "actor", "actress", "entertainment",
        "karaoke", "dj", "party",
    },
    "subsidy": {
        "money", "cash", "coin", "coins", "banknote", "bill", "bills", "currency",
        "donation", "donate", "charity", "help", "helping", "support", "aid",
        "welfare", "benefit", "voucher", "coupon", "grant", "subsidy", "allowance",
        "document", "form", "application", "envelope", "finance", "financial",
        "social security", "poverty", "giving", "give", "hand",
    },
    "money": {
        "money", "cash", "coin", "coins", "banknote", "bill", "bills", "currency",
        "dollar", "dollars", "euro", "euros", "won", "yen", "wallet", "purse",
        "atm", "bank", "banking", "savings", "save", "piggy bank", "budget",
        "tax", "taxes", "salary", "wage", "payment", "pay", "finance", "financial",
        "invoice", "receipt", "calculator",
    },
    "economy": {
        "economy", "economic", "inflation", "recession", "market", "trade", "trading",
        "supply", "logistics", "container", "port", "shipping", "cargo", "factory",
        "industry", "industrial", "production", "manufacturing", "chart", "graph",
        "growth", "statistics", "stock", "price", "prices", "gdp", "crisis",
        "warehouse", "truck", "crane", "oil", "gas station", "fuel",
    },
    "daily-life": {
        "home", "house", "room", "kitchen", "living room", "morning", "routine",
        "laundry", "washing", "cleaning", "clean", "dishes", "television", "tv",
        "smartphone", "phone", "coffee", "breakfast", "bed", "sofa", "couch",
        "notes", "notebook", "diary", "alarm", "clock", "grocery", "shopping bag",
        "bus", "commute", "everyday", "lifestyle", "relax", "rest",
    },
    "emotion": {
        "emotion", "emotional", "sad", "sadness", "cry", "crying", "tears", "happy",
        "happiness", "smile", "smiling", "laugh", "laughing", "joy", "angry", "anger",
        "fear", "anxiety", "anxious", "stress", "stressed", "depression", "depressed",
        "lonely", "loneliness", "love", "tired", "exhausted", "surprise", "shock",
        "face", "portrait", "expression", "feeling", "mood", "hope", "worry",
    },
    "health": {
        "health", "healthy", "fitness", "exercise", "workout", "gym", "yoga",
        "running", "jogging", "stretching", "diet", "nutrition", "vitamin",
        "vitamins", "supplement", "wellness", "sleep", "water", "hydration",
        "blood pressure", "checkup", "dental", "teeth", "tooth", "mental health",
        "meditation", "scale", "weight", "muscle", "body", "care",
    },
    "work": {
        "work", "working", "office", "desk", "business", "meeting", "team",
        "teamwork", "colleague", "coworker", "employee", "job", "laptop", "computer",
        "presentation", "whiteboard", "conference", "video call", "remote work",
        "deadline", "brainstorming", "document", "paperwork", "headset",
        "call center", "worker", "factory", "professional", "corporate",
    },
    "technology": {
        "technology", "tech", "computer", "laptop", "smartphone", "phone", "app",
        "software", "code", "coding", "programming", "developer", "data", "server",
        "cloud", "cyber", "security", "internet", "network", "digital", "robot",
        "robotics", "artificial intelligence", "ai", "virtual reality", "vr",
        "drone", "smartwatch", "chip", "circuit", "electronics", "innovation",
    },
    "travel": {
        "travel", "traveler", "trip", "journey", "vacation", "holiday", "tourism",
        "tourist", "passport", "airport", "airplane", "plane", "flight", "luggage",
        "suitcase", "backpack", "backpacker", "hotel", "resort", "beach", "island",
        "sightseeing", "map", "train", "railway", "adventure", "explore", "hiking",
        "landmark", "destination",
    },
    "food": {
        "food", "meal", "dish", "cooking", "cook", "kitchen", "recipe", "restaurant",
        "bread", "bakery", "cake", "dessert", "fruit", "vegetable", "vegetables",
        "salad", "meat", "barbecue", "bbq", "grill", "noodle", "noodles", "soup",
        "rice", "sushi", "kimchi", "snack", "lunch", "dinner", "breakfast",
        "delicious", "eat", "eating", "plate", "chef", "street food",
    },
    "nature": {
        "nature", "landscape", "forest", "tree", "trees", "wood", "woods", "mountain",
        "mountains", "hill", "river", "stream", "lake", "waterfall", "ocean", "sea",
        "wave", "waves", "beach", "sky", "cloud", "clouds", "sunset", "sunrise",
        "desert", "dune", "aurora", "star", "stars", "flower", "flowers", "plant",
        "grass", "wildlife", "animal", "bird", "scenery", "natural", "outdoor",
        # 야생 동식물 이름 — `animal`·`bird` 같은 말은 너무 흔해서 판단에서 빠지므로
        # 종 이름을 직접 넣어야 야생동물 사진이 제 카테고리를 찾는다
        "frog", "toad", "amphibian", "reptile", "lizard", "snake", "turtle", "tortoise",
        "swan", "duck", "goose", "heron", "owl", "eagle", "hawk", "falcon", "sparrow",
        "robin", "seagull", "gull", "pigeon", "dove", "crow", "woodpecker", "songbird",
        "deer", "fox", "wolf", "bear", "squirrel", "rabbit", "hare", "hedgehog",
        "mouse", "badger", "otter", "seal", "dolphin", "whale", "elephant", "lion",
        "tiger", "monkey", "zebra", "giraffe", "insect", "bee", "wasp", "butterfly",
        "moth", "dragonfly", "beetle", "ant", "spider", "snail", "caterpillar",
        "moss", "fern", "mushroom", "leaf", "leaves", "petal", "petals", "blossom",
        "bloom", "rose", "tulip", "orchid", "lily", "daisy", "sunflower", "lavender",
        "cactus", "palm", "pine", "oak", "maple", "branch", "meadow", "valley",
        "cliff", "rock", "stone", "waterbird", "wildflower", "pond", "creek",
        "horizon", "fauna", "flora",
        # 동물의 몸·서식지 단어 (종 이름을 다 넣을 수는 없어서 이쪽으로 보완)
        "plumage", "beak", "avian", "feather", "feathers", "wing", "wings", "nest",
        "fur", "paw", "claw", "tail", "whiskers", "antler", "horn", "hoof", "mane",
        "savanna", "jungle", "safari", "habitat", "herd", "flock", "swarm", "perch",
        "grazing", "migration", "ornithology", "birdwatching", "mammal", "rodent",
        "predator", "prey", "aquatic", "marine", "botanical", "foliage", "pollen",
        "pollination", "nectar", "seed", "roots", "trunk", "bark",
    },
    "education": {
        "education", "school", "classroom", "class", "student", "students", "study",
        "studying", "teacher", "lecture", "university", "college", "campus",
        "library", "book", "books", "reading", "exam", "test", "homework",
        "learning", "learn", "kindergarten", "children", "graduation", "diploma",
        "notebook", "pencil", "blackboard", "science project", "school bus",
    },
    "family": {
        "family", "parent", "parents", "mother", "mom", "father", "dad", "child",
        "children", "kid", "kids", "baby", "infant", "newborn", "son", "daughter",
        "sibling", "siblings", "brother", "sister", "grandparent", "grandparents",
        "grandmother", "grandfather", "together", "home", "picnic", "parenting",
        "childhood", "generation",
    },
    "sports": {
        "sport", "sports", "soccer", "football", "basketball", "baseball", "tennis",
        "golf", "swimming", "swim", "cycling", "bicycle", "bike", "running", "runner",
        "marathon", "athlete", "gym", "fitness", "workout", "stadium", "match",
        "game", "team", "ball", "racket", "competition", "training", "martial arts",
        "boxing", "badminton", "player",
    },
    "season-weather": {
        "season", "spring", "summer", "autumn", "fall", "winter", "weather", "snow",
        "snowy", "rain", "rainy", "umbrella", "storm", "typhoon", "cloud", "clouds",
        "fog", "foggy", "mist", "sun", "sunny", "heat", "cold", "frost", "ice",
        "cherry blossom", "foliage", "leaves", "temperature", "wind", "sky",
    },
    "business": {
        "business", "corporate", "company", "startup", "entrepreneur", "office",
        "meeting", "negotiation", "handshake", "deal", "contract", "growth",
        "strategy", "management", "manager", "presentation", "conference",
        "teamwork", "professional", "success", "partnership", "coworking",
        "warehouse", "logistics", "shop", "store owner", "suit",
    },
    "finance-invest": {
        "finance", "financial", "invest", "investment", "investor", "stock",
        "stocks", "trading", "chart", "graph", "market", "crypto", "cryptocurrency",
        "bitcoin", "blockchain", "bank", "banking", "savings", "pension",
        "retirement", "insurance", "loan", "mortgage", "interest", "gold",
        "real estate", "portfolio", "profit", "wealth", "money", "coin", "coins",
    },
    "shopping": {
        "shopping", "shop", "store", "retail", "mall", "market", "supermarket",
        "grocery", "cart", "basket", "sale", "discount", "price", "tag", "gift",
        "present", "package", "parcel", "delivery", "courier", "online shopping",
        "ecommerce", "customer", "buy", "buying", "purchase", "checkout", "kiosk",
        "boutique", "bag", "bags",
    },
    "beauty": {
        "beauty", "cosmetic", "cosmetics", "makeup", "lipstick", "skincare", "skin",
        "face", "cream", "lotion", "mask", "spa", "massage", "salon", "hair",
        "hairstyle", "haircut", "manicure", "nails", "nail", "perfume", "fragrance",
        "brush", "mirror", "treatment", "wellness", "grooming", "barber",
    },
    "fashion": {
        "fashion", "style", "outfit", "clothes", "clothing", "dress", "shirt",
        "coat", "jacket", "jeans", "denim", "shoes", "sneakers", "boots", "heels",
        "bag", "handbag", "purse", "jewelry", "necklace", "ring", "watch",
        "sunglasses", "accessories", "model", "runway", "streetwear", "wardrobe",
        "wear", "trendy",
    },
    "interior": {
        "interior", "home", "house", "apartment", "room", "living room", "bedroom",
        "kitchen", "bathroom", "furniture", "sofa", "couch", "chair", "table",
        "bed", "lamp", "lighting", "decor", "decoration", "shelf", "closet",
        "curtain", "carpet", "rug", "minimalist", "scandinavian", "cozy",
        "balcony", "home office", "design",
    },
    "car": {
        "car", "cars", "vehicle", "auto", "automobile", "driving", "drive", "driver",
        "road", "highway", "traffic", "parking", "garage", "engine", "wheel",
        "tire", "dashboard", "steering", "electric car", "ev", "charging",
        "charger", "suv", "truck", "motorcycle", "bike", "transport", "speed",
        "vintage car", "luxury car",
    },
    "pet": {
        "pet", "pets", "dog", "puppy", "cat", "kitten", "animal", "animals",
        "hamster", "rabbit", "bird", "parrot", "fish", "aquarium", "veterinary",
        "vet", "grooming", "leash", "collar", "paw", "fur", "cute", "walking dog",
        "pet food", "kennel", "companion",
    },
    "wedding": {
        "wedding", "bride", "groom", "marriage", "married", "ceremony", "bouquet",
        "ring", "rings", "engagement", "proposal", "veil", "wedding dress", "tuxedo",
        "reception", "celebration", "honeymoon", "invitation", "couple", "love",
        "romantic", "church", "banquet", "decoration",
    },
    "culture-art": {
        "art", "artist", "painting", "paint", "canvas", "gallery", "museum",
        "sculpture", "statue", "exhibition", "graffiti", "street art", "ballet",
        "dance", "orchestra", "concert", "music", "classical", "theater", "theatre",
        "culture", "cultural", "traditional", "craft", "pottery", "calligraphy",
        "photography", "creative", "design", "book",
    },
    "science": {
        "science", "scientific", "scientist", "laboratory", "lab", "research",
        "experiment", "microscope", "chemistry", "chemical", "physics", "biology",
        "dna", "genetics", "molecule", "atom", "space", "galaxy", "universe",
        "star", "stars", "planet", "telescope", "astronomy", "formula", "data",
        "technology", "discovery", "brain", "neuroscience",
    },
    "medical": {
        "medical", "medicine", "doctor", "nurse", "hospital", "clinic", "patient",
        "health", "healthcare", "stethoscope", "surgery", "operation", "injection",
        "vaccine", "syringe", "pill", "pills", "tablet", "pharmacy", "drug",
        "treatment", "therapy", "diagnosis", "ambulance", "emergency", "blood",
        "laboratory", "dentist", "mask", "care",
    },
    "environment": {
        "environment", "environmental", "eco", "ecology", "green", "sustainable",
        "sustainability", "recycle", "recycling", "waste", "pollution", "plastic",
        "climate", "climate change", "solar", "solar panel", "wind turbine",
        "renewable", "energy", "nature", "tree", "planting", "forest", "earth",
        "conservation", "carbon", "clean energy", "organic",
    },
    "city-life": {
        "city", "urban", "downtown", "skyline", "skyscraper", "building",
        "buildings", "street", "road", "crosswalk", "traffic", "subway", "metro",
        "station", "bus", "commute", "pedestrian", "sidewalk", "night", "neon",
        "apartment", "construction", "crane", "rooftop", "town", "architecture",
        "crowd", "public transport",
    },
    "countryside": {
        "countryside", "rural", "village", "farm", "farmer", "farming",
        "agriculture", "field", "fields", "rice", "barn", "tractor", "harvest",
        "crop", "crops", "orchard", "garden", "vegetable", "livestock", "cattle",
        "cow", "sheep", "chicken", "greenhouse", "meadow", "pasture", "country road",
        "hay", "grain",
    },
    "senior": {
        "senior", "seniors", "elderly", "old", "older", "aged", "aging", "grandma",
        "grandmother", "grandpa", "grandfather", "grandparent", "grandparents",
        "retirement", "retired", "pension", "nursing", "care", "wrinkle", "wrinkles",
        "walking stick", "cane", "old man", "old woman", "old couple",
    },
    "job-career": {
        "job", "career", "interview", "resume", "cv", "hiring", "recruit",
        "recruitment", "employment", "employee", "employer", "work", "office",
        "professional", "handshake", "training", "workshop", "certificate",
        "graduation", "networking", "promotion", "success", "ladder", "candidate",
        "application", "job fair", "business",
    },
    "law-justice": {
        "law", "legal", "justice", "court", "courtroom", "judge", "gavel", "lawyer",
        "attorney", "jury", "trial", "verdict", "contract", "signing", "police",
        "policeman", "officer", "crime", "criminal", "handcuffs", "prison", "jail",
        "security", "cctv", "rights", "scale", "statute", "regulation",
    },
    "love-couple": {
        "love", "couple", "romance", "romantic", "date", "dating", "kiss",
        "hug", "hugging", "holding hands", "heart", "valentine", "affection",
        "boyfriend", "girlfriend", "together", "relationship", "proposal",
        "engagement", "flowers", "gift", "sunset couple", "intimacy",
    },
    "youth": {
        "youth", "young", "teenager", "teen", "student", "students", "college",
        "university", "campus", "generation", "millennial", "friends", "friendship",
        "group", "fun", "hangout", "smartphone", "sneakers", "graduation",
        "startup", "entrepreneur", "job seeker", "young people", "young adult",
        "young woman", "young man",
    },
    "coffee-cafe": {
        "coffee", "cafe", "espresso", "latte", "cappuccino", "barista", "cup",
        "mug", "beans", "coffee shop", "brew", "brewing", "dessert", "bakery",
        "croissant", "tea", "drink", "interior", "table",
    },
    "korea-politics": {
        "korea", "korean", "seoul", "politics", "political", "government",
        "president", "parliament", "assembly", "election", "flag", "policy",
    },
    "search": set(),
}

_SPLIT = re.compile(r"[,\|/]+")


def tag_set(source_tags: str | None) -> set[str]:
    """'dog, animal, cute' → {'dog','animal','cute'} (+ 각 단어도 따로)"""
    tags: set[str] = set()
    for raw in _SPLIT.split((source_tags or "").lower()):
        tag = raw.strip()
        if not tag:
            continue
        tags.add(tag)
        for word in tag.split():
            if len(word) > 2:
                tags.add(word)
    return tags


# 라이브러리의 몇 %에 붙어 있으면 '너무 흔한 태그' 로 보고 판단에서 뺄지
GENERIC_RATIO = 0.05


def build_generic_tags(conn, ratio: float = GENERIC_RATIO) -> set[str]:
    """라이브러리 전체에서 너무 흔한 태그를 골라낸다.

    Pixabay 태그는 `nature`(전체의 38%), `beauty`(10%), `fashion`(10%) 처럼
    아무 사진에나 붙는 말이 많다. 이런 태그를 그대로 쓰면 모든 사진이 nature 로
    끌려가므로 판단 근거에서 제외한다.
    """
    from collections import Counter
    rows = [r[0] for r in conn.execute(
        "SELECT source_tags FROM images "
        "WHERE source_tags IS NOT NULL AND source_tags NOT IN ('', '-', '(삭제됨)')"
    )]
    if not rows:
        return set()
    counter: Counter = Counter()
    for raw in rows:
        counter.update(tag_set(raw))
    cutoff = len(rows) * ratio
    return {tag for tag, n in counter.items() if n > cutoff}


def score(tags: set[str], category: str, generic: set[str] | None = None) -> int:
    """카테고리 어휘와 겹치는 태그 수 (흔한 태그는 제외)."""
    vocab = CATEGORY_VOCAB.get(category)
    if not vocab:
        return 0
    hits = tags & vocab
    if generic:
        hits = hits - generic
    return len(hits)


def best_categories(tags: set[str], top: int = 3,
                    generic: set[str] | None = None) -> list[tuple[str, int]]:
    """점수가 높은 카테고리 순으로. 점수 0 은 제외."""
    scored = [(cat, score(tags, cat, generic)) for cat in CATEGORY_VOCAB]
    scored = [(c, s) for c, s in scored if s > 0]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:top]


# 현재 카테고리가 이만큼 밀리면 오분류로 본다 (1점 차이는 우열을 가리기 어려움)
MARGIN = 2
# 옮길 곳은 최소 이 점수는 되어야 한다 (태그 하나 걸린 것만으로 옮기면 오히려 틀린다)
MIN_SUGGEST = 2


def audit(source_tags: str | None, category: str, generic: set[str] | None = None) -> dict:
    """한 장 판정: 현재 카테고리가 맞는지 / 아니면 어디로 갈지.

    - 현재 점수가 0  → 불일치 (카테고리와 겹치는 태그가 하나도 없음)
    - 다른 카테고리가 MARGIN 이상 높음 → 불일치 (그쪽이 확실히 더 맞음)
    - 아무 카테고리도 점수를 못 얻음 → 판정 불가 (태그가 너무 일반적)
    """
    tags = tag_set(source_tags)
    current = score(tags, category, generic)
    ranked = best_categories(tags, top=5, generic=generic)
    best = ranked[0] if ranked else None
    best_score = best[1] if best else 0

    movable = bool(best and best[0] != category and best_score >= MIN_SUGGEST)
    outranked = movable and best_score - current >= MARGIN
    return {
        "current_score": current,
        "ok": current > 0 and not outranked,
        "suggested": best[0] if movable else None,
        "suggested_score": best_score,
        "ranked": ranked,
        # 옮길 곳을 못 정하면 '판정 불가' — 사람이 보거나 그대로 둔다
        "unclear": not ranked or (current == 0 and not movable),
    }
