import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from parsers.run_all import collect_products_from_sources, save_products


PROFILE_RULES = {
    "bad_weather": lambda item: bool(item.get("weather_wind")) and bool(item.get("weather_snow")),
    "wet_weather": lambda item: bool(item.get("weather_rain")) and bool(item.get("weather_wind")),
    "hot_weather": lambda item: bool(item.get("weather_heat")) and bool(item.get("weather_wind")),
    "winter_weather": lambda item: bool(item.get("weather_snow")),
    "summer_weather": lambda item: bool(item.get("weather_heat")),
    "windy_weather": lambda item: bool(item.get("weather_wind")),
    "rain": lambda item: bool(item.get("weather_rain")),
    "snow": lambda item: bool(item.get("weather_snow")),
    "wind": lambda item: bool(item.get("weather_wind")),
    "heat": lambda item: bool(item.get("weather_heat")),
}


def is_weather_product(item, profile: str = "all") -> bool:
    profile = (profile or "all").strip().lower()

    if profile == "all":
        return any(rule(item) for rule in PROFILE_RULES.values())

    if profile not in PROFILE_RULES:
        raise ValueError(f"Unsupported weather profile: {profile}")

    return PROFILE_RULES[profile](item)


def get_weather_products(profile: str = "all"):
    products = collect_products_from_sources()
    return [item for item in products if is_weather_product(item, profile=profile)]


def run_weather_parsers(profile: str = "all"):
    weather_products = get_weather_products(profile=profile)
    saved, skipped = save_products(weather_products)

    print("weather profile:", profile)
    print("weather collected:", len(weather_products))
    print("saved:", saved)
    print("skipped:", skipped)


if __name__ == "__main__":
    profile = sys.argv[1] if len(sys.argv) > 1 else "all"
    run_weather_parsers(profile=profile)
