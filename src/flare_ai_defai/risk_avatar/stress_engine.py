from flare_ai_defai.risk_avatar.models import (
    RiskProfile,
    MarketState,
    AvatarState,
)


def update_avatar_state(
    profile: RiskProfile,
    market: MarketState,
    avatar: AvatarState,
) -> AvatarState:
    """
    Update the avatar stress level and risk mode based on market conditions.
    """

    shock_stress = (
        (market.volatility ** 1.5) * 180 * profile.stress_sensitivity
        + (market.drawdown_speed ** 1.3) * 500
    )

    pain_stress = (market.drawdown ** 1.3) * 300

    incoming_stress = shock_stress + pain_stress

    avatar.stress_level += incoming_stress * profile.reaction_speed * 0.01

    if avatar.risk_mode == "panic":
        recovery = 0.15
    elif avatar.risk_mode == "alert":
        recovery = 0.5
    else:
        recovery = 1.0

    avatar.stress_level -= recovery

    avatar.stress_level = max(0.0, min(100.0, avatar.stress_level))

    if avatar.stress_level < 30:
        avatar.risk_mode = "calm"
    elif avatar.stress_level < 70:
        avatar.risk_mode = "alert"
    else:
        avatar.risk_mode = "panic"

    return avatar
