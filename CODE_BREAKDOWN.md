# AdaptAd — Complete Code Breakdown
### CS6170 AI Capstone | Northeastern University | Craig Roberts

This document provides a file-by-file breakdown of every source file in AdaptAd. For each file: what it is, what every function/class does, inputs/outputs, and how it connects to the rest of the system.

---

## Table of Contents

1. [Backend Foundation](#1-backend-foundation)
   - backend/config.py
   - backend/state.py
2. [Data Layer](#2-data-layer)
   - backend/data/constants.py
   - backend/data/generate.py
   - backend/data/ad_inventory.py
   - backend/data/content_library.py
   - backend/data/grounding.py
   - backend/data/pipeline.py
3. [Simulation Layer](#3-simulation-layer)
   - backend/simulation/fatigue.py
   - backend/simulation/breaks.py
   - backend/simulation/binge.py
   - backend/simulation/session.py
   - backend/simulation/engine.py
4. [Agent Layer](#4-agent-layer)
   - backend/agents/user_advocate.py
   - backend/agents/advertiser_advocate.py
   - backend/agents/negotiator.py
   - backend/agents/llm_reasoning.py
5. [Genetic Algorithm Layer](#5-genetic-algorithm-layer)
   - backend/ga/fitness.py
   - backend/ga/engine.py
   - backend/ga/storage.py
6. [LangGraph Orchestration](#6-langgraph-orchestration)
   - backend/graph/builder.py
7. [Experiment Layer](#7-experiment-layer)
   - backend/experiments/runner.py
   - backend/experiments/ablations.py
   - backend/experiments/metrics.py
   - backend/experiments/stats.py
8. [Database Layer](#8-database-layer)
   - backend/db/database.py
9. [API Layer](#9-api-layer)
   - backend/main.py
   - backend/api/routes_data.py
   - backend/api/routes_evolve.py
   - backend/api/routes_decide.py
   - backend/api/routes_simulate.py
   - backend/api/routes_ab.py
   - backend/api/routes_experiments.py
   - backend/api/websocket.py
10. [Test Suite](#10-test-suite)
    - backend/tests/test_ga.py
    - backend/tests/test_api.py
11. [Frontend Layer](#11-frontend-layer)
    - Entry Points
    - Store
    - API Client
    - WebSocket Hook
    - Components
    - Pages

---

## 1. Backend Foundation

---

### `backend/config.py`

**Purpose:** Single source of truth for every tunable parameter in the system. All other modules import from here. Changing a value here changes it everywhere.

**Pattern used:** Python dataclasses with a module-level singleton `config = Config()`. This means you import `from backend.config import config` and get the same object everywhere — no re-instantiation.

#### Classes

**`GAConfig`** — Genetic algorithm hyperparameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `population_size` | 30 | Enough diversity without excessive compute |
| `elite_ratio` | 0.20 | Top 20% survive unchanged each generation |
| `mutation_rate` | 0.15 | 15% per-gene mutation probability |
| `mutation_strength` | 0.30 | Max gene change ≈ ±0.15 (strength/2 as std) |
| `max_generations` | 50 | Convergence typically happens by gen 30 |
| `convergence_threshold` | 0.001 | Stop if improvement < 0.1% over 10 gens |
| `convergence_window` | 10 | Window for convergence check |
| `fitness_user_weight` | 0.60 | 60% weight on user satisfaction in fitness |
| `fitness_revenue_weight` | 0.40 | 40% weight on revenue |
| `stuck_restart_threshold` | 20 | Restart with fresh population after 20 stuck gens |

**`FatigueConfig`** — How fatigue accumulates and decays
| Parameter | Value | Meaning |
|-----------|-------|---------|
| `show_increment` | 0.10 | Showing a full ad increases fatigue by 10% |
| `soften_increment` | 0.05 | Softened ad increases fatigue by 5% |
| `delay_increment` | 0.02 | Delayed ad increases fatigue by 2% |
| `suppress_increment` | 0.00 | Suppressed ad has zero fatigue impact |
| `decay_per_minute` | 0.01 | Fatigue drops 1% per ad-free minute |
| `force_suppress_threshold` | 0.85 | Hard cap — all ads suppressed above this |
| `penalty_threshold` | 0.70 | Satisfaction starts being penalized above this |
| `penalty_amount` | 0.15 | Satisfaction penalty when fatigue > 0.70 |

**`AgentConfig`** — All agent scoring constants
- User Advocate: base=0.5, relevance multipliers, fatigue multiplier=1.5, timing bonus=0.3, session penalties, intensity penalty=0.12, binge penalty=0.08
- Advertiser Advocate: base=0.55, relevance multiplier=1.5, engagement multiplier=0.3, primetime evening=0.15, afternoon=0.05
- Negotiator: user_weight=0.55, advertiser_weight=0.45, base_show_threshold=0.45, show_threshold_scale=0.35, soften_offset=0.15, delay_offset=0.15

**`LLMConfig`** — LLM provider settings
- Primary: Groq (`llama-3.3-70b-versatile`), timeout 5s
- Fallback: Gemini (`gemini-2.5-flash`)
- `enabled`: can be toggled off for pure-math mode

**`SimulationConfig`** — Session simulation parameters
- `num_users=200`, `num_ads=80`, `num_content_items=100`
- `break_point_buffer_minutes=5` — no ads in first/last 5 min
- `binge_queue_threshold=2`, `binge_tendency_threshold=0.5`

**`Config`** — Top-level dataclass composing all sub-configs plus `chromosomes_dir` and `debug` flag.

---

### `backend/state.py`

**Purpose:** Defines every data model used in the system as Pydantic v2 models. Acts as the contract between all layers. If you change a model here, all layers adapt automatically because they share these types.

#### Enumerations

**`TimeOfDay`** — `morning | afternoon | evening | latenight`
Used in SessionContext and UserProfile. Drives timing bonuses and primetime calculations.

**`Season`** — `Spring | Summer | Fall | Winter`
Used in SessionContext and AdCandidate.seasonal_affinity for seasonal ad matching.

**`ContentMood`** — `calm | uplifting | playful | energetic | intense | dark`
Stored on ContentItem. Used in User Advocate scoring — dark/intense content → lower ad tolerance.

**`AdDecision`** — `SHOW | SOFTEN | DELAY | SUPPRESS`
The four possible outcomes of the negotiation. The entire system exists to decide which of these to output.

#### Core Models

**`UserProfile`**
Represents a synthetic streaming viewer. Key fields:
- `id`, `name`: identity
- `age_group`: one of 6 brackets ("18-24" through "65+")
- `interests`: list of 2–4 ad categories this user cares about
- `preferred_watch_time`: TimeOfDay enum value
- `ad_tolerance`: float [0,1] — how much advertising they accept
- `fatigue_level`: float [0,1] — base fatigue before session starts
- `engagement_score`: float [0.1, 0.95] — proxy for attention/engagement
- `binge_tendency`: float [0,1] — likelihood of watching multiple episodes
- `content_preferences`: list of genres

**`AdCandidate`**
Represents a single advertisement in the inventory. Key fields:
- `id`: unique string identifier
- `category`: one of 8 categories
- `duration_seconds`: ad length (15–60s depending on category)
- `priority`: float [0,1] — advertiser importance score
- `has_softened_version`: bool — whether a shorter version exists
- `target_demographics`: list of age groups this ad is designed for
- `seasonal_affinity`: dict mapping Season → float relevance score

**`ContentItem`**
Represents a piece of streaming content. Key fields:
- `id`, `title`, `genre`, `duration_minutes`
- `mood`: ContentMood enum
- `is_series`: bool — affects binge detection
- `intensity_curve`: list of per-minute intensity values [0,1]
- `natural_break_points`: list of minutes where breaks are appropriate (low intensity)

**`SessionContext`**
Snapshot of session state at a given moment. This is the key object that evolves throughout a session:
- `time_of_day`, `season`: environmental context
- `ads_shown_this_session`: count of ads already shown
- `current_minute`: where in the content we are
- `content`: reference to the ContentItem being watched
- `is_binging`: bool — in a binge session
- `session_fatigue_accumulator`: running fatigue total for this session

**`AdOpportunity`**
A single decision point — bundles together everything needed to make a decision:
- `user_profile`: who is watching
- `ad_candidate`: which ad is being considered
- `session_context`: snapshot of session state at this break point

**`Chromosome`**
The 8-gene policy encoded as a Pydantic model. All genes are floats in [0,1], enforced by a `@field_validator` that clamps on assignment.

| Gene | Range | Controls |
|------|-------|---------|
| `fatigue_weight` | [0,1] | How heavily fatigue penalizes UA score |
| `relevance_weight` | [0,1] | How much relevance boosts UA score |
| `timing_weight` | [0,1] | How much break-point timing matters |
| `frequency_threshold` | [0,1] | SHOW/SOFTEN/DELAY/SUPPRESS threshold boundary |
| `delay_probability` | [0,1] | Aggressiveness of delay decisions |
| `soften_threshold` | [0,1] | When to prefer softer ad version |
| `category_boost` | [0,1] | Advertiser relevance boost multiplier |
| `session_depth_factor` | [0,1] | Late-session ad penalty strength |

Methods:
- `to_vector() → list[float]`: ordered list of 8 genes for GA operations
- `from_vector(vec) → Chromosome`: construct from list, validates length
- `gene_names() → list[str]`: returns ordered list of gene name strings

**`AgentScore`**
Output of User Advocate or Advertiser Advocate:
- `agent_name`: "User Advocate" or "Advertiser Advocate"
- `score`: float [0,1]
- `reasoning`: human-readable string explaining the score
- `factors`: dict of factor_name → value for debugging

**`NegotiationResult`**
Final output of the full decision pipeline:
- `decision`: AdDecision enum value
- `user_advocate`: AgentScore from UA
- `advertiser_advocate`: AgentScore from ADV
- `combined_score`: float — weighted combination
- `reasoning`: explanation string (may be LLM-generated)
- `timestamp`, `session_id`, `user_id`, `ad_id`: logging metadata

**`GraphState`**
TypedDict used as the state container for LangGraph graphs. Contains slots for user, ad, context, chromosome, agent scores, negotiation result, and evolution engine. All LangGraph nodes read from and write to this shared state.

---

## 2. Data Layer

---

### `backend/data/constants.py`

**Purpose:** All static lookup data — category names, age groups, genre names, profession lists, advertiser names. Import this instead of hardcoding strings anywhere else.

**`AD_CATEGORIES`** — 8 strings: `["Technology", "Food & Beverage", "Travel", "Gaming", "Health & Wellness", "Fashion", "Finance", "Entertainment"]`

**`AGE_GROUPS`** — 6 brackets: `["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]`

**`AGE_GROUP_WEIGHTS`** — `[0.18, 0.25, 0.22, 0.16, 0.12, 0.07]` — US streaming demographic distribution

**`GENRES`** — 10 strings: Drama, Comedy, Action, Sci-Fi, Horror, Documentary, Romance, Thriller, Animation, Fantasy

**`PROFESSIONS`** — 20 occupation strings for generating realistic user names/context

**`ADVERTISERS`** — dict mapping each category to a list of 4–6 brand names (e.g., Gaming → ["GameStop", "Steam", "Nvidia", "Xbox"])

---

### `backend/data/generate.py`

**Purpose:** Generates 200 synthetic `UserProfile` objects with realistic, age-stratified demographics. Grounded in real dataset statistics where available.

#### Key Functions

**`_age_group_to_interests(age_group, rng) → list[str]`**
Maps an age group to a weighted distribution over ad categories. Younger users skew toward Technology and Gaming; older users skew toward Health & Wellness and Finance. Uses `rng.choices()` with per-age-group weight tables to sample 2–4 interests, then deduplicates while guaranteeing at least 2 unique interests.

**`_age_group_to_ad_tolerance(age_group, rng) → float`**
Older users have lower ad tolerance. Base values: 18-24→0.55 down to 65+→0.35. Adds Gaussian noise N(0, 0.12), clamped to [0.05, 0.95]. This simplification is explicitly documented in the docstring.

**`_preferred_watch_time(age_group, rng) → TimeOfDay`**
Evening is universal peak. Late-night skews toward 18-24. Older users shift toward morning/afternoon. Samples from weighted TimeOfDay options.

**`_generate_watch_history(genres, content_preferences, rng) → list[str]`**
Generates a list of 5–25 "content_42"-style IDs representing previously watched items. These are placeholder IDs used only for simulation narrative — the exact values do not affect scoring.

**`generate_user(user_id, rng) → UserProfile`**
Assembles a single UserProfile:
1. Samples age group using AGE_GROUP_WEIGHTS
2. Samples profession from PROFESSIONS list
3. Calls `_age_group_to_interests()` for interests
4. Calls `_preferred_watch_time()` for watch time
5. Calls `_age_group_to_ad_tolerance()` for tolerance
6. Samples fatigue from N(0.25, 0.15), clamped [0,1]
7. **Calls `get_grounded_engagement_stats()`** — gets mean/std from MovieLens data → samples engagement_score from N(0.72, 0.18)
8. Samples session_count 1–300, binge_tendency from N(0.45, 0.20)
9. **Calls `get_content_preferences_from_movielens()`** — genre preferences weighted by MovieLens genre distribution
10. Generates name from first_names × last_names list

**`generate_users(count=200, seed=42) → list[UserProfile]`**
Creates a `random.Random(seed)` instance for reproducibility and calls `generate_user()` 200 times.

**`load_or_generate_users(cache_path, count, seed) → list[UserProfile]`**
Optionally caches generated users to a JSON file. If cache exists, loads with `UserProfile.model_validate()`. Otherwise generates and saves. Used for faster startup in production scenarios.

**Connections:** Imports from `data/constants.py` and `data/grounding.py`. Output consumed by `simulation/engine.py`, `ga/fitness.py`, and all API routes via `routes_data.py`.

---

### `backend/data/ad_inventory.py`

**Purpose:** Generates 80 synthetic `AdCandidate` objects covering all 8 ad categories, with realistic durations, seasonal patterns, and demographic targeting.

#### Key Functions

**`_duration_for_category(category, rng) → int`**
Category-specific duration distributions (seconds):
- Technology: 30–60s (demo-style ads)
- Food & Beverage: 15–45s (quick impact)
- Travel: 45–60s (immersive)
- Gaming: 15–30s (fast-paced)
- Health & Wellness: 30–60s (informative)
- Fashion: 15–30s (visual)
- Finance: 30–60s (compliance-heavy)
- Entertainment: 15–45s (trailers)

**`_seasonal_affinity_for_category(category, rng) → dict`**
Returns a dict mapping each Season to a relevance float. Travel peaks in Summer, Fashion peaks in Fall, Finance peaks in Winter/Spring (tax season), Entertainment is relatively flat. Adds small Gaussian noise per season for variety.

**`_target_demographics_for_category(category, rng) → list[str]`**
Determines which age groups each category targets. Gaming targets 18-24 and 25-34. Finance targets 35-44, 45-54, 55-64. Health & Wellness targets 45-54, 55-64, 65+. Technology targets 18-24, 25-34, 35-44. Samples 2–4 age groups with category-appropriate weighting.

**`generate_ad_inventory(count=80, seed=42) → list[AdCandidate]`**
Creates `count` ads distributed across 8 categories (10 per category). For each ad:
1. Assigns category cyclically across the 8 categories
2. Samples advertiser name from `ADVERTISERS[category]`
3. Calls the three helper functions above
4. Samples priority from Beta(2,2) distribution — avoids extreme 0/1 values
5. Samples `has_softened_version` with 70% probability

**Connections:** Output consumed via `routes_data.get_ads()` by all routes, `simulation/engine.py`, and `ga/fitness.py`.

---

### `backend/data/content_library.py`

**Purpose:** Generates 100 `ContentItem` objects — 30 series episodes and 70 movies — with realistic intensity curves and natural break points.

#### Key Functions

**`_generate_intensity_curve(duration_minutes, mood, rng) → list[float]`**
Creates a per-minute intensity curve using a random walk:
1. Sets mood baseline: calm=0.2, uplifting=0.4, playful=0.35, energetic=0.6, intense=0.8, dark=0.7
2. Starts at baseline
3. Each minute: adds Gaussian noise N(0, 0.08), then smoothly pulls back toward baseline with momentum factor 0.3
4. Clamps all values to [0, 1]
5. Result: realistic intensity that wanders but stays in character

**`_find_break_points(intensity_curve, buffer_minutes=5) → list[int]`**
Identifies appropriate ad break minutes:
1. Never places breaks in first 5 or last 5 minutes (buffer)
2. Scores each minute by low intensity (lower = better break)
3. Finds local minima in the intensity curve
4. Enforces minimum gap of 8 minutes between breaks
5. Returns sorted list of break-point minutes

**`generate_content_item(item_id, is_series, rng) → ContentItem`**
Builds a single ContentItem:
- Series episodes: 22–45 minutes, assigned to season/episode numbers
- Movies: 85–150 minutes
- Samples genre from GENRES list
- Samples mood from ContentMood enum
- Calls `_generate_intensity_curve()` and `_find_break_points()`
- Series titles: "Show_{genre} S{n}E{n}", Movie titles: "{genre} Film {id}"

**`generate_content_library(count=100, seed=42) → list[ContentItem]`**
Creates 30 series + 70 movies using deterministic seed.

**Connections:** Output consumed via `routes_data.get_content()`. The `intensity_curve` and `natural_break_points` fields are used heavily in `simulation/breaks.py`.

---

### `backend/data/grounding.py`

**Purpose:** Bridge between the raw dataset pipeline output and the synthetic data generators. Loads processed distributions and exposes clean accessor functions. Every function has a hardcoded fallback so the system never crashes when datasets are unavailable.

#### Key Functions

**`load_distributions() → dict`**
Calls `pipeline.load_distributions()` which loads from `datasets/processed/distributions.json` if it exists, otherwise runs the pipeline. Returns a nested dict with `movielens`, `criteo`, and `avazu` sub-dicts.

**`get_grounded_engagement_stats() → tuple[float, float]`**
Returns `(mean, std)` for the engagement score distribution.
- If MovieLens data available: `(movielens_engagement_mean, 0.18)` — typically ~0.72
- Fallback: `(0.60, 0.18)`
- Used by `generate.py` to sample engagement scores from N(mean, std)

**`get_grounded_genre_weights() → dict[str, float]`**
Returns genre → probability mapping from MovieLens.
- Drama ~26%, Thriller ~16%, Comedy ~17%, Action ~14% (from actual data)
- Fallback: uniform distribution across 10 genres
- Used by `get_content_preferences_from_movielens()`

**`get_primetime_boost() → float`**
Returns the evening CTR boost from Avazu data.
- Computed as: `evening_mean_ctr − morning_mean_ctr` over Avazu's 40M rows
- Avazu is a mobile ad dataset — result is ~0.0 (flat hourly pattern on mobile)
- Fallback: 0.15 (used as default when Avazu data unavailable)
- Used by `advertiser_advocate.py` for primetime_map construction

**`get_grounded_ctr() → float`**
Returns mean click-through rate from Criteo dataset.
- Criteo data: ~3.1% CTR across 1M rows
- Fallback: 0.031
- Currently informational — used in documentation/metrics

**`get_content_preferences_from_movielens(rng, num_prefs) → list[str]`**
Samples `num_prefs` genres weighted by MovieLens genre distribution.
- Higher weight for Drama, Comedy, Action (more popular in MovieLens)
- Lower weight for Documentary, Western, Film-Noir
- Returns deduplicated list

**Connections:** Called by `generate.py` and `advertiser_advocate.py`. Depends on `pipeline.py`.

---

### `backend/data/pipeline.py`

**Purpose:** Processes three real-world datasets and outputs a `distributions.json` file. Designed for graceful degradation — every function returns fallback values if files are missing.

#### Constants

**`FALLBACK_GENRE_WEIGHTS`** — Hardcoded genre distribution used when MovieLens unavailable.

**`FALLBACK_CTR`** — 0.031 (3.1%) — industry average CTR for display advertising.

**`FALLBACK_HOURLY_CTR`** — Dict of hour → CTR values showing typical daily pattern (peaks at 17:00–21:00).

#### Key Functions

**`process_movielens(raw_dir) → dict`**
Processes MovieLens 25M dataset:
1. Looks for `raw/ml-25m/movies.csv` — if missing, returns fallback
2. Reads CSV with `csv.DictReader`, splits `genres` column by "|"
3. Maps 18 MovieLens genre names to our 10 genre names using `ml_to_our` dict (Adventure→Action, Crime→Thriller, War→Drama, etc.)
4. Normalizes counts to weights
5. Optionally reads `raw/ml-25m/ratings.csv` — reads first 100,000 rows, computes `mean_rating / 5.0` as engagement_mean
Returns: `{genre_weights, engagement_mean, engagement_std, source}`

**`process_criteo(raw_dir, max_rows=1_000_000) → dict`**
Processes Criteo Display Advertising dataset:
1. Looks for `raw/criteo/train.txt` (tab-separated)
2. Reads up to 1M rows, counts clicks (col 0 = label 0 or 1)
3. Computes `clicks / total` as mean CTR
Returns: `{mean_ctr, rows_processed, source}`

**`process_avazu(raw_dir) → dict`**
Processes Avazu CTR Prediction dataset:
1. Checks two locations: `raw/avazu-ctr-prediction/train.gz` (gzip) OR `raw/avazu/train.csv` (plain)
2. **Gzip handling:** `open_fn = gzip.open if use_gz else open`, then `open_fn(path, "rt", encoding="utf-8")`
3. Parses `hour` field (format: YYMMDDHH) — takes last 2 digits for hour of day
4. Accumulates `hourly_clicks` and `hourly_total` dicts
5. Computes `primetime_boost = mean(CTR 18:00-22:00) − mean(CTR 6:00-10:00)`
6. **Result on real data:** ~0.0 boost (mobile ads have flat hourly pattern)
Returns: `{hourly_ctr, primetime_boost, rows_processed, source}`

**`run_pipeline(raw_dir, processed_dir) → dict`**
Orchestrates all three processors, saves result to `datasets/processed/distributions.json`.

**`load_distributions(processed_dir) → dict`**
Loads from `distributions.json` if it exists, otherwise calls `run_pipeline()`.

**Design decision:** The `FALLBACK_*` constants were carefully chosen to represent realistic industry values so the system produces plausible output even without any downloaded datasets.

---

## 3. Simulation Layer

---

### `backend/simulation/fatigue.py`

**Purpose:** Implements the fatigue state machine — the core mechanism for protecting viewer welfare.

#### Key Functions

**`update_fatigue(ctx, decision, minutes_since_last_ad) → float`**
Computes new fatigue value:
```
decay = minutes_since_last_ad × 0.01
increment = {SHOW: 0.10, SOFTEN: 0.05, DELAY: 0.02, SUPPRESS: 0.00}[decision]
new_fatigue = clamp(current_fatigue - decay + increment, 0.0, 1.0)
```
This means: if 10 ad-free minutes pass, fatigue drops by 0.10 — exactly canceling one SHOW. The fatigue system self-regulates: showing ads at a sustainable rate keeps fatigue stable.

**`should_force_suppress(ctx) → bool`**
Returns `True` if `ctx.session_fatigue_accumulator > 0.85`. This is a hard override — once fatigue is too high, no ad gets shown regardless of any other scoring. This directly implements H2 (fatigue < 0.40 as mean; hard cap at 0.85).

**`fatigue_penalty(fatigue) → float`**
Returns 0.15 if fatigue > 0.70, else 0.0. Applied as a satisfaction penalty in outcome scoring.

**`get_effective_fatigue(user, ctx) → float`**
Combines user's base fatigue (`user.fatigue_level`) with session accumulator:
`effective = clamp(user.fatigue_level + ctx.session_fatigue_accumulator, 0.0, 1.0)`
The user's base fatigue represents long-term ad exposure history. Session fatigue represents what has happened this session.

---

### `backend/simulation/breaks.py`

**Purpose:** Determines where in content it is appropriate to insert an ad break.

#### Key Functions

**`score_break_point(content, minute) → float`**
Scores how good a minute is for an ad break:
- Looks up `content.intensity_curve[minute]` (if available)
- Lower intensity = higher break point score = better time for an ad
- Formula: `score = 1.0 - intensity_curve[minute]`
- Minutes not in the intensity curve return a neutral score of 0.5

**`select_best_break_points(content, max_breaks, min_gap=8) → list[int]`**
Selects the best ad break minutes for a piece of content:
1. Gets all valid minutes (skipping first/last 5 per buffer setting)
2. Scores each valid minute via `score_break_point()`
3. Sorts by score descending
4. Greedily selects break points, enforcing `min_gap` minutes between any two breaks
5. Returns sorted list of selected minutes

**`get_next_break_point(content, current_minute, min_gap) → Optional[int]`**
Finds the next valid break after `current_minute`, respecting the minimum gap. Used for sequential ad scheduling.

**`get_scored_break_points(content) → list[tuple[int, float]]`**
Returns all `(minute, score)` pairs for visualization in the frontend SessionTimeline component.

---

### `backend/simulation/binge.py`

**Purpose:** Detects and handles binge-watching behavior, which requires different ad policies.

#### Key Functions

**`is_binge_active(user, episodes_watched, content_queue) → bool`**
Binge detection requires ALL of:
1. `user.binge_tendency > 0.5` — this user is prone to binging
2. `len(content_queue) >= 2` — there are ≥2 more episodes queued
3. `episodes_watched >= 1` — they've already watched at least one episode

All three conditions must be true. This is conservative — only triggers genuine binge sessions.

**`binge_ad_frequency_multiplier(user, is_binging) → float`**
Returns 0.7 if binging (reduce ad frequency by 30%) — binge watchers are more valuable viewers and more sensitive to interruption.

**`binge_fatigue_sensitivity_multiplier(is_binging) → float`**
Returns 1.2 if binging (20% more fatigue-sensitive) — each ad during a binge has greater impact.

**`update_binge_state(ctx, is_binging) → SessionContext`**
Updates `ctx.is_binging` field and returns new context.

**`get_binge_summary(user, episodes_watched, content_queue) → dict`**
Returns a summary dict for the API response showing binge status, tendency, queue length, and whether multipliers are active.

---

### `backend/simulation/session.py`

**Purpose:** Generates all `AdOpportunity` objects for a viewing session — i.e., all the decision points that will need to be evaluated.

#### Key Functions

**`simulate_session(user, content, ad_pool, content_queue, time_of_day, season, seed) → tuple[list[AdOpportunity], SessionContext]`**

This function creates a "plan" for a session — it does not make decisions, only generates opportunities:

1. Calls `select_best_break_points()` to find break minutes
2. For each break minute, selects a random ad from `ad_pool`
3. Creates a `SessionContext` snapshot at that minute:
   - `ads_shown_this_session` is set to the count of ads shown **before** this break
   - **Important:** These contexts are snapshots, not live — they record the state at generation time
4. Creates an `AdOpportunity` bundling (user, ad, context)
5. Returns the full list

**`apply_decision(ctx, user, decision, current_minute, minutes_gap) → SessionContext`**

This is the **key bug-fix function**. After a decision is made, this updates the running session context:
1. Updates `ads_shown_this_session`: increments by 1 for SHOW/SOFTEN, unchanged for DELAY/SUPPRESS
2. Calls `update_fatigue(ctx, decision, minutes_gap)` to update `session_fatigue_accumulator`
3. Returns the updated context

**Why this function exists:** When `simulate_session()` generates `AdOpportunity` objects, it takes snapshots of session state. But those snapshots become stale as decisions are made. Without `apply_decision()`, every opportunity would show `ads_shown_this_session=0` because the simulation generated them all at once before any decisions were made. The `engine.py` and `routes_simulate.py` thread this updated context forward by calling `apply_decision()` after each decision and using the result as the base context for the next opportunity.

---

### `backend/simulation/engine.py`

**Purpose:** Evaluates how well any ad policy performs across all users. Provides three baseline policies for comparison against the GA-evolved policy.

#### Key Functions

**`evaluate_policy(policy_fn, user, content, ad_pool, time_of_day, season) → dict`**

Runs a full session for one user under a given policy and scores the outcome:

1. Calls `simulate_session()` to get all opportunities
2. Creates `running_ctx` from the first opportunity's context
3. **For each opportunity:**
   - Creates `live_opp` by merging `running_ctx` (current state) with the opportunity's `current_minute`
   - Calls `policy_fn(live_opp)` to get the decision
   - Scores the outcome (SHOW/SOFTEN/DELAY/SUPPRESS × relevant/irrelevant × fatigue)
   - Calls `apply_decision()` to update `running_ctx`
4. Returns `{satisfaction, revenue, fatigue, fitness, total_decisions, decision_counts}`

**Outcome scoring table:**
| Decision | Relevant | Low Fatigue | Satisfaction | Revenue |
|----------|----------|-------------|-------------|---------|
| SHOW | ✓ | ✓ | 0.75 | 1.00 |
| SHOW | ✓ | ✗ | 0.45 | 0.85 |
| SHOW | ✗ | ✓ | 0.30 | 0.70 |
| SHOW | ✗ | ✗ | 0.15 | 0.50 |
| SOFTEN | ✓ | — | 0.60 | 0.55 |
| SOFTEN | ✗ | — | 0.35 | 0.55 |
| DELAY | — | — | 0.65 | 0.15 |
| SUPPRESS | — | — | 0.70 | 0.02 |

**Session frequency penalties** (applied to satisfaction):
- `ads_shown == 2`: −0.08
- `ads_shown >= 3`: −0.15

**Three baseline policies:**

**`policy_always_show(opp) → AdDecision.SHOW`**
Shows every ad unconditionally. Represents naive maximum-revenue strategy.

**`policy_random(opp) → AdDecision`**
Randomly chooses SHOW or SUPPRESS with 50/50 probability. Represents uninformed baseline.

**`policy_frequency_cap(cap=3)`**
Shows ads until `ads_shown_this_session >= cap`, then suppresses. Represents a common industry practice. The `running_ctx` threading fix is critical here — without it, `ads_shown_this_session` never increments and this policy degenerates to always_show.

---

## 4. Agent Layer

---

### `backend/agents/user_advocate.py`

**Purpose:** Scores an ad opportunity from the viewer's perspective. Produces a score representing "how acceptable is this ad for this user right now?"

#### `score_user_advocate(user, ad, ctx, chromosome) → AgentScore`

Computes a weighted sum of factors, all modulated by chromosome genes.
No fixed base score — gene values are the primary drivers of the [0, 1] range.

**Factor 1: Ad Tolerance Base**
```python
tolerance_base = user.ad_tolerance * 0.20   # [0.00, 0.20]
```
`ad_tolerance` from UserProfile is now incorporated. High-tolerance users have a
higher floor, reflecting that they are genuinely more receptive to advertising.

**Factor 2: Mood Bonus**
```python
mood_bonus = clip(mood_modifier + 0.15, 0.0, 0.25)   # [0.00, 0.25]
```
Positive content moods improve ad receptiveness.

**Factor 3: Relevance Contribution**
```python
relevance_contribution = chromosome.relevance_weight * (0.40 if relevant else 0.05)
```
Gene scales how much relevance matters. Irrelevant ads still get a small floor (0.05).

**Factor 4: Timing Contribution**
```python
timing_contribution = chromosome.timing_weight * (0.18 if time_matches else 0.0)
```

**Factor 5: Fatigue Penalty**
```python
fatigue_penalty = chromosome.fatigue_weight * session_fatigue * 0.55   # up to -0.55
```
Gene controls how sensitive the policy is to fatigue.

**Factor 6: Session Depth Penalty**
```python
depth_penalty = chromosome.session_depth_factor * (0.28 if ads>2 else 0.14 if ads>1 else 0.0)
```
The more ads already shown, the less acceptable new ones are.

**Factor 6: Mood Modifier**
Directly from content mood (not gene-modulated):
```
calm: +0.10, uplifting: +0.08, playful: +0.05, energetic: 0.0, intense: -0.10, dark: -0.15
```

**Factor 7 & 8: Context Penalties**
```python
intensity_penalty = 0.12 if current break is high-intensity else 0.0
binge_penalty = 0.08 * chromosome.session_depth_factor if ctx.is_binging else 0.0
```

**Final score:** `clamp(base + bonus - penalties + modifiers, 0.0, 1.0)`

**Reasoning generation:** Sorts all factors by absolute value, takes top 2, formats as: `"Score: 0.623. Ad targets this user's interests. Key factors: relevance_bonus=+0.640, fatigue_penalty=-0.225."`

---

### `backend/agents/advertiser_advocate.py`

**Purpose:** Scores the same opportunity from the advertiser's perspective. Produces a score representing "how valuable is this impression for this advertiser?"

#### `score_advertiser_advocate(user, ad, ctx, chromosome) → AgentScore`

No fixed base score — `category_boost` gene is the primary driver.

**Factor 1: Relevance Boost**
```python
relevance_boost = chromosome.category_boost * (0.50 if relevant else 0.08)
```
Relevant ads are more valuable (higher expected CTR). Irrelevant ads get a small
floor (0.08) because impression value is never zero.

**Factor 3: Engagement Boost**
```python
engagement_boost = user.engagement_score * 0.3           # up to +0.285
```
Higher engagement users are more valuable advertising targets.

**Factor 4: Primetime Boost**
```python
_pt = get_primetime_boost()   # From Avazu data (~0.0 on real data, 0.15 fallback)
primetime_map = {
    "morning": 0.0,
    "afternoon": round(_pt * 0.33, 4),
    "evening": _pt if _pt > 0 else 0.15,
    "latenight": _pt if _pt > 0 else 0.15,
}
primetime_boost = primetime_map[ctx.time_of_day.value]
```
Note: Avazu is a mobile dataset showing flat hourly CTR, so `_pt ≈ 0.0` on real data. The `else 0.15` fallback ensures evening still gets a boost when Avazu data is unavailable.

**Factor 5: Priority Factor**
```python
priority_factor = (ad.priority - 0.5) * 0.2    # range: -0.10 to +0.10
```
Higher-priority ads (closer to 1.0) get a small boost; low-priority ads get a penalty.

**Factor 6: Seasonal Affinity**
```python
seasonal_affinity = ad.seasonal_affinity.get(ctx.season.value, 0.0)
```
Direct lookup from the ad's pre-computed seasonal affinity dict.

**Factor 7: Demographic Match**
```python
demo_bonus = 0.08 if user.age_group in ad.target_demographics else 0.0
```
Flat bonus when the ad is targeting this user's demographic.

---

### `backend/agents/negotiator.py`

**Purpose:** Combines the two agent scores into a final AdDecision. This is where the balancing act happens.

#### `negotiate(ua_score, adv_score, chromosome, user_id, ad_id, session_id) → NegotiationResult`

**Step 1: Combine scores**
```python
combined = 0.55 * ua_score.score + 0.45 * adv_score.score
```
The 0.55/0.45 split means user welfare is weighted slightly more than advertiser revenue. This is a design choice reflecting the paper's human-centered framing.

**Step 2: Compute decision thresholds from chromosome**
```python
show_thresh   = 0.35 + chromosome.frequency_threshold * 0.30    # range: [0.35, 0.65]
soften_thresh = show_thresh   - 0.06 - chromosome.soften_threshold  * 0.14  # variable
delay_thresh  = soften_thresh - 0.04 - chromosome.delay_probability * 0.10  # variable
```
All three threshold-related genes are now active:
- `frequency_threshold`: shifts the base SHOW bar (conservative vs aggressive)
- `soften_threshold`: independently controls the width of the SOFTEN zone
- `delay_probability`: independently controls the width of the DELAY zone

**Step 3: Map combined score to decision**
```python
if combined >= show_thresh:   decision = SHOW
elif combined >= soften_thresh: decision = SOFTEN
elif combined >= delay_thresh:  decision = DELAY
else:                           decision = SUPPRESS
```

**Step 4: Build NegotiationResult**
Assembles the full result object with both agent scores, combined score, decision, and a reasoning string.

---

### `backend/agents/llm_reasoning.py`

**Purpose:** Optionally enriches a NegotiationResult with LLM-generated natural language reasoning. Three-layer fallback ensures the system never fails due to LLM unavailability.

#### `enrich_with_llm_reasoning(result, user, ad) → NegotiationResult`

**Step 1: Check cache**
Computes MD5 hash of `(user.id, ad.id, result.decision.value, round(result.combined_score, 2))`. If this exact combination was seen before, returns cached reasoning immediately — avoids duplicate LLM calls for the same scenario.

**Step 2: Build prompt**
Constructs a structured prompt:
```
You are explaining an ad placement decision for a streaming platform.
User: {name}, age {age_group}, interests: {interests}
Ad: {category} from {advertiser}, duration {duration}s
Decision: {decision} (score: {combined_score:.3f})
User Advocate score: {ua_score:.3f} - {ua_reasoning}
Advertiser Advocate score: {adv_score:.3f} - {adv_reasoning}
Explain this decision in 2-3 sentences from a human-centered perspective.
```

**Step 3: Try Groq**
Uses OpenAI-compatible client pointed at `https://api.groq.com/openai/v1`. Model: `llama-3.3-70b-versatile`. 5-second timeout. If API key not set or call fails → go to Step 4.

**Step 4: Try Gemini**
Falls back to Google's Gemini API (`gemini-2.5-flash`). Same 5-second timeout. If this also fails → go to Step 5.

**Step 5: Template fallback**
Generates a deterministic reasoning string from templates:
```python
reasoning = (
    f"Decision: {decision}. "
    f"Combined score {score:.3f} reflects "
    f"{'strong' if ua_score > 0.6 else 'moderate'} user alignment and "
    f"{'high' if adv_score > 0.6 else 'standard'} advertiser value."
)
```

**Step 6: Cache and return**
Caches the result, returns updated NegotiationResult with new reasoning string.

---

## 5. Genetic Algorithm Layer

---

### `backend/ga/fitness.py`

**Purpose:** The performance-critical inner loop of the GA. Evaluates a chromosome's fitness using fully vectorized NumPy operations — no Python loops, no LLM calls, no I/O.

#### Why vectorized?

The GA calls this function 30 chromosomes × 50 generations = 1,500 times per evolution run. Each call processes 200 users × 10 scenarios = 2,000 scenarios. Using Python loops would take minutes; NumPy vectorization completes in milliseconds.

#### `_user_advocate_score_vectorized(chromosome, fatigue, relevant, time_matches, ads_shown, mood_modifier, intensity_high, is_binging) → np.ndarray`

Vectorized version of the User Advocate scoring. All inputs are 1-D arrays of length N. Operations use `np.where()` for conditional logic:
```python
relevance_bonus = np.where(relevant,
    1.0 * c.relevance_weight * 0.8,
    0.15 * c.relevance_weight * 0.8
)
fatigue_penalty = fatigue * c.fatigue_weight * 1.5
timing_bonus = np.where(time_matches, c.timing_weight * 0.3, 0.0)
session_penalty = np.where(ads_shown > 2, 0.3 * c.session_depth_factor,
                  np.where(ads_shown > 1, 0.15 * c.session_depth_factor, 0.0))
# ... add mood_modifier, subtract penalties
score = np.clip(base + relevance_bonus - fatigue_penalty + timing_bonus
                - session_penalty + mood_modifier - intensity_penalty - binge_penalty,
                0.0, 1.0)
```

#### `_advertiser_advocate_score_vectorized(...) → np.ndarray`

Same pattern for Advertiser Advocate. Computes all 7 factors as arrays, sums them, clips to [0,1].

#### `_determine_decision_vectorized(chromosome, combined) → np.ndarray`

Maps combined score array to integer decision codes (0=SHOW, 1=SOFTEN, 2=DELAY, 3=SUPPRESS).
All three threshold-related genes are active — each controls an independent offset:
```python
show_thresh   = 0.35 + chromosome.frequency_threshold * 0.30
soften_thresh = show_thresh   - 0.06 - chromosome.soften_threshold  * 0.14
delay_thresh  = soften_thresh - 0.04 - chromosome.delay_probability * 0.10

decision = np.full(N, SUPPRESS_IDX)
decision = np.where(combined >= delay_thresh,  DELAY_IDX,  decision)
decision = np.where(combined >= soften_thresh, SOFTEN_IDX, decision)
decision = np.where(combined >= show_thresh,   SHOW_IDX,   decision)
```

#### `_score_outcomes_vectorized(decisions, relevant, fatigue, ads_shown) → (sat_array, rev_array)`

Converts decisions to satisfaction and revenue using vectorized lookup:
```python
# SHOW outcomes
sat = np.where(show & relevant & low_fat, 0.75, sat)
rev = np.where(show & relevant & low_fat, 1.00, rev)
# ... 8 conditions for SHOW, then SOFTEN, DELAY, SUPPRESS
# Session penalties
sat = np.where(ads_shown >= 3, np.maximum(0.0, sat - 0.15), sat)
```

#### `evaluate_chromosome_fitness(chromosome, users, content_items, ad_pool, scenarios_per_user=10) → float`

Main function that orchestrates the vectorized evaluation:
1. Builds N = `len(users) × scenarios_per_user` random scenarios
2. Randomly samples ad indices, content indices, ads_shown, time_of_day, season
3. Computes relevance (ad.category in user.interests) for each scenario
4. Calls all four vectorized functions
5. Applies force_suppress override where `session_fatigue > 0.85`
6. Computes `fitness = 0.6 × mean(sat) + 0.4 × mean(rev)`

#### `evaluate_population_fitness(population, ...) → list[float]`

Calls `evaluate_chromosome_fitness()` for each chromosome in the population with a unique `rng_seed` (prevents all chromosomes seeing identical scenarios).

---

### `backend/ga/engine.py`

**Purpose:** Implements the full Genetic Algorithm lifecycle — population initialization, generational evolution, convergence detection, and restart-on-stuck logic.

#### Standalone Functions

**`init_population(size, seed) → list[Chromosome]`**
Creates `size` chromosomes with all 8 genes sampled uniformly from [0,1] using `random.Random(seed)`.

**`select_parents(population, fitnesses, num_parents, rng) → list[Chromosome]`**
Tournament selection: for each parent needed, samples 3 random indices, returns chromosome with highest fitness. Ensures selection pressure toward better solutions while maintaining diversity (unlike greedy top-2 selection).

**`uniform_crossover(parent_a, parent_b, rng) → tuple[Chromosome, Chromosome]`**
For each of the 8 genes, independently picks from parent_a or parent_b with 50% probability. Creates two offspring (both used). More disruptive than one-point crossover but better at combining good gene combinations from different chromosomes.

**`mutate(chromosome, mutation_rate, mutation_strength, rng) → Chromosome`**
For each gene, with probability `mutation_rate=0.15`:
- Sample delta from `N(0, mutation_strength/2)` = `N(0, 0.15)`
- Add to gene value, clamp to [0,1]
The small standard deviation (0.15) ensures mutations are gradual — exploration without destroying good solutions.

**`compute_diversity(population) → float`**
Measures genetic diversity as normalized mean variance across all 8 genes:
```python
vecs = np.array([c.to_vector() for c in population])
variance = np.mean(np.var(vecs, axis=0))
max_variance = 1.0 / 12.0  # variance of uniform [0,1]
return min(1.0, variance / max_variance)
```
Value of 1.0 = maximally diverse, 0.0 = all chromosomes identical (converged).

**`check_convergence(fitness_history, window=10, threshold=0.001) → bool`**
Returns True if the improvement over the last `window` generations is less than `threshold`. Computed as `max(recent) - min(recent) < 0.001`.

**`evolve_one_generation(population, fitnesses, ga_cfg, rng) → list[Chromosome]`**
Produces the next generation:
1. Sorts population by fitness descending
2. Preserves top `elite_count = 20% × 30 = 6` chromosomes unchanged
3. Fills remaining 24 slots with children from `select_parents → uniform_crossover → mutate`

#### `GAEngine` Class

**`__init__`**: Stores users, content, ads. Creates `random.Random(seed)` for reproducibility.

**`initialize()`**: Creates random population, calls `_evaluate()`.

**`_evaluate()`**: Calls `evaluate_population_fitness()` with `rng_seed = np_seed + current_generation` — different scenarios each generation, but deterministic. Updates `best_chromosome` if improvement found, otherwise increments `generations_since_improvement`.

**`_restart()`**: If stuck for 20 generations, creates a completely new random population. Preserves `best_chromosome` (it's never overwritten unless a better one is found).

**`step() → dict`**: One generation: check stuck → evolve → evaluate → check convergence → return stats dict with generation, best_fitness, avg_fitness, diversity, converged, best_chromosome.

**`run(max_generations) → generator`**: Yields stats dict after each generation. Stops when `converged=True` or `max_generations` reached.

---

### `backend/ga/storage.py`

**Purpose:** Persists and retrieves evolved chromosomes as JSON files. Enables the system to remember its best evolved policy across restarts.

#### Key Functions

**`save_chromosome(chromosome, label) → str`**
Filename format: `chromosome_20260322_165907_job_abc123_0.5039.json`
File contents:
```json
{
  "genes": [0.4935, 0.9506, 0.0, 0.4427, 0.8037, 0.9848, 0.5423, 0.755],
  "fitness": 0.5039,
  "gene_names": ["fatigue_weight", "relevance_weight", ...],
  "saved_at": "2026-03-22T16:59:07",
  "label": "job_e4f96067"
}
```

**`load_chromosome(path) → Chromosome`**
Reads JSON, calls `Chromosome.from_vector(genes)`, sets `fitness` field.

**`list_chromosomes(directory) → list[dict]`**
Globs for `chromosome_*.json` in the chromosomes directory, parses each, returns sorted by fitness descending. Skips malformed files silently.

**`load_best_chromosome() → Optional[Chromosome]`**
Calls `list_chromosomes()`, loads the first entry (highest fitness).

---

## 6. LangGraph Orchestration

---

### `backend/graph/builder.py`

**Purpose:** Defines two LangGraph computation graphs — one for evolution, one for per-request decision making. LangGraph provides structured, inspectable workflows as an alternative to ad-hoc function chains.

**Note:** Graceful import fallback. If LangGraph is not installed, `build_evolution_graph()` and `build_decision_graph()` return `None` with a warning. The system continues to work via direct function calls.

#### Evolution Graph

```
START → [node_init_ga] → [node_evolve] ←→ (loop via should_continue_evolving) → END
```

**`node_init_ga(state) → state`**
- Creates `GAEngine` from `state["users"]`, `state["content"]`, `state["ads"]`
- Calls `engine.initialize()`
- Stores engine in `state["engine"]`

**`node_evolve(state) → state`**
- Calls `engine.step()` once
- Appends stats to `state["generation_history"]`
- Updates `state["best_chromosome"]` and `state["best_fitness"]`

**`should_continue_evolving(state) → str`**
- Returns `"evolve"` if `generation < max_generations and not converged`
- Returns `END` otherwise

This graph is an alternative to the direct `engine.run()` generator. It is more inspectable (LangGraph can trace each node) but slower due to state serialization overhead.

#### Decision Graph

```
START → parallel[node_user_advocate, node_advertiser_advocate] → node_negotiate → node_llm_explain → END
```

**`node_user_advocate(state) → state`**
Calls `score_user_advocate()`, stores `AgentScore` in `state["user_advocate_score"]`.

**`node_advertiser_advocate(state) → state`**
Calls `score_advertiser_advocate()`, stores in `state["advertiser_advocate_score"]`.

Both agent nodes run in **parallel** — LangGraph's parallel branch execution means the two scoring functions run concurrently, halving latency for this step.

**`node_negotiate(state) → state`**
Calls `negotiate()` with both agent scores, stores `NegotiationResult` in state.

**`node_llm_explain(state) → state`**
If `state["use_llm"]` is True, calls `enrich_with_llm_reasoning()`. Otherwise passes through unchanged.

---

## 7. Experiment Layer

---

### `backend/experiments/runner.py`

**Purpose:** Orchestrates the full research experiment: evaluate baselines, run N independent GA evolutions, run ablations, test hypotheses, run statistical tests.

#### `run_full_experiment(num_runs, max_generations, num_users, output_dir, seed_offset, verbose) → dict`

Execution sequence:
1. **Generate data:** `generate_users(num_users)`, `generate_content_library()`, `generate_ad_inventory()`
2. **Baseline evaluation:** Runs `evaluate_policy()` with all 3 baselines across all users, averages metrics
3. **Evolution loop:** Runs `num_runs` independent `GAEngine` instances with different seeds (`seed_offset + run_idx`). Collects best chromosome per run.
4. **Aggregate evolved results:** Evaluates best chromosome from each run, averages satisfaction/revenue/fatigue/diversity
5. **Ablation study:** Calls `run_ablations()`
6. **Hypothesis testing:** Calls `compute_h1/h2/h3()`
7. **Statistical tests:** Calls `run_statistical_tests()`
8. **Save results:** Writes JSON to `results/experiment_{timestamp}.json`
9. **Return:** Full results dict

**`_chromosome_to_policy(chromosome) → Callable`**
Converts a `Chromosome` into a `policy_fn` compatible with `evaluate_policy()`. The policy:
1. Calls `score_user_advocate()` and `score_advertiser_advocate()`
2. Calls `negotiate()` with the chromosome
3. Returns the `AdDecision`

---

### `backend/experiments/ablations.py`

**Purpose:** Tests whether each component of AdaptAd contributes to performance by removing it and measuring the impact.

#### `run_ablations(users, content_items, ads, best_chromosome) → dict`

Five conditions, each evaluated across all users:

**`full_system`** — GA chromosome + both agents (0.55/0.45 weighting). This is the full AdaptAd system.

**`ga_only`** — GA chromosome + simplified scoring. Instead of full agent reasoning, uses a simplified heuristic that ignores mood, timing, and binge context. Tests whether the GA alone (without agent reasoning depth) performs as well.

**`agents_no_ga`** — Default chromosome (all genes = 0.5) + both agents. Tests whether the agent scoring framework alone (without GA optimization) is useful.

**`user_advocate_only`** — Ignores Advertiser Advocate entirely (ADV weight = 0). Tests what happens when we maximize user satisfaction with no revenue constraint.

**`advertiser_advocate_only`** — Ignores User Advocate entirely (UA weight = 0). Tests what happens when we maximize revenue with no user welfare constraint.

**Key insight from results:**
- user_advocate_only: high satisfaction (0.589) but very low revenue (0.371) — over-suppresses
- advertiser_advocate_only: nearly identical to always_show (974/983 = 99% SHOW) — revenue-only approach is degenerate
- full_system outperforms both single-agent conditions on the combined fitness metric

---

### `backend/experiments/metrics.py`

**Purpose:** Computes the three research hypotheses and the diversity index.

#### `compute_diversity_index(decisions) → float`

Normalized Shannon entropy over the four decision types:
```python
counts = Counter(decisions)
probs = [counts.get(d, 0) / len(decisions) for d in ["SHOW","SOFTEN","DELAY","SUPPRESS"]]
entropy = -sum(p * log2(p) for p in probs if p > 0)
max_entropy = log2(4)  # = 2.0 (uniform distribution over 4 decisions)
return entropy / max_entropy
```
Value of 1.0 = equal distribution of all 4 decisions. Value of 0.0 = only one decision type used.

#### `compute_h1(fitnesses, threshold=0.65, baseline_fitnesses) → dict`

H1: "The GA-evolved policy achieves fitness > 0.65 and outperforms all baselines."
- `passes`: bool — mean fitness > threshold (currently FAILS at 0.537)
- `baseline_comparisons`: for each baseline, `prop_runs_better` (fraction of 30 runs that beat the baseline) and `mean_delta`
- **Note:** `prop_runs_better = 1.0` for all baselines — the GA beats every baseline in 100% of runs

#### `compute_h2(fatigues, satisfactions) → dict`

H2: "Mean fatigue < 0.40 AND mean satisfaction > 0.70 (as relevance proxy)."
- `fatigue_passes`: True if mean fatigue < 0.40 (**PASSES at 0.344**)
- `relevance_passes`: True if mean satisfaction > 0.70 (**FAILS at 0.433**)

#### `compute_h3(diversities, threshold=0.15) → dict`

H3: "Decision diversity index > 0.15."
- `passes`: True if mean diversity > 0.15 (**PASSES strongly at 0.655**)
- `prop_runs_pass`: fraction of 30 runs that individually pass

---

### `backend/experiments/stats.py`

**Purpose:** Statistical hypothesis testing with proper corrections for multiple comparisons.

#### `_wilcoxon_one_sample(values, target) → (statistic, p_value)`

Tests whether a set of values is significantly greater than `target` using Wilcoxon signed-rank test. Uses `scipy.stats.wilcoxon` if available, otherwise falls back to a sign test (count of values above target). The Wilcoxon test is non-parametric — no assumption of normal distribution — appropriate for small samples of GA fitness values.

#### `_wilcoxon_paired(a_values, b_values) → (statistic, p_value)`

Paired Wilcoxon test for comparing GA fitness vs. a baseline across 30 runs. Tests whether the differences `a - b` are significantly positive.

#### `_holm_bonferroni(p_values) → list[bool]`

Holm-Bonferroni correction for multiple comparisons. When testing GA vs. 3 baselines simultaneously, the probability of a false positive increases. Holm-Bonferroni controls family-wise error rate by sorting p-values and applying increasingly strict thresholds.

#### `run_statistical_tests(ga_fitnesses, baseline_fitnesses_dict) → dict`

Runs:
1. One-sample Wilcoxon: are GA fitnesses > 0.65? (H1 absolute threshold)
2. Paired Wilcoxon vs. each baseline: GA vs always_show, GA vs random, GA vs freq_cap
3. Holm-Bonferroni correction on the three pairwise p-values
Returns all statistics with method notes.

#### `run_sensitivity_analysis(users, content, ads, chromosome, perturbation_size=0.2) → dict`

For each of the 8 genes:
1. Creates perturbed chromosome with gene + perturbation_size (clamped)
2. Creates perturbed chromosome with gene - perturbation_size (clamped)
3. Evaluates fitness of both
4. Sensitivity = `|fitness_plus - fitness_minus| / (2 * perturbation_size)`

Higher sensitivity means that gene has more leverage over the fitness — changing it matters more.

---

## 8. Database Layer

---

### `backend/db/database.py`

**Purpose:** SQLite persistence using aiosqlite (async SQLite). Stores decisions, A/B sessions, ratings, and evolution runs for historical analysis and user study data collection.

**Four tables:**

**`decisions`** — Every NegotiationResult ever produced by the API:
- `session_id`, `user_id`, `ad_id`, `decision`
- `combined_score`, `user_advocate_score`, `advertiser_advocate_score`
- `reasoning`, `chromosome_genes` (JSON array), `timestamp`

**`ab_sessions`** — A/B test session metadata:
- `id`, `user_id`, `content_id`
- `adaptad_decisions`, `baseline_decisions` (JSON)
- `adaptad_label`, `baseline_label` (X or Y, randomized)
- `created_at`, `completed` flag

**`ab_ratings`** — Per-participant ratings:
- `session_id`, `session_label` (X or Y)
- `annoyance`, `relevance`, `willingness` (1–5 each)
- `participant_notes`, `rated_at`

**`evolution_runs`** — GA run metadata:
- `job_id`, `status`, `current_generation`, `max_generations`
- `best_fitness`, `best_chromosome` (JSON), `history` (JSON)
- `started_at`, `completed_at`

#### Key Functions

**`init_db(path)`** — Async. Called at FastAPI startup via lifespan. Creates all 4 tables with `CREATE TABLE IF NOT EXISTS`.

**`get_db()`** — FastAPI async dependency. Yields an `aiosqlite.Connection` with `row_factory = aiosqlite.Row` (allows column-name access on results). Used as `Depends(get_db)` in route functions.

**`log_decision(db, result, chromosome_genes)`** — Inserts NegotiationResult into decisions table. Wrapped in try/except so logging failures never crash the decision pipeline.

---

## 9. API Layer

---

### `backend/main.py`

**Purpose:** FastAPI application entry point. Wires everything together.

**Lifespan context manager:** Calls `init_db()` on startup, ensuring tables exist before any request is handled.

**CORS middleware:** `allow_origins=["*"]` — allows the Vite dev server on port 5173 to call the API on port 8000 during development.

**Routers included:**
- `data_router` — `/api/users`, `/api/ads`, `/api/content`, `/api/health`
- `evolve_router` — `/api/evolve/*` and `/api/chromosome/*`
- `decide_router` — `/api/decide/*`
- `simulate_router` — `/api/simulate/*`
- `ab_router` — `/api/ab/*`
- `experiments_router` — `/api/experiments/*`
- `ws_router` — `/ws/evolve/{job_id}` (WebSocket)

---

### `backend/api/routes_data.py`

**Purpose:** Serves the static data pools (users, ads, content). Uses module-level singletons generated once per process to avoid regenerating on every request.

**Module-level singletons:** `_users`, `_ads`, `_content` — initialized to `None`, generated lazily on first access. All use `seed=42` for reproducibility.

**`get_users() / get_ads() / get_content()`** — Accessor functions used by ALL other route files via import. Single source of the data pools.

**Routes:**
- `GET /api/users?limit=200&offset=0` — paginated user list
- `GET /api/users/{user_id}` — single user by ID (404 if not found)
- `GET /api/ads?category=Gaming` — optionally filter by category
- `GET /api/content?genre=Drama` — optionally filter by genre
- `GET /api/health` — returns `{status: "ok", users: 200, ads: 80, content: 100}`

---

### `backend/api/routes_evolve.py`

**Purpose:** Manages GA evolution jobs. Each job runs in a background thread (FastAPI BackgroundTasks) so the HTTP response returns immediately.

**`_jobs: dict[str, dict]`** — In-memory store. Keys are UUID strings. Values are job state dicts containing: status, history, best_chromosome, ws_queue, stop_requested.

**`_run_evolution(job_id, max_generations, seed)`** — Background function:
1. Creates `GAEngine` with the data pools
2. Calls `engine.run(max_generations)` — generator
3. Each generation: appends to `job["history"]`, pushes to `job["ws_queue"]` if a WebSocket client is connected
4. After all generations: saves chromosome to disk, sets `status="completed"`, pushes "converged" message to ws_queue

**Routes:**
- `POST /api/evolve` — starts job, returns `{job_id, status: "queued"}`
- `GET /api/evolve/{job_id}` — returns full job state including generation history
- `POST /api/evolve/{job_id}/stop` — sets `stop_requested=True`, background task checks this each generation

---

### `backend/api/routes_decide.py`

**Purpose:** Single-decision and batch-decision endpoints. The core inference API.

**`_current_chromosome`** — Global. Loaded from disk (best saved chromosome) or defaults to `Chromosome()` (all genes = 0.5). Updated via `/api/chromosome/set`.

**`_make_decision(user, ad, ctx, chromosome, use_llm, session_id) → NegotiationResult`**
Core decision function used by both `/decide` and `/decide/batch`:
1. Checks `should_force_suppress()` — if fatigue > 0.85, returns immediate SUPPRESS
2. Calls `score_user_advocate()` and `score_advertiser_advocate()`
3. Calls `negotiate()`
4. Optionally calls `enrich_with_llm_reasoning()`

**Routes:**
- `POST /api/decide` — single decision. Accepts `DecideRequest` with user_id, ad_id, context params. Optionally accepts `chromosome_genes` to override the stored chromosome.
- `POST /api/decide/batch` — runs all 200 users through the same ad + context, returns aggregated decision counts and per-user results table.
- `GET /api/decide/{decision_id}` — retrieves from `_decision_log` in-memory cache.
- `POST /api/chromosome/set` — updates `_current_chromosome` with a new gene vector.

---

### `backend/api/routes_simulate.py`

**Purpose:** Full session simulation — all break points for one user × one content item.

**`POST /api/simulate/session`**
1. Looks up user and content by ID
2. Calls `simulate_session()` to get all opportunities
3. **Threads `running_ctx` forward** (same pattern as `engine.py`) — each decision uses the live session state
4. For each break point: calls force-suppress check, then full agent pipeline, then `apply_decision()`
5. Records per-break info: minute, ad details, decision, scores, reasoning, fatigue at break, ads shown before
6. Returns full timeline with summary stats

---

### `backend/api/routes_ab.py`

**Purpose:** A/B testing infrastructure for user study. Compares AdaptAd vs. random baseline within a single session to control for content effects.

**`POST /api/ab/start`**
1. Runs AdaptAd session via `_run_adaptad_session()`
2. Runs random baseline via `_run_random_session()` (SHOW or SUPPRESS randomly)
3. **Randomizes label assignment:** 50% chance X=AdaptAd, 50% chance X=random. Participant never knows which is which. This prevents bias in ratings.
4. If both sessions produce identical decisions, regenerates random session (up to 5 attempts)
5. Returns session with `session_x` and `session_y` decision records

**`POST /api/ab/{session_id}/rate`**
Accepts `{session_label: "X"|"Y", annoyance: 1-5, relevance: 1-5, willingness: 1-5}`. Marks session as completed when both X and Y are rated.

**`GET /api/ab/results`**
Computes aggregate statistics across all completed sessions:
- Win/loss/tie counts (winner = higher `willingness + relevance - annoyance`)
- Mean scores per metric for AdaptAd vs baseline
- This is the data used for user study analysis in the paper

---

### `backend/api/routes_experiments.py`

**Purpose:** API access to the full experiment pipeline.

**`POST /api/experiments/run`** — Starts a background `run_full_experiment()` job. Returns `job_id` immediately.

**`GET /api/experiments/{job_id}`** — Polls job status and returns results when complete.

**`POST /api/experiments/sensitivity`** — Runs sensitivity analysis on the current best chromosome. Returns per-gene sensitivity scores showing which genes matter most.

---

### `backend/api/websocket.py`

**Purpose:** Real-time streaming of GA evolution progress to the browser via WebSocket.

**`WS /ws/evolve/{job_id}`**

**On connect:**
1. Looks up `job_id` in `_jobs` — sends error and closes if not found
2. Creates a `queue.Queue` and assigns it to `job["ws_queue"]`
3. **Replays history:** Iterates `job["history"]`, sends each as `{"type": "generation", "data": stats}`
4. **If job already completed:** Sends "converged" message immediately and closes — handles late-connecting browsers
5. **If job still running:** Enters polling loop

**In the polling loop:**
- Checks `ws_queue.get_nowait()` for new generation messages from the background thread
- Checks `websocket.receive_text()` with 0.1s timeout for client messages (pause/resume/stop)
- Breaks when job is completed and queue is empty
- `await asyncio.sleep(0.05)` — yields control to FastAPI's event loop every 50ms

**Thread safety:** The evolution runs in a background thread (synchronous), while the WebSocket handler runs in FastAPI's async event loop. The `queue.Queue` bridges these — the background thread calls `ws_queue.put_nowait()`, the async handler calls `ws_queue.get_nowait()`.

---

## 10. Test Suite

---

### `backend/tests/test_ga.py`

**Purpose:** 11 unit tests covering the GA and agent layer.

Tests include:
- `test_init_population`: 30 chromosomes, all genes in [0,1]
- `test_chromosome_to_vector_roundtrip`: `from_vector(to_vector(c)) == c`
- `test_uniform_crossover_genes_from_parents`: every child gene must come from one parent
- `test_mutation_stays_in_bounds`: mutated genes always in [0,1]
- `test_compute_diversity`: diverse population > 0, uniform population ≈ 0
- `test_fitness_evaluation_returns_float`: basic smoke test
- `test_fitness_bounds`: fitness always in [0,1]
- `test_user_advocate_score`: returns AgentScore with score in [0,1]
- `test_advertiser_advocate_score`: same
- `test_negotiate_returns_valid_decision`: decision is one of the 4 valid values
- `test_save_and_load_chromosome`: roundtrip through disk storage

### `backend/tests/test_api.py`

**Purpose:** 17 integration tests using FastAPI `TestClient` (synchronous test runner over the full ASGI app).

Tests include:
- `test_health_endpoint`: GET /api/health returns 200 with counts
- `test_list_users`: returns 200 users
- `test_get_user_by_id`: user 1 has expected fields
- `test_list_ads`: returns 80 ads
- `test_list_content`: returns 100 items
- `test_decide_single`: POST /api/decide returns valid decision
- `test_decide_invalid_user`: returns 404
- `test_batch_decide`: all 200 users get decisions
- `test_simulate_session`: session has decisions list
- `test_evolve_start`: returns job_id
- `test_evolve_status`: job exists after creation
- `test_ab_start`: returns two sessions X and Y
- `test_ab_rate_and_results`: full rating submission flow
- `test_chromosome_set`: POST /api/chromosome/set updates active chromosome

---

## 11. Frontend Layer

---

### `frontend/src/main.tsx`

**Purpose:** React 18 application entry point. Creates root with `ReactDOM.createRoot()`, wraps app in `React.StrictMode` (double-renders in dev to catch bugs), mounts to `#root` div in `index.html`.

---

### `frontend/src/App.tsx`

**Purpose:** Top-level routing. Uses React Router v6 with nested routes.

```
BrowserRouter
└── Routes
    └── Route path="/" element={<Layout>}         ← persistent shell
        ├── index → <Dashboard>                    ← /
        ├── "evolve" → <Evolution>                 ← /evolve
        ├── "decide" → <DecisionExplorer>          ← /decide
        ├── "simulate" → <SessionSimulator>        ← /simulate
        ├── "batch" → <BatchResults>               ← /batch
        ├── "ab-test" → <ABTesting>                ← /ab-test
        └── "settings" → <Settings>               ← /settings
```

Layout is always mounted — only the page content (`<Outlet />`) changes on navigation.

---

### `frontend/src/store/index.ts`

**Purpose:** Global application state using Zustand with localStorage persistence.

**State shape:**
```typescript
{
  chromosomeGenes: number[] | null,      // current best chromosome
  chromosomeFitness: number | null,      // its fitness
  activeJobId: string | null,            // currently running evolution job
  settings: {
    llmEnabled: boolean,
    llmProvider: 'groq' | 'gemini' | 'off',
    maxGenerations: number,              // default: 50
    populationSize: number,              // default: 30
    darkMode: boolean,
  },
  totalDecisions: number,                // count of decisions made this session
}
```

**Actions:** `setChromosome(genes, fitness)`, `setActiveJobId(id)`, `updateSettings(partial)`, `incrementDecisions()`

**Persistence:** Zustand `persist` middleware serializes state to `localStorage` under key `adaptad-store`. This means chromosomes and settings survive page refreshes — but also means stale job IDs persist across restarts (causing the "Job not found" bug that was fixed by clearing `activeJobId` on Evolution page mount).

---

### `frontend/src/api/client.ts`

**Purpose:** All API communication. Single Axios instance with `baseURL: '/api'` — proxied to `http://localhost:8000` by Vite.

**API helper groups:**

**`dataApi`** — `getUsers()`, `getUser(id)`, `getAds()`, `getContent()`, `health()`

**`evolveApi`**
- `start(maxGenerations, seed=random)` — POST /api/evolve with a **random seed each call** (bug fix applied here)
- `status(jobId)` — GET /api/evolve/{jobId}
- `stop(jobId)` — POST /api/evolve/{jobId}/stop
- `listChromosomes()` — GET /api/chromosomes
- `loadBest()` — POST /api/chromosome/load
- `setChromosome(genes)` — POST /api/chromosome/set

**`decideApi`** — `decide(params)`, `batch(params)`

**`simulateApi`** — `session(params)`

**`abApi`** — `start()`, `rate(sessionId, ratings)`, `results()`, `session(sessionId)`

**`experimentApi`** — `run(params)`, `status(jobId)`, `sensitivity(genes)`

---

### `frontend/src/hooks/useWebSocket.ts`

**Purpose:** Reusable React hook managing a WebSocket connection to the evolution server.

**Connection URL:** `ws://{window.location.host}/ws/evolve/{jobId}` — using the page's host means the Vite proxy transparently forwards to port 8000.

**`stoppedRef`:** A `useRef<boolean>` that prevents reconnection after receiving "converged" or "stopped" messages. When a new `jobId` is passed (new evolution run), the effect cleanup closes the old socket and the new effect resets `stoppedRef.current = false`.

**Auto-reconnect:** On WebSocket close (e.g., server restart), schedules reconnect after `reconnectDelayMs=3000ms` unless `stoppedRef.current = true`.

**Message handling:** Parses JSON, passes to `onMessage` callback. Sets `stoppedRef=true` on converged/stopped to stop reconnection.

**Returns:** `{connected: boolean, send: (msg) => void, disconnect: () => void}`

---

### Components

**`DecisionBadge.tsx`**
A small colored pill rendering an AdDecision value:
- SHOW → green background
- SOFTEN → yellow background
- DELAY → blue background
- SUPPRESS → red background
Used throughout the UI wherever a decision needs to be displayed.

**`FitnessChart.tsx`**
Recharts `LineChart` with two lines: `best_fitness` (indigo) and `avg_fitness` (gray). X-axis = generation number, Y-axis = fitness [0,1]. Animated line drawing as generations arrive via WebSocket. Shows real-time evolution progress on the Evolution page.

**`ChromosomeViz.tsx`**
Renders all 8 chromosome genes as labeled horizontal bars. Gene names displayed in human-readable form (e.g., "Fatigue Weight", "Relevance Weight"). Bar width = gene value × 100%. Color interpolates green (high) → red (low). Shows fitness value at the top if available.

**`FatigueMeter.tsx`**
A progress bar showing current fatigue level. Color thresholds:
- `fatigue < 0.40`: green — healthy
- `0.40 ≤ fatigue < 0.70`: yellow — elevated
- `fatigue ≥ 0.70`: red — high risk of force-suppress

**`AgentPanel.tsx`**
Side-by-side cards for User Advocate and Advertiser Advocate. Each card shows: score as a number and bar, reasoning text, expandable factors dict. Used on Decision Explorer page to explain why a particular decision was made.

**`SessionTimeline.tsx`**
Visual representation of a full session. Horizontal bar representing content duration. Colored tick marks at each break point — color matches the decision type. Hovering a tick shows minute, decision, and combined score. Used on Session Simulator page.

**`NavBar.tsx`**
Left sidebar with navigation links to all 7 pages. Highlights active route. Shows current chromosome fitness if available (e.g., "Best: 0.5039"). Fixed width, dark background.

**`Layout.tsx`**
Persistent shell component wrapping all pages. Contains `NavBar` on the left and `<Outlet />` for page content on the right. Applies dark theme class to the root element.

---

### Pages

**`Dashboard.tsx`**
Landing page showing system overview:
- Calls `GET /api/health` on mount, displays user/ad/content counts
- Shows current chromosome genes visualization if one is saved in store
- Quick-action cards linking to Evolution, Decision Explorer, Session Simulator

**`Evolution.tsx`**
Main evolution interface:
- **On mount:** Clears `activeJobId` from store (prevents stale job reconnection)
- **Start button:** POSTs to `/api/evolve` with random seed, stores returned `job_id`
- **WebSocket:** `useWebSocket(activeJobId)` connects and streams generation updates
- **Live chart:** FitnessChart updates in real time as generations arrive
- **Load Best button:** POSTs to `/api/chromosome/load`, updates store
- **Status display:** idle → starting → queued → running → converged

**`DecisionExplorer.tsx`**
Interactive single-decision tool:
- Dropdowns for user (from `/api/users`) and ad (from `/api/ads`)
- Sliders for time_of_day, season, session_fatigue, ads_shown
- Submit calls `POST /api/decide`
- Shows: DecisionBadge, AgentPanel (both scores), reasoning text
- Optional LLM reasoning toggle (from settings)

**`SessionSimulator.tsx`**
Full session walkthrough:
- User picker + Content picker
- Calls `POST /api/simulate/session`
- Shows SessionTimeline with all break points
- Table of each break: minute, ad category, decision, scores, fatigue
- Summary: total breaks, ads shown, final fatigue, decision distribution

**`BatchResults.tsx`**
Population-level view:
- Ad picker
- Calls `POST /api/decide/batch` (all 200 users × 1 ad)
- Pie chart of decision distribution (SHOW/SOFTEN/DELAY/SUPPRESS counts)
- Sortable table: user name, age group, decision, combined score
- Useful for showing how the policy treats different demographics

**`ABTesting.tsx`**
User study interface:
- Start button calls `POST /api/ab/start`
- Shows two sessions side-by-side: "Session X" and "Session Y"
- Each session shows timeline of decisions (user doesn't know which is AdaptAd)
- Rating sliders: Annoyance (1-5), Relevance (1-5), Willingness to continue (1-5)
- Submit calls `POST /api/ab/{id}/rate` twice (once for X, once for Y)
- Results panel shows aggregate AdaptAd vs baseline comparison

**`Settings.tsx`**
Configuration panel:
- Toggle: LLM enabled/disabled
- Dropdown: LLM provider (Groq / Gemini / Off)
- Slider: Max generations (10–200)
- Slider: Population size (10–100)
- All settings persisted via Zustand store to localStorage

---

## Summary: How It All Connects

```
Real Datasets (MovieLens/Avazu/Criteo)
        ↓ pipeline.py → grounding.py
Synthetic Data (generate.py / ad_inventory.py / content_library.py)
        ↓ routes_data.py (singletons)
Session Simulation (session.py + breaks.py + binge.py + fatigue.py)
        ↓ AdOpportunity objects
Two-Agent Pipeline (user_advocate.py + advertiser_advocate.py → negotiator.py)
        ↓ NegotiationResult
GA Fitness Evaluation (fitness.py) ← PURE MATH, uses agent scoring logic
        ↓ Chromosome fitness scores
GA Evolution (engine.py) → Chromosome
        ↓ saved to chromosomes/ via storage.py
REST API (FastAPI routes) ← uses evolved chromosome for real-time decisions
        ↑↓ WebSocket (websocket.py) for live evolution updates
React Frontend (7 pages, Zustand store, typed API client)
        ↓ results in browser
Experiment Pipeline (runner.py + ablations.py + metrics.py + stats.py)
        ↓ results/experiment_*.json
Database (database.py / aiosqlite) — logs all decisions and A/B ratings
```

---

*Document covers 46 Python source files and 20 TypeScript/TSX files — every file in the AdaptAd codebase.*
