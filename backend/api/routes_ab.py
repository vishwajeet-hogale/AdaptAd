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
from ..state import AdDecision, Chromosome, Season, TimeOfDay
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


def _build_user_profile(user)-> dict:
    return {
        "id": user.id,
        "name": user.name,
        "age_group": getattr(user, "age_group", None),
        "profession": user.profession,
        "interests": list(user.interests),  # ad categories
        "content_preferences": list(user.content_preferences),  # genres
        "binge_tendency": round(float(user.binge_tendency), 2),
        "fatigue_level": round(float(user.fatigue_level), 2),
        "engagement_score": round(float(user.engagement_score), 2),
        "ad_tolerance": round(float(user.ad_tolerance), 2),
        "preferred_watch_time": str(user.preferred_watch_time),
        "session_count": user.session_count,
    }

def _build_content_profile(content)->dict:
    return {
        "id":content.id,
        "title": content.title,
        "genre": getattr(content, "genre", None),
        "duration": getattr(content, "duration", None),
        "mood": getattr(content, "mood", None),
    }

def _build_session_context(user, content, records)-> dict:
    total_ads = sum(1 for r in records if r["decision"] in ("SHOW", "SOFTEN"))
    total_breaks = len(records)

    return {
        "ads_shown": total_ads,
        "total_breaks": total_breaks,
        "fatigue": round(float(user.fatigue_level),2),
        "session_depth": records[-1]["break_minute"] if records else 0,
        "content_duration": getattr(content, "duration", None),
        "binge": bool(getattr(user, "binge_tendency", 0.0) > 0.5),
    }


@router.post("/start")
def start_ab_session(req: ABStartRequest):
    users = get_users()
    content_items = get_content()
    ads = get_ads()
    rng = random.Random(req.seed)

    user = next((u for u in users if u.id == req.user_id), None) if req.user_id else rng.choice(users)
    content = next((c for c in content_items if c.id == req.content_id), None) if req.content_id else rng.choice(content_items)

    if user is None:
        raise HTTPException(status_code=404, detail=f"User {req.user_id} not found.")
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content {req.content_id} not found.")

    chromosome = get_chromosome()
    seed = req.seed or rng.randint(0, 2**31)

    adaptad_records = _run_adaptad_session(user, content, ads, chromosome, seed)
    random_records = _run_random_session(user, content, ads, seed + 1)

    #new code
    user_profile=_build_user_profile(user)
    content_profile = _build_content_profile(content)
    session_context= _build_session_context(user, content, adaptad_records)

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
    _ab_sessions[session_id] = {
        "session_id": session_id,
        "user_id": user.id,
        "user_name": user.name,
        "user_profile": user_profile,
        "content_id": content.id,
        "content_title": content.title,
        "content_profile": content_profile,
        "session_context": session_context,
        "session_x": session_x_records,
        "session_y": session_y_records,
        "x_is_adaptad": x_is_adaptad,
        "ratings": {},
        "created_at": datetime.utcnow().isoformat(),
        "completed": False,
    }

    return {
        "session_id": session_id,
        "user_name": user.name,
        "user_profile": user_profile,
        "content_title": content.title,
        "content_profile": content_profile,
        "session_context": session_context,
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
                "user_profile": s.get("user_profile"),
                "content_title": s["content_title"],
                "content_profile": s.get("content_profile"),
                "session_context": s.get("session_context"),
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
