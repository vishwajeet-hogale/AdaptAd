"""
A/B testing routes.

POST /api/ab/start              Create a new A/B test session.
POST /api/ab/{session_id}/rate  Submit ratings for one session label.
GET  /api/ab/results            All A/B test results with aggregate stats.
GET  /api/ab/{session_id}       Details for one A/B session.
"""

import random
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from ..agents.user_advocate import score_user_advocate
from ..agents.advertiser_advocate import score_advertiser_advocate
from ..agents.negotiator import negotiate
from ..simulation.session import simulate_session, apply_decision
from ..simulation.fatigue import should_force_suppress
from ..state import AdDecision, Chromosome, ContentMood, ContentItem, Season, TimeOfDay, UserProfile
from ..data.content_library import GENRE_MOODS, _generate_intensity_curve, _natural_break_points, pick_content_for_user
from ..db.database import save_ab_session_sync, save_ab_rating_sync, get_ab_history_sync
from .routes_data import get_users, get_ads, get_content
from .routes_decide import get_chromosome

router = APIRouter(prefix="/api/ab", tags=["ab"])

# In-memory store for A/B sessions and ratings.
_ab_sessions: dict[str, dict] = {}
_ab_ratings: list[dict] = []


class ABStartRequest(BaseModel):
    user_id: Optional[int] = None       # If None, pick random user.
    content_id: Optional[int] = None    # If None, pick random content.
    seed: Optional[int] = None


class CustomABRequest(BaseModel):
    """Run an A/B test using a real person's profile and a real show they're watching."""
    person_name: str = "Anonymous"
    age_group: str = "25-34"
    country: str = ""
    interests: list[str] = ["tech", "travel"]
    ad_tolerance: float = 0.5
    show_title: str = "My Show"
    show_genre: str = "Drama"
    show_duration_minutes: int = 45
    is_series: bool = False
    seed: Optional[int] = None

    @field_validator("age_group")
    @classmethod
    def validate_age_group(cls, v: str) -> str:
        valid = {"13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"}
        if v not in valid:
            raise ValueError(f"age_group must be one of {valid}")
        return v

    @field_validator("ad_tolerance")
    @classmethod
    def clamp_tolerance(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @field_validator("show_duration_minutes")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        return max(10, min(240, v))


class ABRatingRequest(BaseModel):
    session_label: str                  # "X" or "Y" as shown to participant.
    annoyance: int                      # 1-5
    relevance: int                      # 1-5
    willingness: int                    # 1-5
    notes: Optional[str] = None

    @field_validator("annoyance", "relevance", "willingness")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        return v


def _run_adaptad_session(user, content, ads, chromosome, seed) -> list[dict]:
    """Run AdaptAd policy and return decision records."""
    opportunities, _ = simulate_session(
        user=user, content=content, ad_pool=ads, seed=seed
    )
    records = []
    if not opportunities:
        return records
    running_ctx = opportunities[0].session_context.model_copy()
    prev_minute = 0
    for opp in opportunities:
        live_ctx = running_ctx.model_copy(update={"current_minute": opp.session_context.current_minute})
        if should_force_suppress(live_ctx):
            decision = AdDecision.SUPPRESS
        else:
            ua = score_user_advocate(user, opp.ad_candidate, live_ctx, chromosome)
            adv = score_advertiser_advocate(user, opp.ad_candidate, live_ctx, chromosome)
            result = negotiate(ua, adv, chromosome, user.id, opp.ad_candidate.id, "ab_adaptad")
            decision = result.decision
        minutes_gap = max(0, opp.session_context.current_minute - prev_minute)
        running_ctx = apply_decision(running_ctx, user, decision, opp.session_context.current_minute, minutes_gap)
        prev_minute = opp.session_context.current_minute
        records.append({
            "break_minute": opp.session_context.current_minute,
            "ad_id": opp.ad_candidate.id,
            "ad_category": opp.ad_candidate.category,
            "decision": decision.value,
        })
    return records


def _run_random_session(user, content, ads, seed) -> list[dict]:
    """Run random baseline and return decision records."""
    rng = random.Random(seed)
    opportunities, _ = simulate_session(
        user=user, content=content, ad_pool=ads, seed=seed
    )
    records = []
    for opp in opportunities:
        decision = rng.choice([AdDecision.SHOW, AdDecision.SUPPRESS])
        records.append({
            "break_minute": opp.session_context.current_minute,
            "ad_id": opp.ad_candidate.id,
            "ad_category": opp.ad_candidate.category,
            "decision": decision.value,
        })
    return records


@router.post("/start")
def start_ab_session(req: ABStartRequest):
    users = get_users()
    content_items = get_content()
    ads = get_ads()
    rng = random.Random(req.seed)

    user = next((u for u in users if u.id == req.user_id), None) if req.user_id else rng.choice(users)
    content = next((c for c in content_items if c.id == req.content_id), None) if req.content_id else pick_content_for_user(user, content_items, rng)

    if user is None:
        raise HTTPException(status_code=404, detail=f"User {req.user_id} not found.")
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content {req.content_id} not found.")

    chromosome = get_chromosome()
    seed = req.seed or rng.randint(0, 2**31)

    adaptad_records = _run_adaptad_session(user, content, ads, chromosome, seed)
    random_records = _run_random_session(user, content, ads, seed + 1)

    # Ensure sessions are not identical; regenerate random if needed.
    attempts = 0
    while (
        [r["decision"] for r in adaptad_records] == [r["decision"] for r in random_records]
        and attempts < 5
    ):
        random_records = _run_random_session(user, content, ads, seed + attempts + 10)
        attempts += 1

    # Randomize label assignment to prevent bias.
    if rng.random() < 0.5:
        session_x_records = adaptad_records
        session_y_records = random_records
        x_is_adaptad = True
    else:
        session_x_records = random_records
        session_y_records = adaptad_records
        x_is_adaptad = False

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": user.id,
        "user_name": user.name,
        "user_age_group": user.age_group,
        "user_country": getattr(user, "country", ""),
        "user_interests": user.interests,
        "user_ad_tolerance": user.ad_tolerance,
        "content_id": content.id,
        "content_title": content.title,
        "content_genre": content.genre,
        "content_language": getattr(content, "language", "English"),
        "session_x": session_x_records,
        "session_y": session_y_records,
        "x_is_adaptad": x_is_adaptad,
        "ratings": {},
        "created_at": datetime.utcnow().isoformat(),
        "completed": False,
        "is_custom": False,
    }
    _ab_sessions[session_id] = session_data
    save_ab_session_sync(session_data)

    return {
        "session_id": session_id,
        "user_name": user.name,
        "content_title": content.title,
        "session_x": session_x_records,
        "session_y": session_y_records,
        "instructions": "Rate each session on annoyance, relevance, and willingness to continue (1-5).",
    }


@router.post("/{session_id}/rate")
def submit_rating(session_id: str, req: ABRatingRequest):
    if session_id not in _ab_sessions:
        raise HTTPException(status_code=404, detail=f"AB session {session_id} not found.")

    session = _ab_sessions[session_id]
    if req.session_label not in ("X", "Y"):
        raise HTTPException(status_code=400, detail="session_label must be 'X' or 'Y'.")

    rating = {
        "session_id": session_id,
        "session_label": req.session_label,
        "annoyance": req.annoyance,
        "relevance": req.relevance,
        "willingness": req.willingness,
        "notes": req.notes,
        "rated_at": datetime.utcnow().isoformat(),
    }
    session["ratings"][req.session_label] = rating
    _ab_ratings.append(rating)

    if "X" in session["ratings"] and "Y" in session["ratings"]:
        session["completed"] = True
        save_ab_session_sync({**session, "completed": True})

    save_ab_rating_sync(
        session_id=session_id,
        label=req.session_label,
        x_is_adaptad=session["x_is_adaptad"],
        annoyance=req.annoyance,
        relevance=req.relevance,
        willingness=req.willingness,
        notes=req.notes,
    )

    return {"status": "recorded", "session_id": session_id}


@router.get("/results")
def get_ab_results():
    if not _ab_sessions:
        return {"sessions": [], "aggregate": None}

    completed = [s for s in _ab_sessions.values() if s["completed"]]

    adaptad_wins = 0
    baseline_wins = 0
    tie = 0

    adaptad_scores = {"annoyance": [], "relevance": [], "willingness": []}
    baseline_scores = {"annoyance": [], "relevance": [], "willingness": []}

    for session in completed:
        x_is_adaptad = session["x_is_adaptad"]
        ratings = session["ratings"]
        if "X" not in ratings or "Y" not in ratings:
            continue

        rx = ratings["X"]
        ry = ratings["Y"]

        adaptad_r = rx if x_is_adaptad else ry
        baseline_r = ry if x_is_adaptad else rx

        for metric in ("annoyance", "relevance", "willingness"):
            adaptad_scores[metric].append(adaptad_r[metric])
            baseline_scores[metric].append(baseline_r[metric])

        # Overall winner: higher willingness + lower annoyance + higher relevance.
        adaptad_total = adaptad_r["willingness"] + adaptad_r["relevance"] - adaptad_r["annoyance"]
        baseline_total = baseline_r["willingness"] + baseline_r["relevance"] - baseline_r["annoyance"]

        if adaptad_total > baseline_total:
            adaptad_wins += 1
        elif baseline_total > adaptad_total:
            baseline_wins += 1
        else:
            tie += 1

    def _mean(lst):
        return round(sum(lst) / len(lst), 3) if lst else None

    aggregate = {
        "total_sessions": len(_ab_sessions),
        "completed_sessions": len(completed),
        "adaptad_wins": adaptad_wins,
        "baseline_wins": baseline_wins,
        "ties": tie,
        "adaptad_mean_scores": {k: _mean(v) for k, v in adaptad_scores.items()},
        "baseline_mean_scores": {k: _mean(v) for k, v in baseline_scores.items()},
    }

    return {
        "sessions": [
            {
                "session_id": s["session_id"],
                "user_name": s["user_name"],
                "content_title": s["content_title"],
                "completed": s["completed"],
                "ratings": s["ratings"],
            }
            for s in _ab_sessions.values()
        ],
        "aggregate": aggregate,
    }


@router.get("/{session_id}")
def get_ab_session(session_id: str):
    if session_id not in _ab_sessions:
        raise HTTPException(status_code=404, detail=f"AB session {session_id} not found.")
    return _ab_sessions[session_id]


@router.post("/custom")
def start_custom_ab_session(req: CustomABRequest):
    """
    Run an A/B test using a real person's self-reported profile and a show they are watching.
    Creates a synthetic UserProfile and ContentItem from the supplied details, then runs
    the same AdaptAd vs random-baseline comparison as the standard endpoint.
    """
    from ..data.constants import AD_CATEGORIES

    rng = random.Random(req.seed or random.randint(0, 2**31))

    # Validate interests against known categories.
    valid_cats = set(AD_CATEGORIES)
    interests = [i for i in req.interests if i in valid_cats]
    if not interests:
        interests = ["tech", "travel"]

    user = UserProfile(
        id=99999,
        name=req.person_name if req.person_name.strip() else "You",
        age_group=req.age_group,
        country=req.country,
        profession="Custom",
        interests=interests,
        preferred_watch_time=TimeOfDay.evening,
        ad_tolerance=req.ad_tolerance,
        fatigue_level=0.2,
        engagement_score=0.7,
        session_count=10,
        watch_history=[],
        binge_tendency=0.4,
        content_preferences=interests[:2],
    )

    # Build a realistic ContentItem from the supplied show details.
    genre = req.show_genre if req.show_genre in GENRE_MOODS else "Drama"
    mood_choices = GENRE_MOODS[genre]
    moods, mood_weights = zip(*mood_choices)
    mood = ContentMood(rng.choices(moods, weights=list(mood_weights), k=1)[0])
    duration = req.show_duration_minutes
    intensity = _generate_intensity_curve(duration, mood, rng)
    breaks = _natural_break_points(duration, req.is_series, intensity, rng)

    content = ContentItem(
        id=99999,
        title=req.show_title if req.show_title.strip() else "Custom Show",
        genre=genre,
        language="Custom",
        duration_minutes=duration,
        mood=mood,
        is_series=req.is_series,
        natural_break_points=breaks,
        intensity_curve=intensity,
    )

    ads = get_ads()
    chromosome = get_chromosome()
    seed = req.seed or rng.randint(0, 2**31)

    adaptad_records = _run_adaptad_session(user, content, ads, chromosome, seed)
    random_records = _run_random_session(user, content, ads, seed + 1)

    attempts = 0
    while (
        [r["decision"] for r in adaptad_records] == [r["decision"] for r in random_records]
        and attempts < 5
    ):
        random_records = _run_random_session(user, content, ads, seed + attempts + 10)
        attempts += 1

    if rng.random() < 0.5:
        session_x_records = adaptad_records
        session_y_records = random_records
        x_is_adaptad = True
    else:
        session_x_records = random_records
        session_y_records = adaptad_records
        x_is_adaptad = False

    session_id = str(uuid.uuid4())
    session_data = {
        "session_id": session_id,
        "user_id": user.id,
        "user_name": user.name,
        "user_age_group": user.age_group,
        "user_country": req.country,
        "user_interests": user.interests,
        "user_ad_tolerance": user.ad_tolerance,
        "content_id": content.id,
        "content_title": content.title,
        "content_genre": content.genre,
        "content_language": "Custom",
        "session_x": session_x_records,
        "session_y": session_y_records,
        "x_is_adaptad": x_is_adaptad,
        "ratings": {},
        "created_at": datetime.utcnow().isoformat(),
        "completed": False,
        "is_custom": True,
    }
    _ab_sessions[session_id] = session_data
    save_ab_session_sync(session_data)

    return {
        "session_id": session_id,
        "user_name": user.name,
        "content_title": content.title,
        "session_x": session_x_records,
        "session_y": session_y_records,
        "instructions": "Rate each session on annoyance, relevance, and willingness to continue (1-5).",
    }


@router.get("/history")
def get_ab_history(limit: int = 100):
    """
    Return all completed AB sessions from the database with user profile,
    content info, ratings, and who won each round.
    """
    sessions = get_ab_history_sync(limit=limit)

    adaptad_wins = sum(1 for s in sessions if s["winner"] == "adaptad")
    baseline_wins = sum(1 for s in sessions if s["winner"] == "baseline")
    ties = sum(1 for s in sessions if s["winner"] == "tie")

    return {
        "sessions": sessions,
        "total": len(sessions),
        "aggregate": {
            "adaptad_wins": adaptad_wins,
            "baseline_wins": baseline_wins,
            "ties": ties,
            "win_rate": round(adaptad_wins / len(sessions), 3) if sessions else None,
        },
    }
