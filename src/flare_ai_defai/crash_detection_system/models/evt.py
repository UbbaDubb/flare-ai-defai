"""
Extreme Value Theory for tail risk - PURE MATH, NO LLM.

Uses Generalized Pareto Distribution (GPD) to model tail losses.
Computes VaR and Expected Shortfall.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Tuple


class ExtremeValueModel:
    """GPD model for tail risk estimation"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.threshold = None
        self.shape = None
        self.scale = None
        self.n_exceedances = 0
    
    def fit(self, returns: pd.Series) -> 'ExtremeValueModel':
        losses = -returns.dropna()
        self.n = len(losses)

        threshold_pct = self.config['threshold_percentile']
        self.threshold = np.percentile(losses, threshold_pct)

        exceedances = losses[losses > self.threshold] - self.threshold
        self.n_exceedances = len(exceedances)

        if self.n_exceedances < 10:
            self.shape = 0.2
            self.scale = exceedances.std() if len(exceedances) > 0 else 0.01
        else:
            self.shape, _, self.scale = stats.genpareto.fit(exceedances, floc=0)

        return self

    
    def var(self, p_tail: float | None = None) -> float:
        """
        Value-at-Risk using EVT POT.

        p_tail: tail probability (e.g. 0.01 for 99% VaR)
        """
        if p_tail is None:
            p_tail = 1 - self.config['var_confidence']
        if self.shape is None or self.scale is None or self.threshold is None:
            return 0.05

        p = p_tail  # local non-optional float

        shape = self.shape
        scale = self.scale
        threshold = self.threshold

        n = self.n
        n_u = max(self.n_exceedances, 10)

        var_value = threshold + (scale / shape) * ((n * (p / n_u) ) ** (-shape) - 1)

        return max(var_value, 0.0)


    
    def expected_shortfall(self, p_tail: float | None = None) -> float:
        if p_tail is None:
            p_tail = 1 - self.config['es_confidence']

        if self.shape is None or self.scale is None or self.threshold is None:
            return self.var(p_tail) * 1.3

        if self.shape >= 1:
            return self.var(p_tail) * 1.3

        shape = self.shape
        scale = self.scale
        threshold = self.threshold

        var_value = self.var(p_tail)
        es = var_value / (1 - shape) + (scale - shape * threshold) / (1 - shape)

        return max(es, var_value)

    
    def tail_index(self) -> float:
        """
        Return tail shape parameter.
        
        > 0.3 = heavy tail (high crash risk)
        
        Returns:
            Tail shape ξ
        """
        return self.shape if self.shape is not None else 0.2
