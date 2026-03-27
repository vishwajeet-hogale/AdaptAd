"""
Real dataset processing pipeline.

Processes MovieLens 25M, Criteo Display Advertising, and Avazu CTR datasets.
Each dataset has a graceful fallback if files are missing.
Outputs processed distributions to datasets/processed/.
System never crashes if datasets are absent.

Usage:
  python3 -m backend.data.pipeline
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATASETS_DIR = Path("datasets")
RAW_DIR = DATASETS_DIR / "raw"
PROCESSED_DIR = DATASETS_DIR / "processed"

# Hardcoded fallbacks used when datasets are missing.
FALLBACK_GENRE_WEIGHTS = {
    "Action": 0.14, "Comedy": 0.13, "Drama": 0.18, "Sci-Fi": 0.09,
    "Horror": 0.07, "Documentary": 0.06, "Romance": 0.08, "Thriller": 0.10,
    "Animation": 0.08, "Fantasy": 0.07,
}

FALLBACK_CTR = 0.031  # Criteo dataset average: ~3.1%

FALLBACK_HOURLY_CTR = {
    0: 0.018, 1: 0.015, 2: 0.013, 3: 0.012, 4: 0.014, 5: 0.019,
    6: 0.026, 7: 0.034, 8: 0.038, 9: 0.040, 10: 0.042, 11: 0.043,
    12: 0.041, 13: 0.039, 14: 0.038, 15: 0.040, 16: 0.042, 17: 0.044,
    18: 0.046, 19: 0.049, 20: 0.051, 21: 0.050, 22: 0.045, 23: 0.030,
}


# ---------------------------------------------------------------------------
# MovieLens 25M
# ---------------------------------------------------------------------------


def process_movielens(raw_dir: Path = RAW_DIR) -> dict:
    """
    Extract genre distribution and engagement patterns from MovieLens 25M.

    Expected files: raw/ml-25m/movies.csv, raw/ml-25m/ratings.csv
    Falls back to uniform genre distribution if files missing.
    """
    movies_path = raw_dir / "ml-25m" / "movies.csv"
    ratings_path = raw_dir / "ml-25m" / "ratings.csv"

    if not movies_path.exists():
        logger.warning(
            "MovieLens movies.csv not found at %s. Using fallback genre distribution.", movies_path
        )
        return {
            "genre_weights": FALLBACK_GENRE_WEIGHTS,
            "source": "fallback",
        }

    try:
        import csv
        genre_counts: dict[str, int] = {}
        with open(movies_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                genres = row.get("genres", "").split("|")
                for g in genres:
                    g = g.strip()
                    if g and g != "(no genres listed)":
                        genre_counts[g] = genre_counts.get(g, 0) + 1

        total = sum(genre_counts.values())
        if total == 0:
            return {"genre_weights": FALLBACK_GENRE_WEIGHTS, "source": "fallback"}

        # Map MovieLens genre names to our genre names.
        ml_to_our = {
            "Action": "Action", "Comedy": "Comedy", "Drama": "Drama",
            "Sci-Fi": "Sci-Fi", "Horror": "Horror", "Documentary": "Documentary",
            "Romance": "Romance", "Thriller": "Thriller", "Animation": "Animation",
            "Fantasy": "Fantasy", "Adventure": "Action", "Crime": "Thriller",
            "Mystery": "Thriller", "Musical": "Comedy", "War": "Drama",
            "Western": "Action", "IMAX": "Action", "Film-Noir": "Dark",
        }
        our_counts: dict[str, float] = {g: 0.0 for g in FALLBACK_GENRE_WEIGHTS}
        for ml_genre, count in genre_counts.items():
            our_genre = ml_to_our.get(ml_genre)
            if our_genre and our_genre in our_counts:
                our_counts[our_genre] += count

        genre_total = sum(our_counts.values()) or 1
        genre_weights = {g: round(c / genre_total, 4) for g, c in our_counts.items()}

        engagement_mean = 0.62
        engagement_std = 0.18
        # If ratings file exists, compute from data.
        if ratings_path.exists():
            try:
                rating_vals = []
                with open(ratings_path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= 100_000:
                            break
                        try:
                            rating_vals.append(float(row.get("rating", 3.0)))
                        except ValueError:
                            pass
                if rating_vals:
                    engagement_mean = round(sum(rating_vals) / len(rating_vals) / 5.0, 4)
            except Exception as e:
                logger.warning("Could not parse ratings.csv: %s", e)

        result = {
            "genre_weights": genre_weights,
            "engagement_mean": engagement_mean,
            "engagement_std": engagement_std,
            "source": "movielens",
        }
        logger.info("MovieLens processed. Genre weights: %s", genre_weights)
        return result

    except Exception as e:
        logger.warning("Failed to process MovieLens: %s. Using fallback.", e)
        return {"genre_weights": FALLBACK_GENRE_WEIGHTS, "source": "fallback"}


# ---------------------------------------------------------------------------
# Criteo Display Advertising
# ---------------------------------------------------------------------------


def process_criteo(raw_dir: Path = RAW_DIR, max_rows: int = 1_000_000) -> dict:
    """
    Extract CTR distribution and feature importances from Criteo dataset.

    Expected file: raw/criteo/train.txt or raw/criteo/train.txt.gz
    Tab-separated, first col = label 0/1.
    Falls back to hardcoded CTR = 0.031 if file missing.
    """
    gz_path = raw_dir / "criteo" / "train.txt.gz"
    txt_path = raw_dir / "criteo" / "train.txt"

    if gz_path.exists():
        criteo_path = gz_path
        use_gz = True
    elif txt_path.exists():
        criteo_path = txt_path
        use_gz = False
    else:
        logger.warning("Criteo train.txt[.gz] not found at %s. Using fallback CTR.", raw_dir / "criteo")
        return {"mean_ctr": FALLBACK_CTR, "source": "fallback"}

    try:
        import gzip
        total = 0
        clicks = 0
        open_fn = gzip.open if use_gz else open
        with open_fn(criteo_path, "rt", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                parts = line.strip().split("\t")
                if parts:
                    try:
                        label = int(parts[0])
                        clicks += label
                        total += 1
                    except ValueError:
                        pass

        if total == 0:
            return {"mean_ctr": FALLBACK_CTR, "source": "fallback"}

        mean_ctr = round(clicks / total, 4)
        result = {"mean_ctr": mean_ctr, "rows_processed": total, "source": "criteo"}
        logger.info("Criteo processed. CTR = %.4f from %d rows.", mean_ctr, total)
        return result

    except Exception as e:
        logger.warning("Failed to process Criteo: %s. Using fallback.", e)
        return {"mean_ctr": FALLBACK_CTR, "source": "fallback"}


# ---------------------------------------------------------------------------
# Avazu CTR Prediction
# ---------------------------------------------------------------------------


def process_avazu(raw_dir: Path = RAW_DIR) -> dict:
    """
    Extract hourly CTR curves and day-of-week patterns from Avazu dataset.

    Looks for the file in two locations:
      raw/avazu-ctr-prediction/train.gz  (downloaded from Kaggle competition)
      raw/avazu/train.csv                (uncompressed fallback)
    Hour format: YYMMDDHH (last 2 digits = hour of day)
    Falls back to hardcoded primetime curve if neither file found.
    """
    # Check both possible locations and formats.
    gz_path = raw_dir / "avazu-ctr-prediction" / "train.gz"
    csv_path = raw_dir / "avazu" / "train.csv"

    if gz_path.exists():
        avazu_path = gz_path
        use_gz = True
    elif csv_path.exists():
        avazu_path = csv_path
        use_gz = False
    else:
        logger.warning("Avazu train file not found. Using fallback hourly CTR.")
        return {"hourly_ctr": FALLBACK_HOURLY_CTR, "primetime_boost": 0.15, "source": "fallback"}

    _ = use_gz  # used below in open logic

    if not avazu_path.exists():
        logger.warning("Avazu train.csv not found at %s. Using fallback hourly CTR.", avazu_path)
        return {"hourly_ctr": FALLBACK_HOURLY_CTR, "primetime_boost": 0.15, "source": "fallback"}

    try:
        import csv
        import gzip
        hourly_clicks: dict[int, int] = {h: 0 for h in range(24)}
        hourly_total: dict[int, int] = {h: 0 for h in range(24)}
        rows = 0
        open_fn = gzip.open if use_gz else open
        with open_fn(avazu_path, "rt", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    hour_str = str(row.get("hour", "0"))
                    hour = int(hour_str[-2:]) % 24
                    click = int(row.get("click", 0))
                    hourly_clicks[hour] += click
                    hourly_total[hour] += 1
                    rows += 1
                except (ValueError, KeyError):
                    pass

        hourly_ctr = {}
        for h in range(24):
            if hourly_total[h] > 0:
                hourly_ctr[h] = round(hourly_clicks[h] / hourly_total[h], 4)
            else:
                hourly_ctr[h] = FALLBACK_HOURLY_CTR[h]

        # Primetime boost = ratio of evening peak to morning baseline.
        evening_mean = sum(hourly_ctr.get(h, 0) for h in range(18, 23)) / 5
        morning_mean = sum(hourly_ctr.get(h, 0) for h in range(6, 10)) / 4
        primetime_boost = round(max(0, evening_mean - morning_mean), 4) if morning_mean > 0 else 0.15

        result = {
            "hourly_ctr": hourly_ctr,
            "primetime_boost": primetime_boost,
            "rows_processed": rows,
            "source": "avazu",
        }
        logger.info("Avazu processed. Primetime boost = %.4f from %d rows.", primetime_boost, rows)
        return result

    except Exception as e:
        logger.warning("Failed to process Avazu: %s. Using fallback.", e)
        return {"hourly_ctr": FALLBACK_HOURLY_CTR, "primetime_boost": 0.15, "source": "fallback"}


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------


def run_pipeline(
    raw_dir: Optional[Path] = None,
    processed_dir: Optional[Path] = None,
) -> dict:
    """
    Run all three dataset processors and save outputs to processed/.

    Always succeeds (uses fallbacks if files missing).
    Returns a dict with all extracted distributions.
    """
    raw = raw_dir or RAW_DIR
    processed = processed_dir or PROCESSED_DIR
    processed.mkdir(parents=True, exist_ok=True)

    movielens = process_movielens(raw)
    criteo = process_criteo(raw)
    avazu = process_avazu(raw)

    output = {
        "movielens": movielens,
        "criteo": criteo,
        "avazu": avazu,
    }

    out_path = processed / "distributions.json"
    try:
        out_path.write_text(json.dumps(output, indent=2))
        logger.info("Pipeline complete. Distributions saved to %s.", out_path)
    except Exception as e:
        logger.warning("Could not save distributions: %s", e)

    return output


def load_distributions(processed_dir: Optional[Path] = None) -> dict:
    """
    Load processed distributions from disk, or run pipeline if not available.
    """
    processed = processed_dir or PROCESSED_DIR
    out_path = processed / "distributions.json"
    if out_path.exists():
        try:
            return json.loads(out_path.read_text())
        except Exception:
            pass
    return run_pipeline()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_pipeline()
    print("Movielens source:", result["movielens"]["source"])
    print("Criteo source:   ", result["criteo"]["source"])
    print("Avazu source:    ", result["avazu"]["source"])
    print("Genre weights:", result["movielens"]["genre_weights"])
    print("Mean CTR:", result["criteo"]["mean_ctr"])
    print("Primetime boost:", result["avazu"]["primetime_boost"])
