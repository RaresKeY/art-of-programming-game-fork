"""
Difficulty curve utilities driven by company popularity.

This module encapsulates the logic that translates gameplay outcomes into
popularity, demand tiers, and challenge modifiers. GameEngine can use this to
scale package generation and rewards.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class DemandTier(Enum):
    CALM = "Calm"
    BUSY = "Busy"
    PEAK = "Peak"
    FRENZY = "Frenzy"


@dataclass(frozen=True)
class DifficultySnapshot:
    """
    Snapshot of difficulty settings for a single day.

    Attributes:
        popularity: Current popularity score (0-1000)
        demand_tier: Demand tier label
        challenge_index: Composite difficulty score (0-100)
        modifiers: Dict of keyed challenge modifiers that subsystems can use
    """

    popularity: int
    demand_tier: DemandTier
    challenge_index: float
    modifiers: Dict[str, float]


# --- Popularity utilities ------------------------------------------------- #


def clamp_popularity(score: float) -> int:
    """Clamp popularity score into the allowed [0, 1000] range."""
    return max(0, min(1000, int(round(score))))


def compute_popularity_delta(
    delivered_ratio: float,
    profit: float,
    penalties: float,
    day: int,
    current_popularity: int,
) -> int:
    """
    Calculate popularity delta based on daily performance.

    Args:
        delivered_ratio: Fraction of packages delivered (0-1).
        profit: Profit earned today.
        penalties: Sum of penalty weights (e.g., missed/rush failures).
        day: Current day number (for smoothing during tutorial period).
        current_popularity: Popularity prior to applying delta.

    Returns:
        Popularity delta (may be negative or positive).
    """
    # Delivery success is the strongest signal.
    base_delta = (delivered_ratio - 0.75) * 80  # ±20 roughly for ±0.25 swing

    # Profit influences perception, but taper impact at very high values.
    profit_factor = min(max(profit / 5000, -1), 1) * 10

    # Penalties directly subtract popularity (e.g., undelivered rush packages).
    penalty_impact = -penalties * 15

    delta = base_delta + profit_factor + penalty_impact

    # Tutorial smoothing: keep things gentle in first five days.
    if day <= 5:
        delta *= 0.4

    # High-popularity plateau: harder to climb above 800.
    if current_popularity >= 800 and delta > 0:
        delta *= 0.6

    # Comeback assistance: if very low, boost recoverability.
    if current_popularity <= 200 and delta > 0:
        delta *= 1.3

    return int(round(delta))


# --- Demand tiers and modifiers ------------------------------------------- #


def determine_demand_tier(popularity: int, marketing_level: int) -> DemandTier:
    """
    Determine demand tier from popularity and marketing.

    Marketing provides a slight bias upward, reflecting increased advertising.
    """
    effective_score = popularity + (marketing_level - 1) * 40

    if effective_score < 220:
        return DemandTier.CALM
    if effective_score < 480:
        return DemandTier.BUSY
    if effective_score < 720:
        return DemandTier.PEAK
    return DemandTier.FRENZY


def compute_challenge_index(
    demand_tier: DemandTier,
    day: int,
    recent_penalties: int,
) -> float:
    """
    Composite difficulty index used to gate special events.

    Returns:
        Challenge score scaled roughly 0-100.
    """
    tier_weights = {
        DemandTier.CALM: 15,
        DemandTier.BUSY: 35,
        DemandTier.PEAK: 55,
        DemandTier.FRENZY: 75,
    }
    base = tier_weights[demand_tier]

    # Day progression adds gentle ramp.
    base += min(day / 2, 15)

    # Penalties add spice quickly to discourage sloppy streaks.
    base += min(recent_penalties * 5, 20)

    return min(100.0, base)


def build_modifiers(
    demand_tier: DemandTier,
    challenge_index: float,
) -> Dict[str, float]:
    """
    Create challenge modifier dictionary.

    Keys:
        volume_multiplier: Scales base package volume target
        priority_bias: Additional chance for high-priority packages
        rush_ratio: Fraction of packages flagged as rush orders
        reward_multiplier: Adjusts payment for successful deliveries
    """
    # Base defaults
    modifiers = {
        "volume_multiplier": 1.0,
        "priority_bias": 0.0,
        "rush_ratio": 0.0,
        "reward_multiplier": 1.0,
    }

    tier_settings = {
        DemandTier.CALM: dict(volume_multiplier=0.85, priority_bias=-0.05, rush_ratio=0.0, reward_multiplier=0.95),
        DemandTier.BUSY: dict(volume_multiplier=1.05, priority_bias=0.1, rush_ratio=0.05, reward_multiplier=1.0),
        DemandTier.PEAK: dict(volume_multiplier=1.25, priority_bias=0.2, rush_ratio=0.12, reward_multiplier=1.1),
        DemandTier.FRENZY: dict(volume_multiplier=1.5, priority_bias=0.3, rush_ratio=0.2, reward_multiplier=1.2),
    }

    modifiers.update(tier_settings[demand_tier])

    # Additional spice from challenge index—higher means more extreme rush orders.
    if challenge_index > 70:
        modifiers["rush_ratio"] += 0.05
        modifiers["priority_bias"] += 0.05

    return modifiers


def create_difficulty_snapshot(
    popularity: int,
    marketing_level: int,
    day: int,
    recent_penalties: int,
) -> DifficultySnapshot:
    """Convenience for generating a complete difficulty snapshot."""
    demand_tier = determine_demand_tier(popularity, marketing_level)
    challenge_index = compute_challenge_index(demand_tier, day, recent_penalties)
    modifiers = build_modifiers(demand_tier, challenge_index)
    return DifficultySnapshot(
        popularity=popularity,
        demand_tier=demand_tier,
        challenge_index=challenge_index,
        modifiers=modifiers,
    )
