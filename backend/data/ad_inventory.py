"""
Synthetic ad inventory.

Generates 80 ads across 8 categories with duration options, creative quality,
seasonal affinity, demographic targeting, priority, and softened version flags.
"""

import random
from pathlib import Path
from typing import Optional

from ..state import AdCandidate, Season
from .constants import AD_CATEGORIES, AGE_GROUPS, ADVERTISERS

DEFAULT_SEED = 42

# Duration distribution per category. Values are (duration, weight) pairs.
DURATION_WEIGHTS: dict[str, list[tuple[int, float]]] = {
    "tech":    [(15, 0.25), (30, 0.45), (45, 0.15), (60, 0.15)],
    "food":    [(15, 0.35), (30, 0.50), (45, 0.10), (60, 0.05)],
    "auto":    [(15, 0.10), (30, 0.30), (45, 0.25), (60, 0.35)],
    "fashion": [(15, 0.30), (30, 0.50), (45, 0.15), (60, 0.05)],
    "finance": [(15, 0.20), (30, 0.40), (45, 0.20), (60, 0.20)],
    "travel":  [(15, 0.15), (30, 0.40), (45, 0.25), (60, 0.20)],
    "health":  [(15, 0.30), (30, 0.50), (45, 0.15), (60, 0.05)],
    "gaming":  [(15, 0.30), (30, 0.45), (45, 0.15), (60, 0.10)],
}

# Age group affinities per category.
DEMOGRAPHIC_TARGETING: dict[str, list[str]] = {
    "tech":    ["13-17", "18-24", "25-34", "35-44"],
    "food":    ["18-24", "25-34", "35-44", "45-54"],
    "auto":    ["25-34", "35-44", "45-54", "55-64"],
    "fashion": ["13-17", "18-24", "25-34", "35-44"],
    "finance": ["25-34", "35-44", "45-54", "55-64", "65+"],
    "travel":  ["25-34", "35-44", "45-54", "55-64"],
    "health":  ["35-44", "45-54", "55-64", "65+"],
    "gaming":  ["13-17", "18-24", "25-34"],
}

# Seasonal affinities per category. Base values, adjusted per ad.
BASE_SEASONAL: dict[str, dict[str, float]] = {
    "tech":    {"Spring": 0.10, "Summer": 0.10, "Fall": 0.20, "Winter": 0.35},
    "food":    {"Spring": 0.20, "Summer": 0.30, "Fall": 0.25, "Winter": 0.20},
    "auto":    {"Spring": 0.30, "Summer": 0.20, "Fall": 0.15, "Winter": 0.10},
    "fashion": {"Spring": 0.30, "Summer": 0.25, "Fall": 0.30, "Winter": 0.20},
    "finance": {"Spring": 0.15, "Summer": 0.10, "Fall": 0.15, "Winter": 0.25},
    "travel":  {"Spring": 0.20, "Summer": 0.40, "Fall": 0.15, "Winter": 0.15},
    "health":  {"Spring": 0.25, "Summer": 0.25, "Fall": 0.15, "Winter": 0.20},
    "gaming":  {"Spring": 0.15, "Summer": 0.30, "Fall": 0.20, "Winter": 0.30},
}

CREATIVE_TYPES = ["video", "video", "video", "overlay", "banner"]


def _seasonal_affinity(
    category: str, rng: random.Random
) -> dict[str, float]:
    """Add per-ad noise to the category baseline seasonal affinity."""
    base = BASE_SEASONAL.get(category, {"Spring": 0.25, "Summer": 0.25, "Fall": 0.25, "Winter": 0.25})
    result: dict[str, float] = {}
    for season in ["Spring", "Summer", "Fall", "Winter"]:
        noise = rng.gauss(0, 0.05)
        result[season] = round(max(0.0, min(1.0, base[season] + noise)), 3)
    return result


def _target_demographics(category: str, rng: random.Random) -> list[str]:
    """Sample 2-4 target age groups from category defaults, with small chance of including others."""
    base = DEMOGRAPHIC_TARGETING.get(category, AGE_GROUPS)
    extra = [g for g in AGE_GROUPS if g not in base]
    # Small chance to include one non-primary group.
    pool = base[:]
    if extra and rng.random() < 0.2:
        pool.append(rng.choice(extra))
    num = rng.randint(2, min(4, len(pool)))
    return rng.sample(pool, k=num)


def generate_ad_inventory(
    count: int = 200, seed: Optional[int] = DEFAULT_SEED
) -> list[AdCandidate]:
    rng = random.Random(seed)
    ads: list[AdCandidate] = []
    ads_per_category = count // len(AD_CATEGORIES)
    remainder = count % len(AD_CATEGORIES)
    ad_id = 1
    for i, category in enumerate(AD_CATEGORIES):
        num_ads = ads_per_category + (1 if i < remainder else 0)
        advertiser_pool = ADVERTISERS.get(category, ["Brand"])
        for _ in range(num_ads):
            advertiser = rng.choice(advertiser_pool)
            durations, dur_weights = zip(*DURATION_WEIGHTS.get(
                category, [(15, 0.25), (30, 0.50), (45, 0.15), (60, 0.10)]
            ))
            duration = rng.choices(list(durations), weights=list(dur_weights), k=1)[0]
            priority = round(max(0.1, min(0.95, rng.gauss(0.55, 0.20))), 3)
            seasonal = _seasonal_affinity(category, rng)
            demographics = _target_demographics(category, rng)
            creative_type = rng.choice(CREATIVE_TYPES)
            # Longer ads are more likely to have a softened version.
            has_softened = duration >= 30 or rng.random() < 0.6
            ads.append(
                AdCandidate(
                    id=f"ad_{ad_id:03d}",
                    category=category,
                    advertiser=advertiser,
                    duration_seconds=duration,
                    priority=priority,
                    seasonal_affinity=seasonal,
                    target_demographics=demographics,
                    creative_type=creative_type,
                    has_softened_version=has_softened,
                )
            )
            ad_id += 1
    return ads


def load_or_generate_ads(
    cache_path: Optional[str] = None,
    count: int = 200,
    seed: Optional[int] = DEFAULT_SEED,
) -> list[AdCandidate]:
    import json

    if cache_path is not None:
        p = Path(cache_path)
        if p.exists():
            try:
                raw = json.loads(p.read_text())
                return [AdCandidate.model_validate(ad) for ad in raw]
            except Exception as e:
                print(f"Warning: could not load ad cache from {cache_path}: {e}. Regenerating.")

    ads = generate_ad_inventory(count=count, seed=seed)

    if cache_path is not None:
        try:
            p = Path(cache_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps([ad.model_dump() for ad in ads], indent=2))
        except Exception as e:
            print(f"Warning: could not save ad cache to {cache_path}: {e}")

    return ads


if __name__ == "__main__":
    ads = generate_ad_inventory(count=16, seed=42)
    for ad in ads:
        print(
            f"  {ad.id} | {ad.category:<8} | {ad.advertiser:<16} | "
            f"{ad.duration_seconds}s | priority={ad.priority:.2f} | "
            f"softened={ad.has_softened_version}"
        )
