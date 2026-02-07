"""
Hidden Markov Model for regime detection - PURE MATH, NO LLM.

Uses hmmlearn library for Gaussian HMM with 3 states:
- Calm (low vol, positive returns)
- Volatile (high vol, uncertain returns)
- Crash (extreme vol, negative returns)
"""
import numpy as np
import pandas as pd
import warnings
from typing import Dict
from numpy.typing import NDArray
from hmmlearn.hmm import GaussianHMM
from typing import cast


try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    warnings.warn("hmmlearn not installed - using simplified regime detection")


class RegimeHMM:
    """Hidden Markov Model for market regime detection"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.model = None
        self.regime_labels = ['Calm', 'Volatile', 'Crash']
    
    def fit(self, returns: pd.Series) -> 'RegimeHMM':
        """
        Fit HMM to returns data.
        
        Args:
            returns: Log returns series
        
        Returns:
            self
        """
        if not HMM_AVAILABLE:
            return self
        
        X = returns.dropna().to_numpy().reshape(-1, 1)
        
        self.model = hmm.GaussianHMM(
            n_components=self.config['n_components'],
            covariance_type=self.config['covariance_type'],
            n_iter=self.config['n_iter'],
            random_state=self.config['random_state']
        )
        
        self.model.fit(X)
        self._sort_regimes()
        
        return self
    
    def _sort_regimes(self) -> None:
        """Sort regimes by increasing volatility"""

        if self.model is None:
            return

        model = cast(GaussianHMM, self.model)
        covars: np.ndarray = model.covars_.flatten()



        # Extract per-regime variance (1D returns case)
        if covars.ndim == 3:          # full
            variances = covars[:, 0, 0]
        elif covars.ndim == 2:        # diag
            variances = covars[:, 0]
        else:                         # spherical
            variances = covars

        sorted_idx = np.argsort(variances)

        self.model.means_ = self.model.means_[sorted_idx]
        self.model.covars_ = covars[sorted_idx]
        self.model.startprob_ = self.model.startprob_[sorted_idx]
        self.model.transmat_ = self.model.transmat_[sorted_idx][:, sorted_idx]


    
    def predict_regime(self, returns: pd.Series) -> pd.Series:
        """
        Predict most likely regime.
        
        Args:
            returns: Log returns
        
        Returns:
            Regime labels
        """
        if not HMM_AVAILABLE or not self.model:
            return self._fallback_regime(returns)
        
        X = returns.dropna().to_numpy().reshape(-1, 1)
        regimes = self.model.predict(X)
        
        regime_series = pd.Series(
            [self.regime_labels[r] for r in regimes],
            index=returns.dropna().index,
            name='regime'
        )
        
        return regime_series
    
    def predict_proba(self, returns: pd.Series) -> pd.DataFrame:
        """
        Predict regime probabilities.
        
        Args:
            returns: Log returns
        
        Returns:
            DataFrame with P(Calm), P(Volatile), P(Crash)
        """
        if not HMM_AVAILABLE or not self.model:
            return self._fallback_proba(returns)
        
        X = returns.dropna().to_numpy().reshape(-1, 1)
        probs = self.model.predict_proba(X)
        
        prob_df = pd.DataFrame(
            probs,
            index=returns.dropna().index,
            columns=[f'prob_{label}' for label in self.regime_labels]
        )
        
        return prob_df
    
    def _fallback_regime(self, returns: pd.Series) -> pd.Series:
        """Fallback regime detection when HMM unavailable"""
        ann_factor = np.sqrt(365 * 24 * 4)
        vol = returns.rolling(96).std() * ann_factor
        
        regime = pd.Series('Calm', index=returns.index)
        regime[vol > 0.5] = 'Volatile'
        regime[vol > 1.0] = 'Crash'
        
        return regime
    
    def _fallback_proba(self, returns: pd.Series) -> pd.DataFrame:
        """Fallback probabilities when HMM unavailable"""
        regime = self._fallback_regime(returns)
        
        probs = pd.DataFrame(index=returns.index)
        probs['prob_Calm'] = (regime == 'Calm').astype(float)
        probs['prob_Volatile'] = (regime == 'Volatile').astype(float)
        probs['prob_Crash'] = (regime == 'Crash').astype(float)
        
        return probs
