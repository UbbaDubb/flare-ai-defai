"""
Leverage and liquidation stress signals - PURE MATH, NO LLM.
"""
import numpy as np
import pandas as pd
from typing import Dict


class LeverageSignals:
    """Calculate leverage and liquidation risk signals"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def synthetic_funding_rate(self, prices: pd.Series) -> pd.Series:
        """
        Synthetic funding rate proxy using MA differential.
        
        Formula: FR = (fast_MA / slow_MA - 1) × (365 × 24 / 8)
        
        Positive funding = longs paying shorts (overcrowded longs)
        
        Args:
            prices: Close prices
        
        Returns:
            Annualized synthetic funding rate
        """
        fast_window = self.config['funding_fast_window']
        slow_window = self.config['funding_slow_window']
        
        fast_ma = prices.ewm(span=fast_window).mean()
        slow_ma = prices.ewm(span=slow_window).mean()
        
        funding = (fast_ma / slow_ma - 1) * (365 * 24 / 8)
        return funding
    
    def funding_stress(self, funding_proxy: pd.Series) -> pd.Series:
        """
        Funding rate stress indicator.
        
        Normalized by rolling median absolute funding.
        
        Args:
            funding_proxy: Synthetic funding rate
        
        Returns:
            Funding stress ratio
        """
        window = self.config.get('funding_stress_window', 120)
        median_abs = funding_proxy.abs().rolling(window).median()
        stress = funding_proxy.abs() / median_abs
        return stress
    
    def drawdown(self, prices: pd.Series, window: int | None = None) -> pd.Series:
        """
        Calculate rolling drawdown from peak.
        
        Formula: DD = (P_t - max(P)) / max(P)
        
        Args:
            prices: Close prices
            window: Lookback window
        
        Returns:
            Drawdown series (negative values)
        """
        if window is None:
            window = self.config['lcvi_window']
        
        rolling_max = prices.rolling(window, min_periods=1).max()
        dd = (prices - rolling_max) / rolling_max
        return dd
    
    def drawdown_velocity(self, prices: pd.Series) -> pd.Series:
        """
        Rate of change of drawdown (panic metric).
        
        Args:
            prices: Close prices
        
        Returns:
            Drawdown velocity
        """
        dd = self.drawdown(prices)
        dd_vel = dd.diff().abs() / dd.abs().shift(1)
        dd_vel = dd_vel.replace([np.inf, -np.inf], 0).fillna(0)
        return dd_vel
    
    def lcvi(self, prices: pd.Series, returns: pd.Series, funding_proxy: pd.Series) -> pd.Series:
        """
        Liquidation Cascade Vulnerability Index.
        
        Formula: LCVI = (σ/σ_ref) × (1 + |FR_stress|) × (1 + DD_vel)
        
        Combines:
        - Volatility expansion
        - Funding stress
        - Drawdown acceleration
        
        Args:
            prices: Close prices
            returns: Log returns
            funding_proxy: Synthetic funding rate
        
        Returns:
            LCVI series
        """
        # Volatility component
        ann_factor = np.sqrt(self.config['annualization_factor'])
        vol = returns.rolling(96).std() * ann_factor
        vol_ref = vol.rolling(self.config['lcvi_vol_ref_window']).median()
        vol_ratio = vol / vol_ref
        
        # Funding stress
        fund_stress = self.funding_stress(funding_proxy)
        
        # Drawdown velocity
        dd_vel = self.drawdown_velocity(prices)
        
        # LCVI composite
        lcvi = vol_ratio * (1 + fund_stress) * (1 + dd_vel)
        return lcvi
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all leverage signals.
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            DataFrame with leverage signals
        """
        returns = np.log(data['close'] / data['close'].shift(1))
        
        signals = pd.DataFrame(index=data.index)
        signals['funding_proxy'] = self.synthetic_funding_rate(data['close'])
        signals['funding_stress'] = self.funding_stress(signals['funding_proxy'])
        signals['drawdown'] = self.drawdown(data['close'])
        signals['dd_velocity'] = self.drawdown_velocity(data['close'])
        signals['lcvi'] = self.lcvi(data['close'], returns, signals['funding_proxy'])
        
        return signals
