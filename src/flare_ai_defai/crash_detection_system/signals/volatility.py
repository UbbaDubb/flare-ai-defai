"""
Volatility signal calculations - PURE MATH, NO LLM.

All functions are deterministic and unit-testable.
"""
import numpy as np
import pandas as pd


class VolatilitySignals:
    """Calculate volatility-based crash detection signals"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def realized_volatility(self, returns: pd.Series, window: int | None = None) -> pd.Series:
        """
        Calculate annualized realized volatility.
        
        Formula: RV_t = σ(r_t) × √(periods_per_year)
        
        Args:
            returns: Log returns series
            window: Rolling window size (bars)
        
        Returns:
            Annualized realized volatility
        """
        if window is None:
            window = self.config.get('rv_window', 20)
        
        window = int(window) if window is not None else 20
        ann_factor = np.sqrt(self.config['annualization_factor'])
        rv = returns.rolling(window).std() * ann_factor
        return rv
    
    def vol_regime(self, returns: pd.Series) -> pd.Series:
        """
        Volatility regime indicator: short-term vol / long-term vol.
        
        > 1.5 indicates extreme volatility (fragile market state)
        
        Args:
            returns: Log returns series
        
        Returns:
            Volatility regime ratio
        """
        short_window = self.config['vol_regime_short']
        long_window = self.config['vol_regime_long']
        
        rv_short = self.realized_volatility(returns, short_window)
        rv_long = rv_short.ewm(span=long_window).mean()
        
        regime = rv_short / rv_long
        return regime
    
    def vol_of_vol(self, returns: pd.Series) -> pd.Series:
        """
        Volatility of volatility (coefficient of variation).
        
        High vol-of-vol indicates unstable variance dynamics.
        
        Args:
            returns: Log returns series
        
        Returns:
            Vol-of-vol series
        """
        window = self.config['vov_window']
        lookback = self.config['vov_lookback']
        
        rv = self.realized_volatility(returns, window=24)
        vov = rv.rolling(lookback).std() / rv.rolling(lookback).mean()
        
        return vov
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all volatility signals.
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            DataFrame with volatility signals
        """
        returns = pd.Series(np.log(data['close'] / data['close'].shift(1)), index=data.index)
        
        signals = pd.DataFrame(index=data.index)
        signals['realized_vol'] = self.realized_volatility(returns)
        signals['vol_regime'] = self.vol_regime(returns)
        signals['vol_of_vol'] = self.vol_of_vol(returns)
        
        return signals
