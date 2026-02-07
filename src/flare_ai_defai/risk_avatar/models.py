from dataclasses import dataclass


@dataclass
class RiskProfile:
    risk_level: int           # 0–100
    max_drawdown: float
    leverage_allowed: bool
    stress_sensitivity: float
    reaction_speed: float


@dataclass
class MarketState:
    price: float
    volatility: float
    drawdown: float
    drawdown_speed: float
    timestamp: int


@dataclass
class AvatarState:
    stress_level: float
    risk_mode: str  # "calm" | "alert" | "panic"
