"""
GA fitness evaluation.

PURE MATH. No LLM calls. No I/O. NumPy only.
This inner loop runs millions of times during evolution.

Fitness = 60% mean user satisfaction + 40% mean advertiser revenue,
averaged across all users and sampled scenarios.

Design principles:
- No fixed base scores: gene values are the primary drivers of the [0, 1] range.
  The old base = 0.5 / 0.55 approach caused the fitness landscape to be flat
  because the floor was already close to 0.5 regardless of gene values.
- All 8 genes are active: previously delay_probability and soften_threshold
  were computed but never read. They now control independent threshold offsets
  in the decision mapping.
- ad_tolerance from UserProfile is incorporated: this field was generated but
  never used in fitness evaluation. High-tolerance users are genuinely more
  satisfied when shown an ad under the same conditions.
"""

import numpy as np

from ..state import (
    Chromosome,
    UserProfile,
    AdCandidate,
    ContentItem,
)
from ..config import config


MOOD_MODIFIER = {
    "calm":      0.10,
    "uplifting": 0.08,
    "playful":   0.05,
    "energetic": 0.00,
    "intense":  -0.10,
    "dark":     -0.15,
}

SHOW_IDX    = 0
SOFTEN_IDX  = 1
DELAY_IDX   = 2
SUPPRESS_IDX = 3


def _user_advocate_score_vectorized(
    chromosome: Chromosome,
    fatigue: np.ndarray,        # (N,) session fatigue at break point
    relevant: np.ndarray,       # (N,) bool — ad category in user interests
    time_matches: np.ndarray,   # (N,) bool — sampled ToD matches user preference
    ads_shown: np.ndarray,      # (N,) int  — ads shown so far this session
    mood_modifier: np.ndarray,  # (N,) float — content mood contribution
    intensity_high: np.ndarray, # (N,) bool — break point is high-intensity
    is_binging: np.ndarray,     # (N,) bool — user is binge-watching
    ad_tolerance: np.ndarray,   # (N,) float — user's inherent ad receptiveness
) -> np.ndarray:
    """
    Vectorized User Advocate scoring. No fixed base — genes drive the range.

    Gene roles:
      relevance_weight    — how much ad-interest match improves the score
      timing_weight       — how much time-of-day alignment improves the score
      fatigue_weight      — how heavily session fatigue penalizes the score
      session_depth_factor — how heavily late-session ad count penalizes the score

    Score range: [0, 1]. Higher = user is more receptive to seeing an ad here.
    """
    c = chromosome

    # User's base receptiveness (was previously ignored entirely)
    tolerance_base = ad_tolerance * 0.20  # [0.00, 0.20]

    # Content mood bonus: positive moods increase receptiveness
    mood_bonus = np.clip(mood_modifier + 0.15, 0.0, 0.25)  # [0.00, 0.25]

    # Relevance contribution — gene scales how much relevance matters
    # relevant ad:     up to +0.40 when relevance_weight=1
    # irrelevant ad:   up to +0.05 (small floor so it's never zero)
    relevance_contribution = c.relevance_weight * np.where(relevant, 0.40, 0.05)

    # Timing contribution — gene scales how much time-of-day alignment matters
    timing_contribution = c.timing_weight * np.where(time_matches, 0.18, 0.0)

    # Fatigue penalty — gene scales how sensitive the policy is to fatigue
    # fatigue_weight=1: high fatigue causes up to -0.55
    # fatigue_weight=0: fatigue is ignored
    fatigue_penalty = c.fatigue_weight * fatigue * 0.55

    # Session depth penalty — gene scales how much session depth hurts
    depth_penalty = c.session_depth_factor * np.where(
        ads_shown > 2, 0.28,
        np.where(ads_shown > 1, 0.14, 0.0)
    )

    # Fixed structural penalties (not gene-scaled)
    intensity_penalty = np.where(intensity_high, 0.10, 0.0)
    binge_penalty     = np.where(is_binging, 0.08 * c.session_depth_factor, 0.0)

    score = (
        tolerance_base
        + mood_bonus
        + relevance_contribution
        + timing_contribution
        - fatigue_penalty
        - depth_penalty
        - intensity_penalty
        - binge_penalty
    )
    return np.clip(score, 0.0, 1.0)


def _advertiser_advocate_score_vectorized(
    chromosome: Chromosome,
    relevant: np.ndarray,           # (N,) bool
    engagement: np.ndarray,         # (N,) float
    is_primetime: np.ndarray,       # (N,) float {0, 0.05, 0.15}
    priority: np.ndarray,           # (N,) float [0, 1]
    seasonal_affinity: np.ndarray,  # (N,) float
    demographic_match: np.ndarray,  # (N,) bool
) -> np.ndarray:
    """
    Vectorized Advertiser Advocate scoring. No fixed base — genes drive the range.

    Gene roles:
      category_boost — how much the ad-user category match boosts advertiser value

    Score range: [0, 1]. Higher = more advertiser value in showing the ad here.
    """
    c = chromosome

    # Gene-weighted category relevance (primary advertiser signal)
    # relevant:     up to +0.50 when category_boost=1
    # not relevant: up to +0.08 (still some value, just lower)
    relevance_boost = c.category_boost * np.where(relevant, 0.50, 0.08)

    # Engaged users are more valuable to advertisers (fixed, not gene-dependent)
    engagement_boost = engagement * 0.25  # [0.00, 0.25]

    # Primetime premium from Avazu data
    primetime_bonus = is_primetime         # {0, 0.05, 0.15}

    # Ad priority signal from the advertiser's own system
    priority_factor = (priority - 0.5) * 0.18  # [-0.09, +0.09]

    # Seasonal fit and demographic alignment
    seasonal_bonus = seasonal_affinity * 0.12   # [0.00, 0.12]
    demo_bonus     = np.where(demographic_match, 0.08, 0.0)

    score = (
        relevance_boost
        + engagement_boost
        + primetime_bonus
        + priority_factor
        + seasonal_bonus
        + demo_bonus
    )
    return np.clip(score, 0.0, 1.0)


def _determine_decision_vectorized(
    chromosome: Chromosome,
    combined: np.ndarray,  # (N,) combined UA+ADV score
) -> np.ndarray:
    """
    Vectorized decision mapping. All four threshold-related genes are now active.

    Gene roles:
      frequency_threshold — base bar for showing any ad [0.35, 0.65]
      soften_threshold    — width of the SOFTEN zone below show_thresh [0.06, 0.20]
      delay_probability   — width of the DELAY zone below soften_thresh [0.04, 0.14]

    Previously soften_threshold and delay_probability were in the chromosome
    but were never read in this function. They now each control an independent
    offset, giving the GA real signal to tune both thresholds separately.
    """
    show_thresh   = 0.35 + chromosome.frequency_threshold * 0.30
    soften_thresh = show_thresh   - 0.06 - chromosome.soften_threshold  * 0.14
    delay_thresh  = soften_thresh - 0.04 - chromosome.delay_probability * 0.10

    decision = np.full(combined.shape, SUPPRESS_IDX, dtype=np.int8)
    decision = np.where(combined >= delay_thresh,  DELAY_IDX,   decision)
    decision = np.where(combined >= soften_thresh, SOFTEN_IDX,  decision)
    decision = np.where(combined >= show_thresh,   SHOW_IDX,    decision)
    return decision


def _score_outcomes_vectorized(
    decisions: np.ndarray,      # (N,) int decision indices
    relevant: np.ndarray,       # (N,) bool
    fatigue: np.ndarray,        # (N,) float
    ads_shown: np.ndarray,      # (N,) int
    ad_tolerance: np.ndarray,   # (N,) float — modulates SHOW satisfaction
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert (decision, context) pairs to (satisfaction, revenue) arrays.

    Satisfaction for SHOW decisions now varies with ad_tolerance: users who
    are inherently more tolerant of ads are genuinely more satisfied when
    shown an ad under identical conditions.
    """
    sat = np.zeros(len(decisions), dtype=np.float32)
    rev = np.zeros(len(decisions), dtype=np.float32)

    show   = decisions == SHOW_IDX
    soften = decisions == SOFTEN_IDX
    delay  = decisions == DELAY_IDX
    supp   = decisions == SUPPRESS_IDX
    low_fat = fatigue < 0.5

    # Tolerance boost: high-tolerance users (>0.5) get up to +0.15 sat on SHOW
    tol_boost = np.clip(ad_tolerance - 0.5, 0.0, 0.15)

    # SHOW — base values plus tolerance boost
    sat = np.where(show & relevant & low_fat,    0.68 + tol_boost, sat)
    rev = np.where(show & relevant & low_fat,    1.00,             rev)
    sat = np.where(show & relevant & ~low_fat,   0.42 + tol_boost, sat)
    rev = np.where(show & relevant & ~low_fat,   0.85,             rev)
    sat = np.where(show & ~relevant & low_fat,   0.25 + tol_boost, sat)
    rev = np.where(show & ~relevant & low_fat,   0.65,             rev)
    sat = np.where(show & ~relevant & ~low_fat,  0.12 + tol_boost, sat)
    rev = np.where(show & ~relevant & ~low_fat,  0.45,             rev)

    # SOFTEN — shorter ad, moderate satisfaction
    sat = np.where(soften & relevant,  0.58 + tol_boost * 0.5, sat)
    sat = np.where(soften & ~relevant, 0.32 + tol_boost * 0.5, sat)
    rev = np.where(soften,             0.52,                    rev)

    # DELAY — preserves viewer, minimal revenue
    sat = np.where(delay, 0.65, sat)
    rev = np.where(delay, 0.12, rev)

    # SUPPRESS — best viewer outcome, almost no revenue
    sat = np.where(supp, 0.72, sat)
    rev = np.where(supp, 0.02, rev)

    # Session frequency penalty: showing too many ads in one session hurts satisfaction
    sat = np.where(ads_shown >= 3, np.maximum(0.0, sat - 0.15), sat)
    sat = np.where(ads_shown == 2, np.maximum(0.0, sat - 0.08), sat)

    # High fatigue penalty
    sat = np.where(fatigue > 0.70, np.maximum(0.0, sat - 0.10), sat)

    return sat, rev


def evaluate_chromosome_fitness(
    chromosome: Chromosome,
    users: list[UserProfile],
    content_items: list[ContentItem],
    ad_pool: list[AdCandidate],
    scenarios_per_user: int = 5,
    rng_seed: int = 0,
) -> float:
    """
    Evaluate fitness of a single chromosome.

    Samples `scenarios_per_user` random scenarios per user and computes the
    weighted average of satisfaction and revenue.

    PURE MATH. Called millions of times by the GA inner loop.
    """
    rng = np.random.default_rng(rng_seed)
    cfg = config
    fa_cfg = cfg.fatigue

    N = len(users) * scenarios_per_user
    if N == 0 or not ad_pool or not content_items:
        return 0.0

    # Build scenario arrays
    user_indices = np.tile(np.arange(len(users)), scenarios_per_user)

    ad_indices = rng.integers(0, len(ad_pool), size=N)
    ads_shown  = rng.integers(0, 5, size=N).astype(np.float32)

    # Extract user features
    fatigue_arr      = np.array([users[i].fatigue_level    for i in user_indices], dtype=np.float32)
    engagement_arr   = np.array([users[i].engagement_score for i in user_indices], dtype=np.float32)
    ad_tolerance_arr = np.array([users[i].ad_tolerance     for i in user_indices], dtype=np.float32)
    preferred_tod    = [users[i].preferred_watch_time.value for i in user_indices]
    interests_list   = [users[i].interests                  for i in user_indices]
    age_groups       = [users[i].age_group                  for i in user_indices]
    binge_tendency   = np.array([users[i].binge_tendency    for i in user_indices], dtype=np.float32)

    # Sample time of day for each scenario
    tod_options = ["morning", "afternoon", "evening", "latenight"]
    tod_indices = rng.integers(0, 4, size=N)
    sampled_tod = [tod_options[i] for i in tod_indices]

    # Extract ad features
    ad_categories   = [ad_pool[i].category              for i in ad_indices]
    ad_priorities   = np.array([ad_pool[i].priority     for i in ad_indices], dtype=np.float32)
    ad_target_demos = [ad_pool[i].target_demographics   for i in ad_indices]

    # Season for seasonal affinity lookup
    season_options    = ["Spring", "Summer", "Fall", "Winter"]
    season_indices    = rng.integers(0, 4, size=N)
    sampled_seasons   = [season_options[i] for i in season_indices]
    seasonal_affinity = np.array(
        [ad_pool[ad_indices[i]].seasonal_affinity.get(sampled_seasons[i], 0.0) for i in range(N)],
        dtype=np.float32,
    )

    # Relevant = ad category in user interests
    relevant     = np.array([ad_categories[i] in interests_list[i] for i in range(N)], dtype=bool)
    time_matches = np.array([sampled_tod[i] == preferred_tod[i]    for i in range(N)], dtype=bool)

    # Primetime boost from Avazu data
    primetime_map = {"morning": 0.0, "afternoon": 0.05, "evening": 0.15, "latenight": 0.15}
    is_primetime  = np.array([primetime_map[t] for t in sampled_tod], dtype=np.float32)

    # Demographic match
    demographic_match = np.array(
        [age_groups[i] in ad_target_demos[i] for i in range(N)], dtype=bool
    )

    # Sample content mood for each scenario
    mood_values_list    = list(MOOD_MODIFIER.keys())
    mood_sample_indices = rng.integers(0, len(mood_values_list), size=N)
    mood_modifier       = np.array(
        [MOOD_MODIFIER[mood_values_list[j]] for j in mood_sample_indices], dtype=np.float32
    )

    # ~30% of break points are high-intensity
    intensity_high = rng.random(N) > 0.7
    is_binging     = binge_tendency > cfg.simulation.binge_tendency_threshold

    # Session fatigue: base fatigue + accumulation from ads already shown
    session_fatigue = np.clip(
        fatigue_arr + ads_shown * fa_cfg.show_increment,
        0.0, 1.0
    ).astype(np.float32)

    force_suppress = session_fatigue > fa_cfg.force_suppress_threshold

    ua_scores = _user_advocate_score_vectorized(
        chromosome=chromosome,
        fatigue=session_fatigue,
        relevant=relevant,
        time_matches=time_matches,
        ads_shown=ads_shown.astype(int),
        mood_modifier=mood_modifier,
        intensity_high=intensity_high,
        is_binging=is_binging,
        ad_tolerance=ad_tolerance_arr,
    )

    adv_scores = _advertiser_advocate_score_vectorized(
        chromosome=chromosome,
        relevant=relevant,
        engagement=engagement_arr,
        is_primetime=is_primetime,
        priority=ad_priorities,
        seasonal_affinity=seasonal_affinity,
        demographic_match=demographic_match,
    )

    combined = ua_scores * cfg.agents.user_weight + adv_scores * cfg.agents.advertiser_weight
    combined = np.clip(combined, 0.0, 1.0)

    decisions = _determine_decision_vectorized(chromosome, combined)
    decisions = np.where(force_suppress, SUPPRESS_IDX, decisions)

    sat, rev = _score_outcomes_vectorized(
        decisions, relevant, session_fatigue, ads_shown.astype(int), ad_tolerance_arr
    )

    fitness = (
        cfg.ga.fitness_user_weight    * float(np.mean(sat))
        + cfg.ga.fitness_revenue_weight * float(np.mean(rev))
    )
    return float(np.clip(fitness, 0.0, 1.0))


def evaluate_population_fitness(
    population: list[Chromosome],
    users: list[UserProfile],
    content_items: list[ContentItem],
    ad_pool: list[AdCandidate],
    scenarios_per_user: int = 5,
    rng_seed: int = 0,
) -> list[float]:
    """
    Evaluate fitness for every chromosome in the population.

    Returns a list of fitness scores in the same order as population.
    """
    return [
        evaluate_chromosome_fitness(
            chrom, users, content_items, ad_pool,
            scenarios_per_user=scenarios_per_user,
            rng_seed=rng_seed + i,
        )
        for i, chrom in enumerate(population)
    ]
