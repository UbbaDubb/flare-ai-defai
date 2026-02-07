"""
Crash probability model - PURE MATH, NO LLM.

Combines signals using weighted ensemble with sigmoid transformation.
"""
import numpy as np
import pandas as pd
from typing import Dict


class CrashProbabilityModel:
    """Weighted ensemble crash probability model"""
    
    def __init__(self, config: Dict, weights: Dict[str, float]):
        """
        Args:
            config: Model configuration
            weights: Signal weights from RiskProfile
        """
        self.config = config
        self.weights = weights
    
    def calculate(self, signals: Dict[str, pd.DataFrame]) -> pd.Series:
        """
        Calculate crash probability from signals.
        
        Formula:
        1. Normalize each signal to [0, 1] using percentile rank
        2. Weighted sum: score = Σ (rank(signal_i) × weight_i)
        3. Sigmoid: P(crash) = 1 / (1 + exp(-5(score - 0.5)))
        
        Args:
            signals: Dict of signal DataFrames
        
        Returns:
            Crash probability series [0, 1]
        """
        # Combine all signals into one DataFrame
        all_signals = pd.DataFrame(index=signals['volatility'].index)
        
        # Extract relevant signals
        if 'vol_regime' in signals['volatility'].columns:
            all_signals['vol_regime'] = signals['volatility']['vol_regime']
        
        if 'lcvi' in signals['leverage'].columns:
            all_signals['lcvi'] = signals['leverage']['lcvi']
        
        if 'dd_velocity' in signals['leverage'].columns:
            all_signals['dd_velocity'] = signals['leverage']['dd_velocity']
        
        if 'funding_stress' in signals['leverage'].columns:
            all_signals['funding_stress'] = signals['leverage']['funding_stress']
        
        if 'illiquidity_ratio' in signals['microstructure'].columns:
            all_signals['illiquidity'] = signals['microstructure']['illiquidity_ratio']
        
        # Add regime probabilities
        if 'regime_probs' in signals:
            all_signals['regime_prob'] = signals['regime_probs']['prob_Crash']
        
        # Add EVT tail shape
        if 'evt_tail_shape' in signals:
            all_signals['evt_tail'] = signals['evt_tail_shape']
        
        # Normalize signals to [0, 1] using percentile rank
        normalized = pd.DataFrame(index=all_signals.index)
        
        for col in all_signals.columns:
            if col in self.weights:
                normalized[col] = all_signals[col].rank(pct=True)
        
        # Weighted sum
        score = pd.Series(0, index=all_signals.index)
        total_weight = 0
        
        for col, weight in self.weights.items():
            if col in normalized.columns:
                score += normalized[col] * weight
                total_weight += weight
        
        if total_weight > 0:
            score /= total_weight
        
        # Sigmoid transformation to probability
        crash_prob = 1 / (1 + np.exp(-5 * (score - 0.5)))
        
        return crash_prob
