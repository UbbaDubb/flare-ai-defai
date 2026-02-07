import time
from collections import deque
import numpy as np

from flare_ai_defai.risk_avatar.models import (
    RiskProfile,
    MarketState,
    AvatarState,
)
from flare_ai_defai.risk_avatar.stress_engine import update_avatar_state
from flare_ai_defai.risk_avatar.flare_oracle import get_btc_price


class RiskAvatarManager:
    def __init__(self, window: int = 30):
        self.prices = deque(maxlen=window)
        self.timestamps = deque(maxlen=window)
        self._prev_drawdown = 0.0

        self.profile = RiskProfile(
            risk_level=50,
            max_drawdown=0.15,
            leverage_allowed=True,
            stress_sensitivity=2.5,
            reaction_speed=0.8,
        )

        self.avatar = AvatarState(
            stress_level=20.0,
            risk_mode="calm",
        )

    def _compute_features(self):
        if len(self.prices) < 2:
            return 0.0, 0.0, 0.0

        prices = np.array(self.prices)
        returns = np.diff(prices) / prices[:-1]

        volatility = np.std(returns)
        peak = np.max(prices)
        drawdown = (peak - prices[-1]) / peak

        drawdown_speed = max(0.0, drawdown - getattr(self, "_prev_drawdown", 0.0))
        self._prev_drawdown = drawdown

        return volatility, drawdown, drawdown_speed

    def update(self) -> AvatarState:
        price, ts = get_btc_price()

        self.prices.append(price)
        self.timestamps.append(ts)

        volatility, drawdown, drawdown_speed = self._compute_features()

        market = MarketState(
            price=price,
            volatility=float(volatility),
            drawdown=float(drawdown),
            drawdown_speed=float(drawdown_speed),
            timestamp=int(time.time()),
        )

        self.avatar = update_avatar_state(
            self.profile,
            market,
            self.avatar,
        )

        return self.avatar
