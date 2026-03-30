# AdaptAd

Human-centered ad decision system for streaming platforms.

**Team:** Craig Roberts, Arzoo Jiwani, Vishwajeet Hogale
**Course:** CS6170 AI Capstone, Northeastern University
**Deadline:** April 13, 2026

---

## What it does

AdaptAd asks "should we even show an ad right now?" instead of "which ad gets more clicks?".
For every ad opportunity in a streaming session it picks one of four actions:

| Decision | Meaning |
|----------|---------|
| **SHOW** | Display the full ad. Conditions are favorable. |
| **SOFTEN** | Show a shorter version. Moderate fit. |
| **DELAY** | Wait for a better moment. Bad timing, good ad. |
| **SUPPRESS** | Skip entirely. Protect the viewer. |

A genetic algorithm evolves an 8-gene chromosome that controls decision thresholds.
Two agents (User Advocate and Advertiser Advocate) score each opportunity using the chromosome.
An LLM generates natural language explanations for every decision.

---

## Setup

### Requirements

- Python 3.10+
- Node 18+

### Install Python dependencies

```bash
pip install -r requirements.txt
```

Optional (for statistical tests):
```bash
pip install scipy
```

### Install frontend dependencies

```bash
cd frontend && npm install
```

### LLM keys (optional)

AdaptAd works without any LLM keys. If you want natural language explanations:

```bash
# Primary provider (14,400 req/day, free)
export GROQ_API_KEY=your_key_here

# Fallback provider (250 req/day, free)
export GEMINI_API_KEY=your_key_here
```

Get keys at console.groq.com and ai.google.dev. No credit card required.

---

## Running the system

### Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/api/health

### Start the frontend

```bash
cd frontend && npm run dev
```

App: http://localhost:5173

### Run tests

```bash
pytest backend/tests/ -v
```

---

## Real datasets (optional)

The system works fully without any downloaded datasets.
If you want to ground the synthetic data in real distributions:

### MovieLens 25M

```bash
mkdir -p datasets/raw/ml-25m
# Download from http://files.grouplens.org/datasets/movielens/ml-25m.zip
# Extract movies.csv and ratings.csv into datasets/raw/ml-25m/
```

### Criteo Display Advertising

```bash
mkdir -p datasets/raw/criteo
# Download train.txt from https://www.kaggle.com/c/criteo-display-ad-challenge/data
# Place at datasets/raw/criteo/train.txt
```

### Avazu CTR Prediction

```bash
mkdir -p datasets/raw/avazu
# Download from https://www.kaggle.com/datasets/gauravduttakiit/avazu-ctr-prediction-with-random-50k-rows
# Place train.csv at datasets/raw/avazu/train.csv
```

Then run the pipeline:

```bash
python3 -m backend.data.pipeline
```

This extracts distributions to `datasets/processed/distributions.json` and the
synthetic data generator picks them up automatically.

---

## Running experiments

Quick test (5 runs, 10 generations):
```bash
python3 -c "from backend.experiments.runner import run_full_experiment; run_full_experiment(num_runs=5, max_generations=10)"
```

Full paper run (30 runs, 50 generations):
```bash
python3 -c "from backend.experiments.runner import run_full_experiment; run_full_experiment(num_runs=30, max_generations=50)"
```

Results are saved to `results/experiment_{timestamp}.json`.

---

## Architecture

```
Request -> FastAPI -> Agent System -> Decision
                           |
                    User Advocate (math scoring)
                    Advertiser Advocate (math scoring)
                    Negotiator (threshold mapping)
                    LLM Explain (Groq/Gemini/template)

GA Evolution:
  Population (30 chromosomes) -> Fitness Eval (pure NumPy) ->
  Tournament Selection -> Crossover -> Mutation -> Next Gen
```

### 8-gene chromosome

All 8 genes are active in the fitness function — no dead genes.

| Gene | Controls | Effect when high |
|------|---------|-----------------|
| fatigue_weight | Sensitivity to session fatigue | More conservative — suppresses ads for tired users |
| relevance_weight | Importance of ad-interest match | Only shows ads to users whose interests align |
| timing_weight | Importance of time-of-day alignment | Favors preferred viewing times |
| frequency_threshold | Base bar to show any ad (show_thresh range: 0.35–0.65) | Stricter about showing ads at all |
| delay_probability | Width of the DELAY zone below the soften threshold | Prefers delaying over suppressing when borderline |
| soften_threshold | Width of the SOFTEN zone below the show threshold | Prefers shorter ads over full skip when conditions are moderate |
| category_boost | Advertiser value weight for category relevance | Rewards relevant ads more heavily for advertisers |
| session_depth_factor | Penalty growth as ads_shown increases | Increasingly cautious deep into a session |

`UserProfile.ad_tolerance` is also incorporated: users with high inherent ad tolerance receive higher satisfaction scores for the same SHOW decision, creating realistic heterogeneity across the 200-user population.

---

## Hypotheses

- **H1:** Evolved policy fitness > 0.58 (vs baselines: always-show ~0.49, random ~0.50, freq-cap ~0.48)
- **H2:** Post-session fatigue < 0.45, ad relevance > 65%
- **H3:** Strategy diversity index (Shannon entropy) > 0.15

Statistical tests: Wilcoxon signed-rank with Holm-Bonferroni correction.

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/evolve | Start GA evolution |
| GET | /api/evolve/{job_id} | Evolution status |
| WS | /ws/evolve/{job_id} | Live generation updates |
| POST | /api/decide | Single ad decision |
| POST | /api/decide/batch | All 200 users at once |
| POST | /api/simulate/session | Full session simulation |
| POST | /api/ab/start | Start A/B test |
| POST | /api/ab/{id}/rate | Submit ratings |
| GET | /api/ab/results | Aggregate A/B results |
| POST | /api/experiments/run | Full experiment pipeline |
| GET | /api/health | System health |

---

## Citations

- Harper and Konstan. 2015. The MovieLens Datasets. ACM TiiS 5(4).
- Criteo Labs. 2014. Kaggle Display Advertising Challenge Dataset.
- Avazu. 2014. Click-Through Rate Prediction. Kaggle Competition.
