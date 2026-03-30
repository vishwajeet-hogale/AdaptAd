"""
LLM-based reasoning for agent explanations.

All LLM calls are for natural language explanation ONLY.
They never affect numerical scores or decisions.
Falls back to template reasoning on any failure.
"""

import hashlib
import json
import time
from functools import lru_cache
from typing import Optional

from ..state import AdCandidate, NegotiationResult, UserProfile
from ..config import config


# Simple in-process cache: maps prompt hash -> response text.
_llm_cache: dict[str, str] = {}


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode()).hexdigest()


def _template_explanation(result: NegotiationResult) -> str:
    """
    Generate a plain-text explanation from the negotiation result factors.
    Used when LLM is disabled or fails.
    """
    ua = result.user_advocate
    adv = result.advertiser_advocate
    decision = result.decision.value

    ua_top = sorted(ua.factors.items(), key=lambda x: abs(x[1]), reverse=True)[:2]
    adv_top = sorted(adv.factors.items(), key=lambda x: abs(x[1]), reverse=True)[:2]
    ua_factors_str = ", ".join(f"{k}: {v:+.3f}" for k, v in ua_top if k not in ("base", "final_score"))
    adv_factors_str = ", ".join(f"{k}: {v:+.3f}" for k, v in adv_top if k not in ("base", "final_score"))

    return (
        f"Decision: {decision}. "
        f"User Advocate (score {ua.score:.3f}): {ua_factors_str}. "
        f"Advertiser Advocate (score {adv.score:.3f}): {adv_factors_str}. "
        f"Combined score: {result.combined_score:.3f}."
    )


def _call_llm(prompt: str, provider: str = "groq") -> Optional[str]:
    """
    Call LLM API with a 5-second timeout.

    Returns response text or None on failure.
    """
    try:
        import openai

        cfg = config.llm
        if provider == "groq":
            base_url = cfg.primary_base_url
            model = cfg.primary_model
            api_key_env = "GROQ_API_KEY"
        else:
            base_url = cfg.fallback_base_url
            model = cfg.fallback_model
            api_key_env = "GEMINI_API_KEY"

        import os
        api_key = os.environ.get(api_key_env)
        if not api_key:
            return None

        client = openai.OpenAI(base_url=base_url, api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            timeout=config.llm.timeout_seconds,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def _build_prompt(
    result: NegotiationResult,
    user: Optional[UserProfile],
    ad: Optional[AdCandidate],
) -> str:
    """Build a compact LLM prompt from the negotiation result."""
    ua = result.user_advocate
    adv = result.advertiser_advocate

    user_desc = ""
    if user:
        user_desc = f"User: {user.age_group}, interests={user.interests}, fatigue={user.fatigue_level:.2f}."

    ad_desc = ""
    if ad:
        ad_desc = f"Ad: {ad.category} from {ad.advertiser}, {ad.duration_seconds}s."

    factors_ua = {k: v for k, v in ua.factors.items() if k not in ("base", "final_score")}
    factors_adv = {k: v for k, v in adv.factors.items() if k not in ("base", "final_score")}

    return (
        f"AdaptAd made a {result.decision.value} decision (combined score {result.combined_score:.3f}).\n"
        f"{user_desc}\n"
        f"{ad_desc}\n"
        f"User Advocate score: {ua.score:.3f}. Factors: {json.dumps(factors_ua, indent=None)}.\n"
        f"Advertiser Advocate score: {adv.score:.3f}. Factors: {json.dumps(factors_adv, indent=None)}.\n"
        f"Write 2-3 plain sentences explaining this decision from both perspectives. "
        f"Be direct and specific. Do not use em dashes or semicolons."
    )


_VALID_GENRES = {
    "Action", "Comedy", "Drama", "Sci-Fi", "Horror",
    "Documentary", "Romance", "Thriller", "Animation", "Fantasy"
}


def lookup_show_metadata(title: str) -> dict:
    """
    Use the LLM to infer genre, duration, and series/movie status from a show title.

    Returns a dict with keys: genre, duration_minutes, is_series, description.
    Falls back to safe defaults on any failure.
    """
    defaults = {
        "genre": "Drama",
        "duration_minutes": 45,
        "is_series": True,
        "description": "",
        "source": "fallback",
    }

    if not title.strip():
        return defaults

    prompt = (
        f'Given the title "{title}", provide metadata as JSON only — no explanation, no markdown.\n'
        f'Respond with exactly this structure:\n'
        f'{{"genre":"...","duration_minutes":N,"is_series":true/false,"description":"..."}}\n'
        f'Rules:\n'
        f'- genre must be one of: Action, Comedy, Drama, Sci-Fi, Horror, Documentary, Romance, Thriller, Animation, Fantasy\n'
        f'- duration_minutes = episode length (in minutes) for series, full runtime for movies\n'
        f'- is_series = true for TV series / anime, false for movies\n'
        f'- description = one sentence synopsis, 15 words max\n'
        f'If you do not recognise the title, make a best guess based on the name.'
    )

    cache_key = _cache_key(prompt)
    raw = _llm_cache.get(cache_key)

    if raw is None:
        raw = _call_llm(prompt, provider="groq")
        if raw is None:
            raw = _call_llm(prompt, provider="gemini")
        if raw is not None:
            _llm_cache[cache_key] = raw

    if raw is None:
        return defaults

    # Strip any markdown fences the model may have included.
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
        genre = data.get("genre", "Drama")
        if genre not in _VALID_GENRES:
            genre = "Drama"
        duration = int(data.get("duration_minutes", 45))
        duration = max(10, min(240, duration))
        is_series = bool(data.get("is_series", True))
        description = str(data.get("description", ""))[:200]
        return {
            "genre": genre,
            "duration_minutes": duration,
            "is_series": is_series,
            "description": description,
            "source": "llm",
        }
    except Exception:
        return defaults


def enrich_with_llm_reasoning(
    result: NegotiationResult,
    user: Optional[UserProfile],
    ad: Optional[AdCandidate],
) -> NegotiationResult:
    """
    Attempt to replace template reasoning with LLM-generated explanation.

    Falls back to template on any failure.
    Returns a new NegotiationResult with updated reasoning field.
    """
    if not config.llm.enabled:
        return result

    prompt = _build_prompt(result, user, ad)
    cache_key = _cache_key(prompt)

    if cache_key in _llm_cache:
        llm_text = _llm_cache[cache_key]
    else:
        # Try primary provider first.
        llm_text = _call_llm(prompt, provider="groq")
        if llm_text is None:
            # Try fallback provider.
            llm_text = _call_llm(prompt, provider="gemini")
        if llm_text is not None:
            _llm_cache[cache_key] = llm_text

    if llm_text is None:
        llm_text = _template_explanation(result)

    return result.model_copy(update={"reasoning": llm_text})
