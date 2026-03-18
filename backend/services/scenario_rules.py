import re
from typing import Dict, List


SCENARIO_RULES: Dict[str, Dict] = {
    "office": {
        "keywords": [
            "офис", "в офис", "на работу", "работа", "деловая встреча", "meeting", "business",
            "деловой стиль", "презентация", "собеседование", "в университет на защиту",
            "на пары", "в универ", "защита проекта", "formal", "smart casual",
            "деловой образ", "в переговорку", "деловой день"
        ],
        "required_categories": [],
        "preferred_categories": ["shirt", "sweater", "trousers", "shoes", "loafers", "blazer"],
        "forbidden_categories": ["shorts", "hoodie"],
        "forbidden_keywords": ["training", "sport", "running", "graphic"],
        "preferred_keywords": ["shirt", "knit", "derby", "loafer", "classic", "tailored"],
    },
    "date": {
        "keywords": [
            "свидание", "date", "романтический вечер", "ужин", "вечерний выход",
            "в ресторан", "на ужин", "на вечер", "романтика", "вечер с девушкой",
            "вечер с парнем"
        ],
        "required_categories": [],
        "preferred_categories": ["shirt", "sweater", "jeans", "trousers", "loafers", "shoes", "boots"],
        "forbidden_categories": ["shorts"],
        "forbidden_keywords": ["technical", "gym", "running", "sport", "performance", "training"],
        "preferred_keywords": ["knit", "shirt", "leather", "suede", "clean", "minimal"],
    },
    "rain": {
        "keywords": [
            "дождь", "в дождь", "прогулка в дождь", "ливень", "сырость",
            "дождливая погода", "непогода", "пасмурно", "rain", "wet weather",
            "морось", "мокро", "слякоть", "сырой день"
        ],
        "required_categories": [],
        "preferred_categories": ["jacket", "coat", "boots", "sneakers"],
        "forbidden_categories": ["loafers"],
        "forbidden_keywords": [],
        "preferred_keywords": ["water", "weather", "coat", "jacket", "boot"],
    },
    "gym": {
        "keywords": [
            "спортзал", "в спортзал", "зал", "в зал", "тренировка", "на тренировку",
            "gym", "fitness", "workout", "кардио", "силовая", "качалка", "фитнес",
            "беговая дорожка", "тренажерный зал", "running", "training"
        ],
        "required_categories": ["sneakers"],
        "preferred_categories": ["tshirt", "hoodie", "shorts", "sneakers"],
        "forbidden_categories": ["jeans", "shoes", "loafers", "coat", "blazer", "boots"],
        "forbidden_keywords": ["leather", "derby", "loafer", "cowboy"],
        "preferred_keywords": ["sport", "running", "training", "workout", "trainer", "performance"],
    },
    "old_money": {
        "keywords": [
            "олдмани", "олд мани", "old money", "oldmoney", "тихий люкс",
            "quiet luxury", "богатый минимализм", "аристократичный стиль",
            "дорогой спокойный образ", "classic luxury",
            "банкет", "гала", "вечерний бал", "бал", "торжественный вечер",
            "прием", "прием", "церемония"
        ],
        "required_categories": [],
        "preferred_categories": ["shirt", "trousers", "loafers", "sweater", "blazer", "coat", "shoes"],
        "forbidden_categories": ["hoodie"],
        "forbidden_keywords": ["sport", "graphic", "technical", "running", "training", "distressed"],
        "preferred_keywords": ["wool", "knit", "suede", "loafer", "tailored", "classic", "fine"],
    },
    "walk": {
        "keywords": [
            "прогулка", "на прогулку", "по городу", "в парк", "city walk",
            "casual day", "днем выйти", "пройтись", "на каждый день", "повседневный",
            "встреча с друзьями", "с друзьями", "дружеская встреча",
            "на матч", "на игру", "баскетбол", "футбол", "стадион"
        ],
        "required_categories": [],
        "preferred_categories": ["tshirt", "sweater", "jeans", "trousers", "sneakers", "boots", "jacket"],
        "forbidden_categories": [],
        "forbidden_keywords": [],
        "preferred_keywords": ["casual", "basic", "clean"],
    },
    "mountains": {
        "keywords": [
            "горы", "поход в горы", "в горы", "hiking", "треккинг",
            "поход", "на природу", "в лес", "outdoor", "camping"
        ],
        "required_categories": [],
        "preferred_categories": ["hoodie", "jacket", "boots", "sneakers", "trousers"],
        "forbidden_categories": ["loafers", "shoes"],
        "forbidden_keywords": ["leather", "formal", "derby"],
        "preferred_keywords": ["rugged", "outdoor", "boot", "utility", "technical"],
    },
    "water_park": {
        "keywords": [
            "аквапарк", "в аквапарк", "water park", "купаться", "водные горки",
            "пляжный парк", "зона бассейна"
        ],
        "required_categories": [],
        "preferred_categories": ["tshirt", "shorts", "sneakers"],
        "forbidden_categories": ["coat", "blazer", "boots", "sweater"],
        "forbidden_keywords": ["leather", "wool", "heavy", "formal"],
        "preferred_keywords": ["light", "sport", "casual", "short"],
    },
    "party": {
        "keywords": [
            "вечеринка", "party", "клуб", "в клуб", "тусовка", "ивент",
            "бар", "на вечеринку", "вечернее мероприятие"
        ],
        "required_categories": [],
        "preferred_categories": ["shirt", "tshirt", "jeans", "trousers", "boots", "shoes", "jacket"],
        "forbidden_categories": [],
        "forbidden_keywords": ["training", "sport"],
        "preferred_keywords": ["leather", "dark", "clean", "sharp"],
    },
    "airport": {
        "keywords": [
            "аэропорт", "в аэропорт", "перелет", "самолет", "flight",
            "дорога", "в путешествие", "поездка"
        ],
        "required_categories": [],
        "preferred_categories": ["hoodie", "tshirt", "trousers", "sneakers", "jacket"],
        "forbidden_categories": ["loafers"],
        "forbidden_keywords": ["formal", "heavy"],
        "preferred_keywords": ["comfort", "casual", "soft"],
    },
    "hot_weather": {
        "keywords": [
            "жара", "жарко", "летом", "летний образ", "summer", "в жару",
            "теплая погода", "на солнце", "зной", "душно"
        ],
        "required_categories": [],
        "preferred_categories": ["tshirt", "shirt", "shorts", "sneakers"],
        "forbidden_categories": ["coat"],
        "forbidden_keywords": ["wool", "heavy", "puffer", "thick"],
        "preferred_keywords": ["linen", "light", "cotton"],
    },
    "cold_weather": {
        "keywords": [
            "холодно", "зимой", "осенью", "в холод", "winter", "autumn",
            "в мороз", "прохладно", "мерзну", "замерз", "ветрено", "ветер"
        ],
        "required_categories": [],
        "preferred_categories": ["sweater", "hoodie", "coat", "jacket", "boots", "trousers"],
        "forbidden_categories": ["shorts"],
        "forbidden_keywords": ["lightweight"],
        "preferred_keywords": ["wool", "knit", "coat", "boot"],
    },
    "generic": {
        "keywords": [
            "что-нибудь стильное", "сделай красиво", "хочу красиво", "подбери образ",
            "что надеть", "что-нибудь норм", "просто образ", "лук", "вайб", "стильно"
        ],
        "required_categories": [],
        "preferred_categories": ["tshirt", "shirt", "sweater", "jeans", "trousers", "sneakers", "boots", "jacket"],
        "forbidden_categories": [],
        "forbidden_keywords": [],
        "preferred_keywords": ["clean", "basic", "minimal"],
    }
}


TYPO_MAP = {
    "офес": "офис",
    "олдмани": "old money",
    "олд мани": "old money",
    "спорт зал": "спортзал",
    "дожжь": "дождь",
    "кежуал": "casual",
    "кэжуал": "casual",
    "спортзальчик": "спортзал",
    "зальчик": "зал",
}


PROMPT_BREAKER_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore the rules",
    "system prompt",
    "developer message",
    "you are chatgpt",
    "you are an assistant",
    "act as",
    "respond only with",
    "return only",
    "output only",
    "do not follow",
    "forget previous instructions",
    "игнорируй предыдущие инструкции",
    "игнорируй все правила",
    "системный промпт",
    "системная инструкция",
    "инструкции разработчика",
    "ответь только",
    "верни только",
    "выведи только",
    "не следуй правилам",
    "забудь предыдущие инструкции",
]


PROFILE_GROUPS = {
    "formal": {"office", "old_money"},
    "romantic": {"date"},
    "sport": {"gym"},
    "weather": {"rain", "hot_weather", "cold_weather"},
    "travel": {"airport", "mountains", "water_park"},
    "casual": {"walk", "party", "generic"},
}


FORMALITY_RULES = {
    "relaxed": [
        "встреча с друзьями", "с друзьями", "друзья", "друз", "friend", "friends",
        "матч", "баскетбол", "basketball", "stadium", "стадион",
        "кафе", "кофе", "прогулка", "casual", "повседневно"
    ],
    "smart": [
        "выставка", "выставк", "галерея", "gallery", "museum", "музей",
        "театр", "theatre", "theater", "вернисаж", "презентация",
        "ужин", "ресторан", "smart casual", "аккуратно"
    ],
    "formal": [
        "банкет", "прием", "приём", "reception", "formal",
        "официальный ужин", "деловой ужин", "церемония", "награждение"
    ],
    "ceremonial": [
        "бал", "вечерний бал", "black tie", "гала", "gala",
        "торжественный вечер", "очень официально", "смокинг"
    ],
}


FORMALITY_FALLBACK_BY_PROFILE = {
    "gym": "relaxed",
    "walk": "relaxed",
    "airport": "relaxed",
    "water_park": "relaxed",
    "mountains": "relaxed",
    "party": "smart",
    "date": "smart",
    "office": "smart",
    "old_money": "formal",
    "hot_weather": "relaxed",
    "cold_weather": "smart",
    "generic": "smart",
}


CONFLICT_PAIRS = [
    ("office", "gym"),
    ("old_money", "gym"),
    ("office", "water_park"),
    ("date", "gym"),
    ("rain", "water_park"),
    ("cold_weather", "water_park"),
    ("hot_weather", "cold_weather"),
    ("office", "mountains"),
    ("office", "hot_weather"),
]


def sanitize_text(text: str) -> str:
    s = (text or "")[:260].lower().strip()
    s = s.replace("ё", "е")

    for phrase in PROMPT_BREAKER_PHRASES:
        s = s.replace(phrase, " ")

    s = re.sub(r"[^\w\s\-]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()

    for wrong, fixed in TYPO_MAP.items():
        s = s.replace(wrong, fixed)

    return s


def _match_profiles(clean_text: str) -> Dict[str, int]:
    scores: Dict[str, int] = {}

    for rule_name, rule in SCENARIO_RULES.items():
        if rule_name == "generic":
            continue

        score = 0
        for kw in rule["keywords"]:
            if kw in clean_text:
                score += max(1, len(kw.split()))

        if score > 0:
            scores[rule_name] = score

    return scores


def _detect_conflicts(matched_profiles: List[str]) -> List[str]:
    found = []
    matched = set(matched_profiles)

    for left, right in CONFLICT_PAIRS:
        if left in matched and right in matched:
            found.append(f"{left}_vs_{right}")

    return found


def _detect_formality(clean_text: str, profile: str) -> Dict:
    scores: Dict[str, int] = {}

    for level, keywords in FORMALITY_RULES.items():
        score = 0
        for kw in keywords:
            if kw in clean_text:
                score += max(1, len(kw.split()))
        if score > 0:
            scores[level] = score

    if scores:
        sorted_levels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_level, best_score = sorted_levels[0]
        total = sum(scores.values())
        confidence = round(best_score / total, 2) if total else 0.3
        matched_levels = [name for name, _ in sorted_levels]
        return {
            "formality": best_level,
            "formality_confidence": confidence,
            "matched_formality": matched_levels,
        }

    fallback_level = FORMALITY_FALLBACK_BY_PROFILE.get(profile, "smart")
    return {
        "formality": fallback_level,
        "formality_confidence": 0.25,
        "matched_formality": [],
    }


def detect_scenario_profile(scenario: str) -> str:
    result = normalize_user_request(scenario)
    return result["profile"]


def get_scenario_rule(scenario: str) -> Dict:
    profile = detect_scenario_profile(scenario)
    return SCENARIO_RULES.get(profile, SCENARIO_RULES["generic"])


def normalize_user_request(scenario: str) -> Dict:
    raw_text = (scenario or "").lower()
    clean_text = sanitize_text(scenario)
    detected_prompt_noise = [p for p in PROMPT_BREAKER_PHRASES if p in raw_text]
    scores = _match_profiles(clean_text)

    if not scores:
        formality_meta = _detect_formality(clean_text, "generic")
        return {
            "original": scenario,
            "clean_text": clean_text,
            "profile": "generic",
            "formality": formality_meta["formality"],
            "formality_confidence": formality_meta["formality_confidence"],
            "matched_formality": formality_meta["matched_formality"],
            "confidence": 0.2,
            "matched_profiles": [],
            "conflicts": [],
            "fallback_used": True,
            "note": "Запрос не распознан явно, использован generic fallback."
        }

    sorted_profiles = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    matched_profiles = [name for name, _ in sorted_profiles]
    best_profile, best_score = sorted_profiles[0]

    conflicts = _detect_conflicts(matched_profiles[:3])

    fallback_used = False
    note = ""

    if conflicts:
        fallback_used = True
        note = f"Обнаружены конфликтующие намерения: {', '.join(conflicts)}. Выбран доминирующий профиль."

    if detected_prompt_noise:
        fallback_used = True
        note = "В запросе были обнаружены служебные или ломающие формулировки. Они были проигнорированы."

    total_score = sum(scores.values())
    confidence = round(best_score / total_score, 2) if total_score > 0 else 0.2

    # слабая уверенность -> уходим в generic
    if confidence < 0.45 and best_profile not in {"office", "date", "gym", "rain"}:
        formality_meta = _detect_formality(clean_text, "generic")
        return {
            "original": scenario,
            "clean_text": clean_text,
            "profile": "generic",
            "formality": formality_meta["formality"],
            "formality_confidence": formality_meta["formality_confidence"],
            "matched_formality": formality_meta["matched_formality"],
            "confidence": confidence,
            "matched_profiles": matched_profiles,
            "conflicts": conflicts,
            "fallback_used": True,
            "note": "Запрос слишком неоднозначный, использован generic fallback."
        }

    formality_meta = _detect_formality(clean_text, best_profile)

    return {
        "original": scenario,
        "clean_text": clean_text,
        "profile": best_profile,
        "formality": formality_meta["formality"],
        "formality_confidence": formality_meta["formality_confidence"],
        "matched_formality": formality_meta["matched_formality"],
        "confidence": confidence,
        "matched_profiles": matched_profiles,
        "conflicts": conflicts,
        "fallback_used": fallback_used,
        "note": note
    }
