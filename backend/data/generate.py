"""
Synthetic user profile generator.

Generates globally diverse users with age-weighted demographics, behavioral
attributes, and country-based names. Grounded in MovieLens genre distributions
where available.
"""

import random
from pathlib import Path
from typing import Optional

from ..state import TimeOfDay, UserProfile
from .constants import (
    AD_CATEGORIES,
    AGE_GROUPS,
    AGE_GROUP_WEIGHTS,
    GENRES,
    PROFESSIONS,
    TIME_OF_DAY_VALUES,
    COUNTRIES,
    COUNTRY_WEIGHTS,
    COUNTRY_NAME_POOLS,
)
from .grounding import get_grounded_engagement_stats, get_content_preferences_from_movielens

# Seed for reproducibility. Change to None for truly random generation.
DEFAULT_SEED = 42


def _age_group_to_interests(age_group: str, rng: random.Random) -> list[str]:
    """
    Map age group to plausible ad interest distribution.

    13-17: heavy gaming/tech. 18-24: tech/gaming. Older: health/finance.
    Food and travel are universal.
    """
    weights_by_age: dict[str, list[float]] = {
        "13-17": [0.20, 0.08, 0.02, 0.18, 0.02, 0.08, 0.04, 0.38],  # gaming/tech/fashion dominant
        "18-24": [0.25, 0.10, 0.05, 0.15, 0.05, 0.10, 0.05, 0.25],
        "25-34": [0.20, 0.12, 0.10, 0.12, 0.10, 0.14, 0.08, 0.14],
        "35-44": [0.15, 0.14, 0.15, 0.10, 0.14, 0.14, 0.12, 0.06],
        "45-54": [0.10, 0.14, 0.16, 0.08, 0.18, 0.14, 0.16, 0.04],
        "55-64": [0.07, 0.14, 0.12, 0.06, 0.20, 0.16, 0.22, 0.03],
        "65+":   [0.05, 0.14, 0.08, 0.05, 0.20, 0.16, 0.30, 0.02],
    }
    weights = weights_by_age.get(age_group, [1.0 / 8] * 8)
    num_interests = rng.randint(2, 4)
    chosen = rng.choices(AD_CATEGORIES, weights=weights, k=num_interests)
    # Remove duplicates while preserving order.
    seen: set[str] = set()
    result: list[str] = []
    for cat in chosen:
        if cat not in seen:
            seen.add(cat)
            result.append(cat)
    # Guarantee at least 2 interests.
    while len(result) < 2:
        candidate = rng.choice(AD_CATEGORIES)
        if candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def _age_group_to_ad_tolerance(age_group: str, rng: random.Random) -> float:
    """
    Teens have moderate-to-low tolerance (find ads annoying).
    Older users tend toward lower tolerance as well.
    """
    base_by_age: dict[str, float] = {
        "13-17": 0.40,
        "18-24": 0.55,
        "25-34": 0.50,
        "35-44": 0.45,
        "45-54": 0.40,
        "55-64": 0.38,
        "65+":   0.35,
    }
    base = base_by_age.get(age_group, 0.45)
    noise = rng.gauss(0, 0.12)
    return max(0.05, min(0.95, base + noise))


def _preferred_watch_time(age_group: str, rng: random.Random) -> TimeOfDay:
    """
    Evening is peak time universally. Latenight skews younger/teens.
    """
    weights_by_age: dict[str, list[float]] = {
        "13-17": [0.05, 0.20, 0.38, 0.37],   # teens: evening/latenight after school
        "18-24": [0.08, 0.15, 0.40, 0.37],
        "25-34": [0.10, 0.15, 0.50, 0.25],
        "35-44": [0.12, 0.18, 0.55, 0.15],
        "45-54": [0.15, 0.20, 0.55, 0.10],
        "55-64": [0.18, 0.25, 0.52, 0.05],
        "65+":   [0.20, 0.30, 0.47, 0.03],
    }
    weights = weights_by_age.get(age_group, [0.15, 0.20, 0.50, 0.15])
    choice = rng.choices(TIME_OF_DAY_VALUES, weights=weights, k=1)[0]
    return TimeOfDay(choice)


def _generate_watch_history(
    genres: list[str], content_preferences: list[str], rng: random.Random
) -> list[str]:
    """Generate a plausible list of previously watched content IDs."""
    num_items = rng.randint(5, 25)
    return [f"content_{rng.randint(1, 100)}" for _ in range(num_items)]


def generate_user(user_id: int, rng: random.Random) -> UserProfile:
    """Generate a single synthetic user profile with global diversity."""
    age_group = rng.choices(AGE_GROUPS, weights=AGE_GROUP_WEIGHTS, k=1)[0]
    profession = rng.choice(PROFESSIONS)
    # Teens are overwhelmingly students.
    if age_group == "13-17":
        profession = "Student"
    interests = _age_group_to_interests(age_group, rng)
    preferred_watch_time = _preferred_watch_time(age_group, rng)
    ad_tolerance = _age_group_to_ad_tolerance(age_group, rng)
    fatigue_level = max(0.0, min(1.0, rng.gauss(0.25, 0.15)))
    eng_mean, eng_std = get_grounded_engagement_stats()
    engagement_score = max(0.1, min(0.95, rng.gauss(eng_mean, eng_std)))
    session_count = rng.randint(1, 300)
    binge_tendency = max(0.0, min(1.0, rng.gauss(0.45, 0.20)))
    num_prefs = rng.randint(2, 4)
    content_preferences = get_content_preferences_from_movielens(rng, num_prefs)
    watch_history = _generate_watch_history(GENRES, content_preferences, rng)

    # Pick a country and generate a culturally appropriate name.
    country = rng.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
    name_pool = COUNTRY_NAME_POOLS[country]
    first = rng.choice(name_pool["first"])
    last = rng.choice(name_pool["last"])
    name = f"{first} {last} ({country})"

    return UserProfile(
        id=user_id,
        name=name,
        age_group=age_group,
        country=country,
        profession=profession,
        interests=interests,
        preferred_watch_time=preferred_watch_time,
        ad_tolerance=ad_tolerance,
        fatigue_level=fatigue_level,
        engagement_score=engagement_score,
        session_count=session_count,
        watch_history=watch_history,
        binge_tendency=binge_tendency,
        content_preferences=content_preferences,
    )


def generate_users(
    count: int = 400, seed: Optional[int] = DEFAULT_SEED
) -> list[UserProfile]:
    """
    Generate a pool of synthetic users.

    Args:
        count: Number of users to generate.
        seed: Random seed for reproducibility. Pass None for random output.
    """
    rng = random.Random(seed)
    users = [generate_user(i + 1, rng) for i in range(count)]
    return users


def load_or_generate_users(
    cache_path: Optional[str] = None,
    count: int = 400,
    seed: Optional[int] = DEFAULT_SEED,
) -> list[UserProfile]:
    """
    Load users from a JSON cache file, or generate and save them.

    If cache_path is None, always generates fresh.
    """
    import json

    if cache_path is not None:
        p = Path(cache_path)
        if p.exists():
            try:
                raw = json.loads(p.read_text())
                users = [UserProfile.model_validate(u) for u in raw]
                return users
            except Exception as e:
                print(f"Warning: could not load user cache from {cache_path}: {e}. Regenerating.")

    users = generate_users(count=count, seed=seed)

    if cache_path is not None:
        try:
            p = Path(cache_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps([u.model_dump() for u in users], indent=2)
            )
        except Exception as e:
            print(f"Warning: could not save user cache to {cache_path}: {e}")

    return users


if __name__ == "__main__":
    users = generate_users(count=10, seed=42)
    for u in users:
        print(f"  {u.id:3d} | {u.name:<35} | {u.age_group} | {u.country:<12} | {u.interests} | fatigue={u.fatigue_level:.2f}")
