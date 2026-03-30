"""
Global configuration for AdaptAd.

All tunable parameters live here. Rationale is documented inline.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GAConfig:
    """Genetic algorithm hyperparameters."""

    population_size: int = 30
    # Top 20% survive unchanged. Protects best solutions across generations.
    elite_ratio: float = 0.2
    # 15% chance per gene per offspring. High enough to escape local optima.
    mutation_rate: float = 0.15
    # Max delta +/- 0.15 per gene. Keeps mutations meaningful but bounded.
    mutation_strength: float = 0.3
    max_generations: int = 50
    # Stop if best fitness improves by less than this over 15 generations.
    convergence_threshold: float = 0.0005
    convergence_window: int = 15
    # Fitness = 60% user satisfaction + 40% revenue. Biased toward user welfare.
    fitness_user_weight: float = 0.6
    fitness_revenue_weight: float = 0.4
    # Restart with fresh random pop if stuck for this many generations.
    stuck_restart_threshold: int = 20


@dataclass
class FatigueConfig:
    """Fatigue accumulation increments per decision type."""

    # Values chosen to reflect relative intrusiveness of each decision.
    # SHOW is fully intrusive, SUPPRESS has zero impact.
    show_increment: float = 0.10
    soften_increment: float = 0.05
    delay_increment: float = 0.02
    suppress_increment: float = 0.00
    # Reward ad-free viewing with mild fatigue recovery.
    decay_per_minute: float = 0.01
    force_suppress_threshold: float = 0.85
    penalty_threshold: float = 0.70
    penalty_amount: float = 0.15


@dataclass
class AgentConfig:
    """Agent scoring parameters."""

    # User Advocate weights
    ua_base: float = 0.5
    ua_relevance_max: float = 0.8
    ua_relevance_irrelevant: float = 0.15
    ua_fatigue_multiplier: float = 1.5
    ua_timing_bonus: float = 0.3
    ua_session_penalty_2: float = 0.15
    ua_session_penalty_3: float = 0.30
    ua_intensity_threshold: float = 0.7
    ua_intensity_penalty: float = 0.12
    ua_binge_penalty: float = 0.08

    # Advertiser Advocate weights
    adv_base: float = 0.55
    adv_relevance_multiplier: float = 1.5
    adv_engagement_multiplier: float = 0.3
    adv_primetime_evening: float = 0.15
    adv_primetime_afternoon: float = 0.05
    adv_priority_scale: float = 0.2
    adv_demographic_match_bonus: float = 0.08

    # Negotiator thresholds
    user_weight: float = 0.55
    advertiser_weight: float = 0.45
    # show_threshold = 0.45 + frequency_threshold_gene * 0.35
    base_show_threshold: float = 0.45
    show_threshold_scale: float = 0.35
    soften_offset: float = 0.15
    delay_offset: float = 0.15


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    primary_provider: str = "groq"
    primary_model: str = "llama-3.3-70b-versatile"
    primary_base_url: str = "https://api.groq.com/openai/v1"

    fallback_provider: str = "gemini"
    fallback_model: str = "gemini-2.5-flash"
    fallback_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"

    timeout_seconds: float = 5.0
    max_retries: int = 3
    enabled: bool = True


@dataclass
class SimulationConfig:
    """Session simulation parameters."""

    num_users: int = 400
    num_content_items: int = 150
    num_ads: int = 80
    # Never place an ad in the first or last 5 minutes of content.
    break_point_buffer_minutes: int = 5
    # Binge detection requires 2+ queued episodes.
    binge_queue_threshold: int = 2
    binge_episode_threshold: int = 1
    binge_tendency_threshold: float = 0.5
    # Session ends when fatigue crosses this level.
    session_end_fatigue: float = 0.9


@dataclass
class DatabaseConfig:
    path: str = "adaptad.db"


@dataclass
class Config:
    ga: GAConfig = field(default_factory=GAConfig)
    fatigue: FatigueConfig = field(default_factory=FatigueConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    chromosomes_dir: str = "chromosomes"
    debug: bool = False


# Module-level singleton
config = Config()
