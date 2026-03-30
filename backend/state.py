"""
Pydantic data models for AdaptAd.

These are the source of truth for all data flowing through the system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AdDecision(str, Enum):
    SHOW = "SHOW"
    SOFTEN = "SOFTEN"
    DELAY = "DELAY"
    SUPPRESS = "SUPPRESS"


class TimeOfDay(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
    latenight = "latenight"


class Season(str, Enum):
    Spring = "Spring"
    Summer = "Summer"
    Fall = "Fall"
    Winter = "Winter"


class ContentMood(str, Enum):
    calm = "calm"
    uplifting = "uplifting"
    playful = "playful"
    energetic = "energetic"
    intense = "intense"
    dark = "dark"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    id: int
    name: str
    age_group: str
    country: str = ""
    profession: str
    interests: list[str]
    preferred_watch_time: TimeOfDay
    ad_tolerance: float
    fatigue_level: float
    engagement_score: float
    session_count: int
    watch_history: list[str]
    binge_tendency: float
    content_preferences: list[str]

    @field_validator("age_group")
    @classmethod
    def validate_age_group(cls, v: str) -> str:
        valid = {"13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"}
        if v not in valid:
            raise ValueError(f"age_group must be one of {valid}, got '{v}'")
        return v

    @field_validator("ad_tolerance", "fatigue_level", "engagement_score", "binge_tendency")
    @classmethod
    def clamp_float(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @field_validator("interests")
    @classmethod
    def interests_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("interests must not be empty")
        return v


class AdCandidate(BaseModel):
    id: str
    category: str
    advertiser: str
    duration_seconds: int
    priority: float
    seasonal_affinity: dict[str, float]
    target_demographics: list[str]
    creative_type: str
    has_softened_version: bool = True

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = {"tech", "food", "auto", "fashion", "finance", "travel", "health", "gaming"}
        if v not in valid:
            raise ValueError(f"category must be one of {valid}, got '{v}'")
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        valid = {15, 30, 45, 60}
        if v not in valid:
            raise ValueError(f"duration_seconds must be one of {valid}, got {v}")
        return v

    @field_validator("creative_type")
    @classmethod
    def validate_creative_type(cls, v: str) -> str:
        valid = {"video", "overlay", "banner"}
        if v not in valid:
            raise ValueError(f"creative_type must be one of {valid}, got '{v}'")
        return v

    @property
    def softened_duration(self) -> int:
        """Duration when SOFTEN decision is made."""
        import math
        return math.floor(self.duration_seconds / 2)


class ContentItem(BaseModel):
    id: int
    title: str
    genre: str
    language: str = "English"
    duration_minutes: int
    mood: ContentMood
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    is_series: bool = False
    natural_break_points: list[int]
    intensity_curve: list[float]

    @model_validator(mode="after")
    def validate_break_points_and_curve(self) -> "ContentItem":
        buffer = 5
        valid_bps = []
        for bp in self.natural_break_points:
            if bp < buffer or bp > self.duration_minutes - buffer:
                continue
            valid_bps.append(bp)
        self.natural_break_points = valid_bps

        if len(self.intensity_curve) != self.duration_minutes:
            # Pad or truncate to match duration.
            if len(self.intensity_curve) < self.duration_minutes:
                self.intensity_curve = self.intensity_curve + [0.5] * (
                    self.duration_minutes - len(self.intensity_curve)
                )
            else:
                self.intensity_curve = self.intensity_curve[: self.duration_minutes]

        return self

    def intensity_at(self, minute: int) -> float:
        """Safe intensity lookup with bounds check."""
        if not self.intensity_curve:
            return 0.5
        idx = max(0, min(minute, len(self.intensity_curve) - 1))
        return self.intensity_curve[idx]


class SessionContext(BaseModel):
    time_of_day: TimeOfDay
    season: Season
    ads_shown_this_session: int = 0
    session_duration_minutes: int = 0
    content: Optional[ContentItem] = None
    current_minute: int = 0
    content_queue: list[ContentItem] = []
    is_binging: bool = False
    session_fatigue_accumulator: float = 0.0

    @field_validator("session_fatigue_accumulator")
    @classmethod
    def clamp_fatigue(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class AdOpportunity(BaseModel):
    """Represents a single moment where an ad could be shown."""

    user: UserProfile
    ad_candidate: AdCandidate
    session_context: SessionContext
    opportunity_id: str


# ---------------------------------------------------------------------------
# Chromosome
# ---------------------------------------------------------------------------


class Chromosome(BaseModel):
    """8-gene policy chromosome for the genetic algorithm."""

    fatigue_weight: float = 0.5
    relevance_weight: float = 0.5
    timing_weight: float = 0.5
    frequency_threshold: float = 0.5
    delay_probability: float = 0.5
    soften_threshold: float = 0.5
    category_boost: float = 0.5
    session_depth_factor: float = 0.5

    fitness: Optional[float] = None

    @field_validator(
        "fatigue_weight",
        "relevance_weight",
        "timing_weight",
        "frequency_threshold",
        "delay_probability",
        "soften_threshold",
        "category_boost",
        "session_depth_factor",
    )
    @classmethod
    def clamp_gene(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    def to_vector(self) -> list[float]:
        return [
            self.fatigue_weight,
            self.relevance_weight,
            self.timing_weight,
            self.frequency_threshold,
            self.delay_probability,
            self.soften_threshold,
            self.category_boost,
            self.session_depth_factor,
        ]

    @classmethod
    def from_vector(cls, vec: list[float]) -> "Chromosome":
        if len(vec) != 8:
            raise ValueError(f"Chromosome vector must have 8 genes, got {len(vec)}")
        return cls(
            fatigue_weight=vec[0],
            relevance_weight=vec[1],
            timing_weight=vec[2],
            frequency_threshold=vec[3],
            delay_probability=vec[4],
            soften_threshold=vec[5],
            category_boost=vec[6],
            session_depth_factor=vec[7],
        )

    @classmethod
    def gene_names(cls) -> list[str]:
        return [
            "fatigue_weight",
            "relevance_weight",
            "timing_weight",
            "frequency_threshold",
            "delay_probability",
            "soften_threshold",
            "category_boost",
            "session_depth_factor",
        ]


# ---------------------------------------------------------------------------
# Agent and negotiation models
# ---------------------------------------------------------------------------


class AgentScore(BaseModel):
    agent_name: str
    score: float
    reasoning: str
    factors: dict[str, float]

    @field_validator("score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class NegotiationResult(BaseModel):
    decision: AdDecision
    user_advocate: AgentScore
    advertiser_advocate: AgentScore
    combined_score: float
    reasoning: str
    timestamp: datetime
    session_id: str
    user_id: int
    ad_id: str


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------


class GraphState(BaseModel):
    """Central state object passed through all LangGraph nodes."""

    # Per-decision context
    user: Optional[UserProfile] = None
    ad_candidate: Optional[AdCandidate] = None
    session_context: Optional[SessionContext] = None

    # GA state
    population: list[Chromosome] = []
    current_generation: int = 0
    max_generations: int = 50
    ga_history: list[dict[str, Any]] = []
    best_chromosome: Optional[Chromosome] = None
    ga_converged: bool = False

    # Agent results
    user_advocate_score: Optional[AgentScore] = None
    advertiser_advocate_score: Optional[AgentScore] = None
    negotiation_result: Optional[NegotiationResult] = None

    # Data pools
    user_pool: list[UserProfile] = []
    ad_pool: list[AdCandidate] = []
    batch_results: list[NegotiationResult] = []

    # Flow control
    phase: str = "idle"
    error: Optional[str] = None
    job_id: Optional[str] = None
