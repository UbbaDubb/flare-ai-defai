"""
Type definitions for the risk analysis system.
All user-facing types and configurations are deterministic.
"""
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class RiskAppetite(str, Enum):
    """User risk tolerance levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RiskProfile:
    """
    Deterministic mapping from user risk appetite to trading parameters.
    
    NO LLM INVOLVEMENT - these are pure mathematical thresholds.
    
    Attributes:
        name: Risk profile identifier (low/medium/high)
        crash_cutoff_high: Probability threshold for "high crash risk" alert
        crash_cutoff_medium: Probability threshold for "medium crash risk" alert
        max_exposure_normal: Maximum position size in normal conditions (1.0 = 100%)
        max_exposure_stress: Maximum position size in high-risk conditions
        weights: Signal importance weights for crash probability model
    """
    name: str
    crash_cutoff_high: float
    crash_cutoff_medium: float
    max_exposure_normal: float
    max_exposure_stress: float
    weights: dict[str, float]


# Predefined risk profiles - DETERMINISTIC, NO LLM
RISK_PROFILES = {
    RiskAppetite.LOW: RiskProfile(
        name="low",
        crash_cutoff_high=0.5,
        crash_cutoff_medium=0.25,
        max_exposure_normal=0.6,
        max_exposure_stress=0.1,
        weights={
            'regime_prob': 0.30,
            'lcvi': 0.25,
            'evt_tail': 0.20,
            'vol_regime': 0.15,
            'dd_velocity': 0.10,
        }
    ),
    RiskAppetite.MEDIUM: RiskProfile(
        name="medium",
        crash_cutoff_high=0.6,
        crash_cutoff_medium=0.3,
        max_exposure_normal=1.0,
        max_exposure_stress=0.3,
        weights={
            'regime_prob': 0.25,
            'lcvi': 0.20,
            'evt_tail': 0.15,
            'vol_regime': 0.15,
            'dd_velocity': 0.12,
            'funding_stress': 0.08,
            'illiquidity': 0.05,
        }
    ),
    RiskAppetite.HIGH: RiskProfile(
        name="high",
        crash_cutoff_high=0.7,
        crash_cutoff_medium=0.4,
        max_exposure_normal=1.5,
        max_exposure_stress=0.5,
        weights={
            'regime_prob': 0.20,
            'lcvi': 0.18,
            'evt_tail': 0.12,
            'vol_regime': 0.15,
            'dd_velocity': 0.15,
            'funding_stress': 0.10,
            'illiquidity': 0.10,
        }
    ),
}


@dataclass
class RiskAnalysisResult:
    """
    Output from the risk engine evaluation.
    ALL fields are deterministic outputs from mathematical models.
    NO LLM INVOLVEMENT in any numerical field.
    """
    crash_prob: float
    regime: str
    regime_probs: dict[str, float]
    lcvi: float
    vol_regime: float
    realized_vol: float
    var_1d: float
    es_1d: float
    tail_shape: float
    recommended_exposure: float
    exposure_rationale: str
    current_price: float
    analysis_timestamp: str


@dataclass
class UserIntent:
    """
    Parsed user input from LLM.
    LLM ONLY extracts these fields; all downstream processing is deterministic.
    """
    position_size_btc: float
    risk_appetite: RiskAppetite
    horizon_hours: int
    specific_concerns: str = ""
