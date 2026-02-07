"""
Market microstructure signals - PURE MATH, NO LLM.
"""
import numpy as np
import pandas as pd


class MicrostructureSignals:
    """Calculate market microstructure signals"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def amihud_illiquidity(self, returns: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Amihud illiquidity measure: price impact per unit volume.
        
        Formula: Illiq = |r| / volume
        
        Higher values = less liquid (dangerous during crashes)
        
        Args:
            returns: Log returns
            volume: Trading volume
        
        Returns:
            Illiquidity series
        """
        window = self.config['illiquidity_window']
        illiq = returns.abs() / volume
        illiq_rolling = illiq.rolling(window).mean()
        return illiq_rolling
    
    def illiquidity_ratio(self, returns: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Illiquidity relative to historical median.
        
        Args:
            returns: Log returns
            volume: Trading volume
        
        Returns:
            Illiquidity ratio
        """
        illiq = self.amihud_illiquidity(returns, volume)
        ref_window = self.config['illiquidity_ref_window']
        illiq_ref = illiq.rolling(ref_window).median()
        ratio = illiq / illiq_ref
        return ratio
    
    def tail_risk_asymmetry(self, returns: pd.Series) -> pd.Series:
        """
        Tail risk asymmetry: -skew × sqrt(excess_kurtosis).
        
        High positive values = left tail risk (crash risk)
        
        Args:
            returns: Log returns
        
        Returns:
            Tail risk asymmetry
        """
        window = self.config['tail_risk_window']
        skew = returns.rolling(window).skew()
        kurt = returns.rolling(window).kurt()
        tra = -skew * np.sqrt(np.maximum(kurt - 3, 0))
        return tra
    
    def compute_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all microstructure signals.
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            DataFrame with microstructure signals
        """
        returns = pd.Series(np.log(data['close'] / data['close'].shift(1)), index=data.index)
        
        signals = pd.DataFrame(index=data.index)
        signals['illiquidity'] = self.amihud_illiquidity(returns, data['volume'])
        signals['illiquidity_ratio'] = self.illiquidity_ratio(returns, data['volume'])
        signals['tail_risk_asym'] = self.tail_risk_asymmetry(returns)
        
        return signals
