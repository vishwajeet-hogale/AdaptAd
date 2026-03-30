"""
Synthetic content library.

Generates 150 content items spanning English, Korean, Japanese, Spanish, Hindi,
Turkish, French, and Portuguese content. Includes series episodes and movies.
"""

import random
from pathlib import Path
from typing import Optional

from ..state import ContentItem, ContentMood
from .constants import GENRES, COUNTRY_LANGUAGE_MAP

DEFAULT_SEED = 42

# Mood per genre. Multiple moods listed with relative weights.
GENRE_MOODS: dict[str, list[tuple[str, float]]] = {
    "Action":      [("energetic", 0.50), ("intense", 0.35), ("uplifting", 0.15)],
    "Comedy":      [("playful", 0.55), ("uplifting", 0.35), ("calm", 0.10)],
    "Drama":       [("intense", 0.35), ("dark", 0.30), ("calm", 0.25), ("uplifting", 0.10)],
    "Sci-Fi":      [("energetic", 0.35), ("intense", 0.35), ("calm", 0.20), ("dark", 0.10)],
    "Horror":      [("dark", 0.60), ("intense", 0.35), ("calm", 0.05)],
    "Documentary": [("calm", 0.55), ("uplifting", 0.25), ("energetic", 0.20)],
    "Romance":     [("uplifting", 0.45), ("calm", 0.35), ("playful", 0.20)],
    "Thriller":    [("intense", 0.45), ("dark", 0.35), ("energetic", 0.20)],
    "Animation":   [("playful", 0.45), ("uplifting", 0.35), ("energetic", 0.20)],
    "Fantasy":     [("uplifting", 0.35), ("energetic", 0.30), ("intense", 0.20), ("dark", 0.15)],
}

# Typical duration ranges by content type.
MOVIE_DURATION_RANGE = (80, 150)
EPISODE_DURATION_RANGE = (22, 60)

# ---- Series titles with language metadata ----
# (title, language, genre)
SERIES_CATALOG: list[tuple[str, str, str]] = [
    # English originals
    ("Darkwave Chronicles",  "English", "Thriller"),
    ("The Signal",           "English", "Sci-Fi"),
    ("Offworld",             "English", "Sci-Fi"),
    ("Pulse City",           "English", "Drama"),
    ("Ironhaven",            "English", "Action"),
    ("Velvet Underground",   "English", "Drama"),
    ("The Reckoning",        "English", "Thriller"),
    ("Starfall",             "English", "Fantasy"),
    ("Night Protocol",       "English", "Thriller"),
    ("Hollow Earth",         "English", "Sci-Fi"),
    # Korean (K-drama / Korean thriller)
    ("Halo of Seoul",        "Korean",  "Drama"),
    ("Midnight Confession",  "Korean",  "Romance"),
    ("Kingdom of Shadows",   "Korean",  "Thriller"),
    # Japanese (anime / live action)
    ("Midnight Sakura",      "Japanese", "Romance"),
    ("Steel Horizon",        "Japanese", "Action"),
    # Spanish / Latin American
    ("La Frontera",          "Spanish",  "Drama"),
    ("Casa Infinita",        "Spanish",  "Comedy"),
    # Hindi / Indian
    ("Mumbai Monsoon",       "Hindi",    "Drama"),
    ("Dilli Nights",         "Hindi",    "Thriller"),
    # Turkish
    ("Bosphorus Dreams",     "Turkish",  "Romance"),
    # French
    ("Le Dernier Signal",    "French",   "Thriller"),
    # Portuguese / Brazilian
    ("Além do Rio",          "Portuguese", "Drama"),
]

# ---- Movie titles with language metadata ----
# (title, language)
MOVIE_CATALOG: list[tuple[str, str]] = [
    # English
    ("Edge of Tomorrow",     "English"),
    ("Lantern Light",        "English"),
    ("The Forgotten Shore",  "English"),
    ("Cascade",              "English"),
    ("Iron Meridian",        "English"),
    ("The Blue Divide",      "English"),
    ("Shadow Protocol",      "English"),
    ("Earthbound",           "English"),
    ("Lone Circuit",         "English"),
    ("The Pale Hour",        "English"),
    ("Fracture Point",       "English"),
    ("Neon Descent",         "English"),
    ("The Crossing",         "English"),
    ("Amber Dawn",           "English"),
    ("Gravity Wells",        "English"),
    ("Mirror Stage",         "English"),
    ("Quantum Breach",       "English"),
    ("The Long Winter",      "English"),
    ("Ember Falls",          "English"),
    ("Hollow Signal",        "English"),
    ("Deep Fracture",        "English"),
    ("The Outer Rim",        "English"),
    ("Shoreline",            "English"),
    ("Beneath the Static",   "English"),
    ("Fault Lines",          "English"),
    ("The Quiet Storm",      "English"),
    ("Override",             "English"),
    ("Solar Drift",          "English"),
    ("Threshold",            "English"),
    ("The Vanishing Point",  "English"),
    ("Blind Orbit",          "English"),
    ("Cold Harbor",          "English"),
    ("Drift Code",           "English"),
    ("Sunken Archive",       "English"),
    ("Terminal Bloom",       "English"),
    ("Static Fields",        "English"),
    ("Warped Horizon",       "English"),
    ("Night Current",        "English"),
    ("Parallel Rift",        "English"),
    ("Void Transit",         "English"),
    ("Signal Lost",          "English"),
    ("Crossfire Protocol",   "English"),
    ("Dead Orbit",           "English"),
    ("Fractured Light",      "English"),
    ("Midnight Axis",        "English"),
    ("Residual Echo",        "English"),
    ("The Burning Grid",     "English"),
    ("Ironclad",             "English"),
    ("Pattern Break",        "English"),
    ("Zero Hour",            "English"),
    # Korean films
    ("Han River Blues",      "Korean"),
    ("The Last Ferry",       "Korean"),
    ("Seoul Burning",        "Korean"),
    ("Under the Cherry Sky", "Korean"),
    ("Echoes of Incheon",    "Korean"),
    # Japanese films
    ("Sakura Protocol",      "Japanese"),
    ("Tokyo Undertow",       "Japanese"),
    ("The Kyoto Silence",    "Japanese"),
    ("Neon Samurai",         "Japanese"),
    ("Autumn in Osaka",      "Japanese"),
    # Hindi / Indian films
    ("Zindagi Ki Daud",      "Hindi"),
    ("Raat Ka Safar",        "Hindi"),
    ("Mumbai Express",       "Hindi"),
    ("Dil Ka Darya",         "Hindi"),
    ("Ek Pal Ki Zindagi",    "Hindi"),
    # Spanish / Latin American films
    ("Tierra de Nadie",      "Spanish"),
    ("El Ultimo Tren",       "Spanish"),
    ("Cielo Rojo",           "Spanish"),
    ("La Sombra del Mar",    "Spanish"),
    ("Volver al Sur",        "Spanish"),
    # French films
    ("La Nuit Blanche",      "French"),
    ("Le Pont de l'Alma",    "French"),
    ("Sans Retour",          "French"),
    ("L'Heure Bleue",        "French"),
    # German films
    ("Die Letzte Welle",     "German"),
    ("Nachtstrom",           "German"),
    ("Der Unsichtbare",      "German"),
    # Turkish films
    ("Istanbul Noir",        "Turkish"),
    ("Son Gemi",             "Turkish"),
    ("Gecenin Sonu",         "Turkish"),
    # Portuguese / Brazilian films
    ("A Última Margem",      "Portuguese"),
    ("Rio Silencioso",       "Portuguese"),
    ("Além da Tempestade",   "Portuguese"),
    # Mandarin Chinese films
    ("The Dragon's Breath",  "Mandarin"),
    ("Midnight in Shanghai", "Mandarin"),
    ("Silent Pearl",         "Mandarin"),
    # More English films
    ("Afterglow",            "English"),
    ("The Pale Circuit",     "English"),
    ("Stormwatch",           "English"),
    ("Redline",              "English"),
    ("The Broken Meridian",  "English"),
    ("Dusk Signal",          "English"),
    ("Cascade Protocol",     "English"),
    ("Beyond the Grid",      "English"),
    ("Shadowline",           "English"),
    ("The Cold Frequency",   "English"),
    ("Lost Harbor",          "English"),
    ("Iron Current",         "English"),
    ("The Open Wire",        "English"),
    ("Drift Point",          "English"),
    ("Signal Bloom",         "English"),
    ("Outer Cascade",        "English"),
    ("Warpfall",             "English"),
    ("The Iron Drift",       "English"),
    ("Pale Horizon",         "English"),
    ("Night Fracture",       "English"),
    ("The Blind Signal",     "English"),
    ("Coldfall",             "English"),
    ("Static Orbit",         "English"),
    ("The Last Frequency",   "English"),
    ("Deep Current",         "English"),
    ("Void Signal",          "English"),
    ("The Burning Wire",     "English"),
    ("Ironfall",             "English"),
    ("Pattern Signal",       "English"),
    ("Zero Orbit",           "English"),
    # More Korean films
    ("Han River Rain",       "Korean"),
    ("Seoul Protocol",       "Korean"),
    ("The Last Han",         "Korean"),
    ("Cherry Blossom Noir",  "Korean"),
    # More Japanese films
    ("Kyoto Rain",           "Japanese"),
    ("Neon Dusk Tokyo",      "Japanese"),
    ("The Quiet Mountain",   "Japanese"),
    # More Hindi / Indian films
    ("Aasman Ka Raaz",       "Hindi"),
    ("Lambi Raahein",        "Hindi"),
    ("Dil Aur Dhadkan",      "Hindi"),
    # More Spanish / Latin films
    ("La Ultima Ola",        "Spanish"),
    ("El Mar Silencioso",    "Spanish"),
    ("Tierra Oscura",        "Spanish"),
    # More French films
    ("Le Silence du Lac",    "French"),
    ("Nuit Froide",          "French"),
    # More Turkish films
    ("Bogazici Gece",        "Turkish"),
    ("Son Isik",             "Turkish"),
    # More Portuguese / Brazilian
    ("Noite do Rio",         "Portuguese"),
    ("A Maré",               "Portuguese"),
    # More Mandarin
    ("The Jade Coast",       "Mandarin"),
    ("Night over Beijing",   "Mandarin"),
    # More German
    ("Der Stille Wald",      "German"),
    ("Morgendammerung",      "German"),
]


def _generate_intensity_curve(
    duration: int, mood: ContentMood, rng: random.Random
) -> list[float]:
    """
    Generate a per-minute intensity curve.

    Base intensity is shaped by mood. High-intensity genres have more peaks.
    """
    mood_baseline: dict[str, float] = {
        "calm": 0.30,
        "uplifting": 0.45,
        "playful": 0.40,
        "energetic": 0.55,
        "intense": 0.65,
        "dark": 0.60,
    }
    baseline = mood_baseline.get(mood.value, 0.5)
    curve = []
    current = baseline
    for minute in range(duration):
        delta = rng.gauss(0, 0.08)
        current = max(0.05, min(0.95, current + delta))
        current = current * 0.85 + baseline * 0.15
        if minute > duration * 0.80:
            current = min(0.95, current + 0.04)
        curve.append(round(current, 3))
    return curve


def _natural_break_points(
    duration: int, is_series: bool, intensity_curve: list[float], rng: random.Random
) -> list[int]:
    """
    Place break points at low-intensity minutes, avoiding first/last 5 min.

    Episodes (22-60 min) get 2-4 breaks.
    Movies (80+ min) get 4-7 breaks.
    """
    buffer = 5
    start = buffer
    end = duration - buffer
    if end <= start:
        return []
    eligible = list(range(start, end + 1))
    if not eligible:
        return []
    weighted = [(m, 1.0 / (intensity_curve[m] + 0.1)) for m in eligible]
    weights = [w for _, w in weighted]
    minutes = [m for m, _ in weighted]
    if is_series:
        num_breaks = rng.randint(2, min(4, len(eligible)))
    else:
        num_breaks = rng.randint(4, min(7, len(eligible)))
    num_breaks = min(num_breaks, len(eligible))
    chosen = rng.choices(minutes, weights=weights, k=num_breaks * 3)
    seen: set[int] = set()
    result: list[int] = []
    for m in sorted(chosen):
        if m not in seen:
            seen.add(m)
            result.append(m)
        if len(result) >= num_breaks:
            break
    return sorted(result)


def generate_content_library(
    count: int = 300, seed: Optional[int] = DEFAULT_SEED
) -> list[ContentItem]:
    rng = random.Random(seed)
    items: list[ContentItem] = []
    item_id = 1

    # Series episodes: 3 episodes per series entry in SERIES_CATALOG.
    for series_title, language, series_genre in SERIES_CATALOG:
        mood_choices = GENRE_MOODS.get(series_genre, GENRE_MOODS["Drama"])
        moods, mood_weights = zip(*mood_choices)
        series_season = 1
        for ep_num in range(1, 4):
            mood = ContentMood(rng.choices(moods, weights=mood_weights, k=1)[0])
            duration = rng.randint(*EPISODE_DURATION_RANGE)
            intensity = _generate_intensity_curve(duration, mood, rng)
            breaks = _natural_break_points(duration, True, intensity, rng)
            items.append(
                ContentItem(
                    id=item_id,
                    title=f"{series_title} S{series_season}E{ep_num}",
                    genre=series_genre,
                    language=language,
                    duration_minutes=duration,
                    mood=mood,
                    episode_number=ep_num,
                    season_number=series_season,
                    is_series=True,
                    natural_break_points=breaks,
                    intensity_curve=intensity,
                )
            )
            item_id += 1

    # Movies: fill remaining slots from MOVIE_CATALOG.
    remaining = count - len(items)
    movie_list = MOVIE_CATALOG[:]
    rng.shuffle(movie_list)
    for i in range(remaining):
        title, language = movie_list[i % len(movie_list)]
        if i >= len(movie_list):
            title = f"{title} II"
        genre = rng.choice(list(GENRE_MOODS.keys()))
        mood_choices = GENRE_MOODS[genre]
        moods, mood_weights = zip(*mood_choices)
        mood = ContentMood(rng.choices(moods, weights=mood_weights, k=1)[0])
        duration = rng.randint(*MOVIE_DURATION_RANGE)
        intensity = _generate_intensity_curve(duration, mood, rng)
        breaks = _natural_break_points(duration, False, intensity, rng)
        items.append(
            ContentItem(
                id=item_id,
                title=title,
                genre=genre,
                language=language,
                duration_minutes=duration,
                mood=mood,
                episode_number=None,
                season_number=None,
                is_series=False,
                natural_break_points=breaks,
                intensity_curve=intensity,
            )
        )
        item_id += 1

    return items[:count]


def pick_content_for_user(
    user, content_items: list, rng: random.Random, native_boost: float = 3.0
) -> "ContentItem":
    """
    Choose a content item biased toward the user's native language(s).

    Items in the user's native language (non-English) are weighted native_boost× higher.
    English content stays at 1.0. Foreign content the user is unlikely to prefer: 0.3×.
    """
    country = getattr(user, "country", "")
    native_langs = COUNTRY_LANGUAGE_MAP.get(country, ["English"])
    weights = []
    for item in content_items:
        if item.language in native_langs and item.language != "English":
            weights.append(native_boost)
        elif item.language == "English":
            weights.append(1.0)
        else:
            weights.append(0.3)
    return rng.choices(content_items, weights=weights, k=1)[0]


def load_or_generate_content(
    cache_path: Optional[str] = None,
    count: int = 300,
    seed: Optional[int] = DEFAULT_SEED,
) -> list[ContentItem]:
    import json

    if cache_path is not None:
        p = Path(cache_path)
        if p.exists():
            try:
                raw = json.loads(p.read_text())
                return [ContentItem.model_validate(item) for item in raw]
            except Exception as e:
                print(f"Warning: could not load content cache from {cache_path}: {e}. Regenerating.")

    items = generate_content_library(count=count, seed=seed)

    if cache_path is not None:
        try:
            p = Path(cache_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps([item.model_dump() for item in items], indent=2))
        except Exception as e:
            print(f"Warning: could not save content cache to {cache_path}: {e}")

    return items


if __name__ == "__main__":
    library = generate_content_library(count=10, seed=42)
    for item in library:
        print(
            f"  {item.id:3d} | {item.title:<45} | {item.language:<12} | {item.genre:<12} | "
            f"{item.mood.value:<10} | {item.duration_minutes}min | "
            f"breaks={item.natural_break_points}"
        )
