# AdaptAd Architecture

CS6170 AI Capstone | Northeastern University
Team: Craig Roberts, Arzoo Jiwani, Vishwajeet Hogale

---

## System Overview

AdaptAd decides whether to show, soften, delay, or suppress an ad during a streaming session. Every decision is explained. No black box.

```
User watches content
        |
        v
Natural break point reached
        |
        v
AdOpportunity created  <-- user profile + ad candidate + session context
        |
        v
+---------------------------------------+
|         Two-Agent Decision System     |
|                                       |
|  User Advocate      Advertiser Adv.   |
|  (protect viewer)   (maximize value)  |
|       |                   |           |
|       +--------+----------+           |
|                |                      |
|           Negotiator                  |
|      (weighted combination)           |
+---------------------------------------+
        |
        v
   SHOW / SOFTEN / DELAY / SUPPRESS
        |
        v
   LLM Explanation (Groq -> Gemini -> template)
        |
        v
   Decision logged to SQLite
```

---

## Full System Flowchart

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                               │
│                                                                 │
│  MovieLens 25M          Avazu (40M rows)     Criteo (fallback)  │
│  movies.csv             train.gz             CTR = 3.1%         │
│  ratings.csv                                                    │
│       │                      │                    │             │
│       v                      v                    v             │
│  pipeline.py ──────────────────────────────────────────────>   │
│  distributions.json                                             │
│  (genre weights, engagement mean, hourly CTR, primetime boost)  │
│       │                                                         │
│       v                                                         │
│  grounding.py                                                   │
│  get_grounded_engagement_stats()  -> generate.py               │
│  get_content_preferences_from_movielens() -> generate.py       │
│  get_primetime_boost()            -> advertiser_advocate.py    │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                    SYNTHETIC DATA GENERATION                    │
│                                                                 │
│  generate.py          content_library.py     ad_inventory.py   │
│  200 UserProfiles     100 ContentItems       80 AdCandidates    │
│                                                                 │
│  Each UserProfile has:        Each ContentItem has:            │
│  - age_group                  - genre + mood                   │
│  - interests (2-4 categories) - duration_minutes               │
│  - fatigue_level (base)       - intensity_curve (per-minute)   │
│  - engagement_score           - natural_break_points           │
│  - binge_tendency             - never first/last 5 min         │
│  - content_preferences        Each AdCandidate has:            │
│    (MovieLens-grounded)       - category (8 types)             │
│  - preferred_watch_time       - duration (15/30/45/60s)        │
│                               - seasonal_affinity              │
│                               - target_demographics            │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                   GENETIC ALGORITHM (Phase 1)                   │
│                                                                 │
│  Population: 30 Chromosomes (each = 8 genes in [0,1])          │
│                                                                 │
│  Gene 1: fatigue_weight       Gene 5: delay_probability        │
│  Gene 2: relevance_weight     Gene 6: soften_threshold         │
│  Gene 3: timing_weight        Gene 7: category_boost           │
│  Gene 4: frequency_threshold  Gene 8: session_depth_factor     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              EVOLUTION LOOP (max 50 gen)             │      │
│  │                                                      │      │
│  │  Initialize random population (30 chromosomes)       │      │
│  │          │                                           │      │
│  │          v                                           │      │
│  │  Fitness Evaluation (PURE NUMPY, no LLM)             │      │
│  │  - Sample 5 scenarios per user x 200 users = 1000   │      │
│  │  - Score each (decision, context) pair              │      │
│  │  - fitness = 0.6 * satisfaction + 0.4 * revenue     │      │
│  │          │                                           │      │
│  │          v                                           │      │
│  │  Elite Preservation (top 20% survive unchanged)      │      │
│  │          │                                           │      │
│  │          v                                           │      │
│  │  Tournament Selection (3-way tournament)             │      │
│  │          │                                           │      │
│  │          v                                           │      │
│  │  Uniform Crossover (each gene 50/50 from A or B)    │      │
│  │          │                                           │      │
│  │          v                                           │      │
│  │  Gaussian Mutation (15% per gene, strength 0.3)     │      │
│  │          │                                           │      │
│  │          v                                           │      │
│  │  Convergence check (delta < 0.001 over 10 gen)      │      │
│  │          │                                           │      │
│  │    converged? ──yes──> Save best chromosome         │      │
│  │          │             to chromosomes/              │      │
│  │          no                                         │      │
│  │          │                                           │      │
│  │    stuck 20 gen? ──yes──> Force restart             │      │
│  │          │                                           │      │
│  │          └──────────────> next generation           │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  WebSocket streams generation stats to frontend in real time   │
└─────────────────────────────────────────────────────────────────┘
        │
        │  best chromosome (8 genes)
        v
┌─────────────────────────────────────────────────────────────────┐
│                  SESSION SIMULATION (Phase 2)                   │
│                                                                 │
│  simulate_session()                                             │
│                                                                 │
│  User selects content                                           │
│          │                                                      │
│          v                                                      │
│  Identify natural break points                                  │
│  breaks.py: score by intensity curve, enforce min gap          │
│          │                                                      │
│          v                                                      │
│  For each break point:                                          │
│    1. Snapshot SessionContext (time, season, ads_shown, fatigue)│
│    2. Pick ad candidate from pool                               │
│    3. Create AdOpportunity                                      │
│    4. Run decision pipeline (see below)                         │
│    5. apply_decision() -> update running context               │
│       - ads_shown_this_session += 1 (if SHOW or SOFTEN)        │
│       - fatigue += increment (SHOW=+0.10, SOFTEN=+0.05,        │
│                               DELAY=+0.02, SUPPRESS=+0.00)     │
│       - fatigue -= 0.01 per ad-free minute                     │
│       - fatigue clamped to [user.base_fatigue, 1.0]            │
│          │                                                      │
│          v                                                      │
│  Binge detection (binge.py)                                     │
│  is_binging = queue >= 2 AND episodes_watched >= 1             │
│              AND binge_tendency > 0.5                          │
│  Effect: raise show_threshold, increase fatigue sensitivity    │
│          │                                                      │
│          v                                                      │
│  Session ends when fatigue > 0.9 or content finishes           │
└─────────────────────────────────────────────────────────────────┘
        │
        │  AdOpportunity (user + ad + session_context)
        v
┌─────────────────────────────────────────────────────────────────┐
│               TWO-AGENT DECISION PIPELINE (Phase 3)             │
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────────────┐    │
│  │    USER ADVOCATE    │    │    ADVERTISER ADVOCATE      │    │
│  │  (viewer protection)│    │    (advertiser value)       │    │
│  │                     │    │                             │    │
│  │  No fixed base —    │    │  No fixed base —            │    │
│  │  genes drive range  │    │  genes drive range          │    │
│  │                     │    │                             │    │
│  │  + ad_tolerance*0.2 │    │  + category_boost*          │    │
│  │  + mood_bonus       │    │    (0.50 if relevant,       │    │
│  │  + relevance_weight │    │     0.08 if not)            │    │
│  │    *(0.40/0.05)     │    │  + engagement*0.25          │    │
│  │  + timing_weight    │    │  + primetime (Avazu)        │    │
│  │    *(0.18 if match) │    │  + priority_factor          │    │
│  │  - fatigue_weight   │    │  + seasonal_affinity*0.12   │    │
│  │    *fatigue*0.55    │    │  + demo_match*0.08          │    │
│  │  - session_depth_   │    │                             │    │
│  │    factor*(0/0.14/  │    │  score in [0, 1]            │    │
│  │    0.28)            │    │                             │    │
│  │  - intensity_penalty│    │                             │    │
│  │  - binge_penalty    │    │                             │    │
│  │                     │    │                             │    │
│  │  score in [0, 1]    │    │                             │    │
│  └──────────┬──────────┘    └─────────────┬───────────────┘    │
│             │  (run in parallel)           │                    │
│             └──────────────┬──────────────┘                    │
│                            v                                    │
│                      NEGOTIATOR                                 │
│                                                                 │
│  combined = UA * 0.55 + ADV * 0.45                             │
│                                                                 │
│  show_thresh    = 0.35 + frequency_threshold * 0.30            │
│  soften_thresh  = show_thresh - 0.06 - soften_threshold * 0.14 │
│  delay_thresh   = soften_thresh - 0.04 - delay_probability*0.10│
│                                                                 │
│  combined >= show_thresh   -> SHOW                             │
│  combined >= soften_thresh -> SOFTEN                           │
│  combined >= delay_thresh  -> DELAY                            │
│  else                      -> SUPPRESS                         │
│                                                                 │
│  Override: fatigue > 0.85  -> always SUPPRESS                  │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                    LLM EXPLANATION                              │
│                                                                 │
│  Input: decision + both agent scores + factor breakdown        │
│                                                                 │
│  Try Groq (llama-3.3-70b)  <-- 14,400 req/day, 5s timeout     │
│          │ fail                                                 │
│          v                                                      │
│  Try Gemini (gemini-2.5-flash) <-- 250 req/day, 5s timeout    │
│          │ fail                                                 │
│          v                                                      │
│  Template fallback                                              │
│  "Score: X. Key factors: fatigue=-0.12, relevance=+0.18"      │
│                                                                 │
│  LLM NEVER affects scores or decisions.                        │
│  Identical prompts are cached by MD5 hash.                     │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                      EXPERIMENT PIPELINE                        │
│                                                                 │
│  run_full_experiment(num_runs=30, max_generations=50)          │
│                                                                 │
│  1. Evaluate 3 baselines (same users, same content)            │
│     - always_show:   fitness 0.512                             │
│     - random:        fitness 0.473                             │
│     - frequency_cap: fitness 0.462                             │
│                                                                 │
│  2. Run N independent GA evolutions                            │
│     Each run: fresh random population -> evolve -> best chrom  │
│                                                                 │
│  3. Evaluate evolved policy against all users                  │
│                                                                 │
│  4. Run 5 ablation conditions                                  │
│     - full system (GA + two agents)                            │
│     - GA only (equal agent weights)                            │
│     - agents without GA (default chromosome)                   │
│     - user advocate only                                       │
│     - advertiser advocate only                                 │
│                                                                 │
│  5. Compute hypotheses                                         │
│     H1: mean fitness > 0.58                                    │
│     H2: mean fatigue < 0.45, mean relevance > 65%             │
│     H3: diversity index (Shannon entropy) > 0.15              │
│                                                                 │
│  6. Statistical tests                                          │
│     Wilcoxon signed-rank (one-sample + pairwise)               │
│     Holm-Bonferroni correction for multiple comparisons        │
│                                                                 │
│  7. Save results to results/experiment_{timestamp}.json        │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                         API LAYER                               │
│                                                                 │
│  FastAPI (port 8000)                                            │
│                                                                 │
│  POST /api/evolve           Start GA evolution (background)    │
│  GET  /api/evolve/{id}      Evolution status + history         │
│  WS   /ws/evolve/{id}       Live generation stats              │
│  POST /api/chromosome/load  Load pre-trained chromosome        │
│  GET  /api/chromosomes      List saved chromosomes             │
│                                                                 │
│  POST /api/decide           Single decision (1 user + 1 ad)   │
│  POST /api/decide/batch     All 200 users vs 1 ad              │
│                                                                 │
│  POST /api/simulate/session Full session simulation            │
│                                                                 │
│  POST /api/ab/start         New A/B test session               │
│  POST /api/ab/{id}/rate     Submit participant ratings         │
│  GET  /api/ab/results       Aggregate A/B results              │
│                                                                 │
│  POST /api/experiments/run  Full experiment pipeline           │
│  GET  /api/health           System health check                │
│                                                                 │
│  SQLite (aiosqlite): decisions, ab_sessions, ab_ratings        │
└─────────────────────────────────────────────────────────────────┘
        │
        v
┌─────────────────────────────────────────────────────────────────┐
│                      REACT FRONTEND                             │
│                                                                 │
│  Vite + React 18 + TypeScript + Tailwind + Zustand + Recharts  │
│                                                                 │
│  /            Dashboard      Overview cards, quick actions     │
│  /evolve      Evolution      Live fitness chart via WebSocket  │
│                              Chromosome gene bars              │
│  /decide      Decision       User + ad + context selectors     │
│  Explorer                    Agent score panels + reasoning    │
│  /simulate    Simulator      Animated timeline, fatigue meter  │
│  /batch       Batch          Pie chart, per-user table         │
│  /ab-test     A/B Test       Side-by-side sessions + ratings   │
│  /settings    Settings       GA params, LLM toggle             │
│                                                                 │
│  Color coding everywhere:                                       │
│  green = SHOW   amber = SOFTEN   orange = DELAY   red = SUPPRESS│
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Summary

```
MovieLens + Avazu
      |
      v
distributions.json
      |
      +---> engagement_mean (0.72) ──> UserProfile.engagement_score
      |
      +---> genre_weights ──────────> UserProfile.content_preferences
      |
      +---> primetime_boost ────────> Advertiser Advocate scoring
      |
      +---> hourly_ctr ─────────────> (available for future use)

Chromosome (8 genes from GA) — all genes active
      |
      +---> fatigue_weight ─────────> UA: penalty = fatigue_weight * session_fatigue * 0.55
      +---> relevance_weight ───────> UA: bonus  = relevance_weight * (0.40 if relevant else 0.05)
      +---> timing_weight ──────────> UA: bonus  = timing_weight * (0.18 if time_match else 0)
      +---> frequency_threshold ────> Negotiator: show_thresh = 0.35 + gene * 0.30
      +---> delay_probability ──────> Negotiator: delay zone width = 0.04 + gene * 0.10
      +---> soften_threshold ───────> Negotiator: soften zone width = 0.06 + gene * 0.14
      +---> category_boost ─────────> ADV: boost = category_boost * (0.50 if relevant else 0.08)
      +---> session_depth_factor ───> UA: penalty scales with ads_shown (0 / 0.14 / 0.28)

UserProfile.ad_tolerance ────────────> UA: tolerance_base = ad_tolerance * 0.20
                                        Outcomes: SHOW satisfaction += clip(tolerance-0.5, 0, 0.15)
```

---

## Fatigue State Machine

```
Decision made at break point
          |
          v
fatigue += increment
  SHOW     +0.10
  SOFTEN   +0.05
  DELAY    +0.02
  SUPPRESS +0.00
          |
          v
fatigue -= 0.01 per ad-free minute
          |
          v
clamp to [user.base_fatigue, 1.0]
          |
     fatigue > 0.85?
          |
    yes ──┼──> Force SUPPRESS for rest of session
          |
    no ───┼──> fatigue > 0.70?
          |
    yes ──┼──> Apply -0.15 penalty to show/soften scores
          |
    no ───┼──> Normal scoring
```

---

## LangGraph Graphs

```
EVOLUTION GRAPH
START --> init_ga --> evolve --> [converged?] --> yes --> END
                        ^                |
                        |_____ no ________|

DECISION GRAPH
                +---> user_advocate ────┐
START ──────────+                       +--> negotiate --> llm_explain --> END
                +---> adv_advocate ─────┘
```

---

## File Structure

```
adaptad/
├── backend/
│   ├── main.py                    FastAPI entry point
│   ├── config.py                  All tunable parameters
│   ├── state.py                   All Pydantic data models
│   ├── agents/
│   │   ├── user_advocate.py       Viewer-side math scoring
│   │   ├── advertiser_advocate.py Advertiser-side math scoring
│   │   ├── negotiator.py          Score combination -> decision
│   │   └── llm_reasoning.py       Groq/Gemini/template fallback
│   ├── api/
│   │   ├── routes_evolve.py       GA evolution endpoints
│   │   ├── routes_decide.py       Decision endpoints
│   │   ├── routes_simulate.py     Session simulation endpoints
│   │   ├── routes_ab.py           A/B testing endpoints
│   │   ├── routes_experiments.py  Experiment runner endpoints
│   │   ├── routes_data.py         Data endpoints
│   │   └── websocket.py           Live evolution WebSocket
│   ├── data/
│   │   ├── pipeline.py            MovieLens/Avazu/Criteo processing
│   │   ├── grounding.py           Real data -> generator bridge
│   │   ├── generate.py            200 synthetic users
│   │   ├── content_library.py     100 content items
│   │   ├── ad_inventory.py        80 ads
│   │   └── constants.py           Shared constants
│   ├── db/
│   │   └── database.py            SQLite schema + helpers
│   ├── experiments/
│   │   ├── runner.py              Full experiment pipeline
│   │   ├── ablations.py           5 ablation conditions
│   │   ├── metrics.py             H1/H2/H3 computation
│   │   └── stats.py               Wilcoxon + Holm-Bonferroni
│   ├── ga/
│   │   ├── engine.py              GAEngine class
│   │   ├── fitness.py             Vectorized NumPy fitness
│   │   └── storage.py             JSON chromosome save/load
│   ├── graph/
│   │   └── builder.py             LangGraph evolution + decision graphs
│   ├── simulation/
│   │   ├── engine.py              Policy evaluator + baselines
│   │   ├── session.py             Session simulator
│   │   ├── breaks.py              Break point scoring
│   │   ├── binge.py               Binge detection
│   │   └── fatigue.py             Fatigue state machine
│   └── tests/
│       ├── test_ga.py             11 GA + agent tests
│       └── test_api.py            17 API integration tests
├── frontend/
│   └── src/
│       ├── api/client.ts          Axios + typed API helpers
│       ├── store/index.ts         Zustand global state
│       ├── hooks/useWebSocket.ts  Live evolution hook
│       ├── components/            8 reusable components
│       └── pages/                 7 pages
├── datasets/
│   ├── raw/
│   │   ├── ml-25m/                MovieLens 25M (movies.csv, ratings.csv)
│   │   └── avazu-ctr-prediction/  Avazu (train.gz, 40M rows)
│   └── processed/
│       └── distributions.json     Extracted real-data distributions
├── chromosomes/                   Saved evolved chromosomes (JSON)
├── results/                       Experiment output (JSON)
├── requirements.txt
├── README.md
├── ARCHITECTURE.md                This file
└── PROJECT_STATUS.txt             Plain-English build log
```
