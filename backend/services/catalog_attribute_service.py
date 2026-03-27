import re
from typing import Any, Dict, Optional, Set


def _normalize_text(*parts: Any) -> str:
    return re.sub(r"\s+", " ", " ".join(str(part or "") for part in parts).strip()).lower()


MATERIAL_KEYWORDS = {
    "cotton": {"cotton", "хлоп", "джерси"},
    "linen": {"linen", "лен", "льня"},
    "wool": {"wool", "шерст", "мерино", "merino"},
    "denim": {"denim", "джинс"},
    "leather": {"leather", "кожа", "кожан"},
    "suede": {"suede", "замш"},
    "fleece": {"fleece", "флис"},
    "knit": {"knit", "вязан", "трикот", "джемпер"},
    "down": {"down", "пух"},
    "membrane": {"membrane", "мембран", "gore", "recco"},
    "softshell": {"softshell", "софтшелл"},
}

FIT_KEYWORDS = {
    "oversized": {"oversize", "oversized", "оверсайз"},
    "regular": {"regular", "regular fit", "прямого кроя", "базов"},
    "slim": {"slim", "slim fit", "зауж"},
    "relaxed": {"relaxed", "baggy", "wide-leg", "wide leg", "свободн", "широк"},
    "straight": {"straight", "straight-leg", "straight leg", "прям"},
    "cropped": {"cropped", "укороч"},
}

SUBCATEGORY_RULES = {
    "jacket": [
        ("parka", {"parka", "парка"}),
        ("bomber", {"bomber", "бомбер"}),
        ("windbreaker", {"windbreaker", "ветров"}),
        ("puffer_jacket", {"puffer", "down jacket", "пухов", "стеган"}),
        ("shell_jacket", {"shell", "softshell", "hardshell"}),
        ("overshirt", {"overshirt", "рубашка-куртка"}),
        ("anorak", {"anorak", "анорак"}),
    ],
    "coat": [
        ("trench_coat", {"trench", "тренч"}),
        ("wool_coat", {"wool coat", "шерстя"}),
        ("puffer_coat", {"puffer", "пухов"}),
        ("maxi_coat", {"maxi", "макси"}),
    ],
    "trousers": [
        ("cargo_trousers", {"cargo", "карго"}),
        ("joggers", {"jogger", "джоггер"}),
        ("leggings", {"legging", "леггин"}),
        ("chinos", {"chino", "чинос"}),
        ("wide_leg_trousers", {"wide-leg", "wide leg", "широк"}),
        ("pleated_trousers", {"pleated", "защип"}),
        ("ski_trousers", {"ski", "лыж"}),
    ],
    "shorts": [
        ("cargo_shorts", {"cargo", "карго"}),
        ("running_shorts", {"running", "runner", "бег"}),
        ("bermuda_shorts", {"bermuda", "бермуд"}),
    ],
    "shirt": [
        ("polo_shirt", {"polo", "поло"}),
        ("overshirt", {"overshirt"}),
        ("blouse", {"blouse", "блуз"}),
        ("linen_shirt", {"linen", "льня"}),
    ],
    "tshirt": [
        ("tank_top", {"tank", "майк"}),
        ("longsleeve", {"long sleeve", "лонгслив"}),
        ("graphic_tshirt", {"graphic", "print", "принт"}),
    ],
    "hoodie": [
        ("zip_hoodie", {"zip", "zip-up", "молнии", "на молнии"}),
        ("pullover_hoodie", {"pullover"}),
    ],
    "sweater": [
        ("cardigan", {"cardigan", "кардиган"}),
        ("turtleneck", {"turtleneck", "водолаз"}),
        ("polo_knit", {"polo", "поло"}),
    ],
    "boots": [
        ("chelsea_boots", {"chelsea"}),
        ("hiking_boots", {"hiking", "mountain", "trail", "турист"}),
        ("snow_boots", {"snow", "ski", "зим", "снег"}),
    ],
    "sneakers": [
        ("running_sneakers", {"running", "runner", "бег"}),
        ("trail_sneakers", {"trail", "hiking", "outdoor"}),
        ("skate_sneakers", {"skate", "skater", "скейт"}),
    ],
    "shoes": [
        ("loafers", {"loafer", "лофер"}),
        ("derby_shoes", {"derby", "дерби"}),
        ("oxford_shoes", {"oxford", "оксфорд"}),
        ("deck_shoes", {"deck"}),
    ],
}

FEATURE_KEYWORDS = {
    "hooded": {"hood", "hooded", "капюш"},
    "waterproof": {"waterproof", "водонепрониц", "непромока"},
    "water_resistant": {"water repellent", "water-repellent", "water resistant", "water-resistant", "влаг", "водоотталк"},
    "windproof": {"windproof", "wind resistant", "ветро"},
    "insulated": {"insulated", "утепл", "thermal", "термо", "пух", "fleece-lined", "down"},
    "technical": {"technical", "shell", "softshell", "hardshell", "recco", "membrane", "мембран"},
    "breathable": {"breathable", "ventilated", "дышащ", "перфор"},
    "multi_pocket": {"cargo", "utility", "multi-pocket", "multiple pockets", "pocket", "карман"},
    "adjustable": {"adjustable", "drawstring", "toggle", "регулир", "утяжк", "кулиск"},
    "quilted": {"quilted", "стеган"},
    "lightweight": {"lightweight", "легк", "ультралегк"},
    "stretch": {"stretch", "elastic", "эласт", "стретч"},
    "zip_closure": {"zip", "zip-up", "zipper", "молнии", "молния", "на молнии"},
    "button_closure": {"button", "пугов"},
    "high_collar": {"stand collar", "high neck", "воротник-стойка", "стойка"},
    "quick_dry": {"quick dry", "quick-dry", "быстросох"},
    "packable": {"packable", "compact", "склад", "компактн"},
    "lined": {"lined", "подклад", "lining"},
    "reinforced": {"reinforced", "durable", "ripstop", "усилен", "прочный"},
    "cargo": {"cargo", "карго"},
    "storm_ready": {"storm", "шторм", "storm cuff", "storm flap", "штормов"},
}

OUTDOOR_KEYWORDS = {
    "outdoor", "trail", "hiking", "mountain", "camp", "commuter", "fishing",
    "туризм", "поход", "рыбал", "горн", "лыж", "дожд", "шторм",
}


def _contains_any(text: str, keywords: Set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def infer_material_tags(text: str) -> list[str]:
    tags = [name for name, keywords in MATERIAL_KEYWORDS.items() if _contains_any(text, keywords)]
    return sorted(tags)


def infer_fit_tags(text: str) -> list[str]:
    tags = [name for name, keywords in FIT_KEYWORDS.items() if _contains_any(text, keywords)]
    return sorted(tags)


def infer_subcategory(category: str, text: str) -> str:
    rules = SUBCATEGORY_RULES.get(category, [])
    for subcategory, keywords in rules:
        if _contains_any(text, keywords):
            return subcategory
    return category


def infer_feature_flags(text: str, category: str, material_tags: list[str], purpose_tags: list[str]) -> Dict[str, Any]:
    pocket_mentions = text.count("pocket") + text.count("карман")
    cargo = _contains_any(text, FEATURE_KEYWORDS["cargo"])
    utility_signal = (
        "utility" in text
        or "multi-pocket" in text
        or "multiple pockets" in text
        or cargo
    )
    hooded = _contains_any(text, FEATURE_KEYWORDS["hooded"])
    waterproof = _contains_any(text, FEATURE_KEYWORDS["waterproof"])
    water_resistant = waterproof or _contains_any(text, FEATURE_KEYWORDS["water_resistant"])
    windproof = _contains_any(text, FEATURE_KEYWORDS["windproof"]) or (category in {"jacket", "coat"} and ("outdoor" in purpose_tags or water_resistant))
    insulated = _contains_any(text, FEATURE_KEYWORDS["insulated"]) or any(tag in material_tags for tag in {"fleece", "down", "wool"})
    technical = _contains_any(text, FEATURE_KEYWORDS["technical"]) or "outdoor" in purpose_tags
    many_pockets = utility_signal or pocket_mentions >= 2
    breathable = _contains_any(text, FEATURE_KEYWORDS["breathable"])
    adjustable = _contains_any(text, FEATURE_KEYWORDS["adjustable"])
    quilted = _contains_any(text, FEATURE_KEYWORDS["quilted"])
    lightweight = _contains_any(text, FEATURE_KEYWORDS["lightweight"])
    stretch = _contains_any(text, FEATURE_KEYWORDS["stretch"])
    zip_closure = _contains_any(text, FEATURE_KEYWORDS["zip_closure"])
    button_closure = _contains_any(text, FEATURE_KEYWORDS["button_closure"])
    high_collar = _contains_any(text, FEATURE_KEYWORDS["high_collar"])
    quick_dry = _contains_any(text, FEATURE_KEYWORDS["quick_dry"])
    packable = _contains_any(text, FEATURE_KEYWORDS["packable"])
    lined = _contains_any(text, FEATURE_KEYWORDS["lined"])
    reinforced = _contains_any(text, FEATURE_KEYWORDS["reinforced"])
    storm_ready = _contains_any(text, FEATURE_KEYWORDS["storm_ready"]) or (
        water_resistant and windproof and category in {"jacket", "coat", "boots"}
    )

    pocket_level = "low"
    if many_pockets:
        pocket_level = "high"
    elif pocket_mentions >= 1:
        pocket_level = "medium"

    return {
        "hooded": hooded,
        "waterproof": waterproof,
        "water_resistant": water_resistant,
        "windproof": windproof,
        "insulated": insulated,
        "technical": technical,
        "many_pockets": many_pockets,
        "breathable": breathable,
        "adjustable": adjustable,
        "quilted": quilted,
        "lightweight": lightweight,
        "stretch": stretch,
        "zip_closure": zip_closure,
        "button_closure": button_closure,
        "high_collar": high_collar,
        "quick_dry": quick_dry,
        "packable": packable,
        "lined": lined,
        "reinforced": reinforced,
        "cargo": cargo,
        "storm_ready": storm_ready,
        "pocket_level": pocket_level,
    }


def infer_usecase_tags(text: str, category: str, style: str, feature_flags: Dict[str, Any], weather_tags: Optional[str]) -> list[str]:
    tags = set()

    if style == "sport":
        tags.update({"sport", "gym"})
    if style == "formal":
        tags.update({"office", "formal"})
    if category in {"jacket", "coat", "boots"}:
        tags.update({"outerwear", "city"})
    if category in {"trousers", "shorts", "boots", "sneakers"}:
        tags.add("walking")
    if _contains_any(text, OUTDOOR_KEYWORDS) or feature_flags["technical"]:
        tags.update({"outdoor", "hiking"})
    if feature_flags["water_resistant"] or (weather_tags and "rain" in weather_tags):
        tags.add("rain")
    if feature_flags["insulated"] or (weather_tags and "snow" in weather_tags):
        tags.add("winter")
    if feature_flags["breathable"] or (weather_tags and "hot" in weather_tags):
        tags.add("summer")
    office_compatible = not (
        feature_flags["technical"]
        or feature_flags["cargo"]
        or "outdoor" in tags
        or "hiking" in tags
    )
    if category in {"shirt", "trousers", "shoes", "coat"} and style in {"formal", "casual"} and office_compatible:
        tags.add("office")
    if feature_flags["many_pockets"] and (
        feature_flags["water_resistant"]
        or feature_flags["technical"]
        or _contains_any(text, {"fishing", "рыбал", "outdoor", "trail", "hiking", "utility"})
    ):
        tags.add("fishing")
    if feature_flags["many_pockets"]:
        tags.add("utility")
    if feature_flags["storm_ready"]:
        tags.update({"bad_weather", "commute"})
    if feature_flags["waterproof"] and feature_flags["hooded"]:
        tags.add("heavy_rain")
    if feature_flags["quick_dry"] or feature_flags["packable"]:
        tags.add("travel")
    if feature_flags["reinforced"]:
        tags.add("workwear")
    if category in {"sneakers", "boots"}:
        tags.add("travel")

    return sorted(tags)


def derive_item_attributes(
    *,
    title: Any,
    category: Any,
    style: Any = None,
    source: Any = None,
    weather_tags: Any = None,
    purpose_tags: Any = None,
    extra_context: Any = None,
) -> Dict[str, Any]:
    normalized_category = str(category or "").strip().lower()
    normalized_style = str(style or "").strip().lower() or "casual"
    text = _normalize_text(title, category, style, source, weather_tags, purpose_tags, extra_context)

    material_tags = infer_material_tags(text)
    fit_tags = infer_fit_tags(text)
    seed_purpose_tags = sorted(set(
        tag.strip().lower()
        for tag in str(purpose_tags or "").split(",")
        if tag.strip()
    ))

    feature_flags = infer_feature_flags(text, normalized_category, material_tags, seed_purpose_tags)
    subcategory = infer_subcategory(normalized_category, text)

    feature_tags = sorted(
        [
            name
            for name in [
                "hooded", "waterproof", "water_resistant", "windproof", "insulated",
                "technical", "many_pockets", "breathable", "adjustable",
                "quilted", "lightweight", "stretch", "zip_closure",
                "button_closure", "high_collar", "quick_dry", "packable",
                "lined", "reinforced", "cargo", "storm_ready",
            ]
            if feature_flags.get(name)
        ]
    )

    usecase_tags = sorted(set(seed_purpose_tags + infer_usecase_tags(
        text,
        normalized_category,
        normalized_style,
        feature_flags,
        str(weather_tags or ""),
    )))

    return {
        "subcategory": subcategory,
        "material_tags": ",".join(material_tags),
        "fit_tags": ",".join(fit_tags),
        "feature_tags": ",".join(feature_tags),
        "usecase_tags": ",".join(usecase_tags),
        "hooded": bool(feature_flags["hooded"]),
        "waterproof": bool(feature_flags["waterproof"]),
        "windproof": bool(feature_flags["windproof"]),
        "insulated": bool(feature_flags["insulated"]),
        "technical": bool(feature_flags["technical"]),
        "many_pockets": bool(feature_flags["many_pockets"]),
        "pocket_level": feature_flags["pocket_level"],
    }
