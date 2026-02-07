"""
Risk Engine - Orchestrates all models and signals.
PURE MATH, NO LLM.
"""
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict

from ..types import RiskProfile, RiskAnalysisResult
from ..signals.volatility import VolatilitySignals
from ..signals.leverage import LeverageSignals
from ..signals.microstructure import MicrostructureSignals
from ..models.regime_hmm import RegimeHMM
from ..models.evt import ExtremeValueModel
from ..models.crash_probability import CrashProbabilityModel


class RiskEngine:
    """
    Main risk analysis engine.
    
    Orchestrates:
    1. Signal computation
    2. Model fitting
    3. Crash probability calculation
    4. Exposure recommendation
    
    ALL DETERMINISTIC - NO LLM INVOLVEMENT
    """
    
    def __init__(self, config_path: str | None = None):
        """
        Args:
            config_path: Path to parameters.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "parameters.yaml"
        
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        # Initialize signal calculators
        self.vol_signals = VolatilitySignals(self.config['signals']['volatility'])
        self.lev_signals = LeverageSignals(self.config['signals']['leverage'])
        self.micro_signals = MicrostructureSignals(self.config['signals']['microstructure'])
        
        # Initialize models
        self.regime_model = RegimeHMM(self.config['models']['regime_hmm'])
        self.evt_model = ExtremeValueModel(self.config['models']['evt'])
    
    def evaluate(
        self,
        data: pd.DataFrame,
        profile: RiskProfile,
        horizon_hours: int
    ) -> RiskAnalysisResult:
        """
        Perform complete risk analysis.
        
        Args:
            data: OHLCV DataFrame (15min bars)
            profile: User risk profile (determines weights)
            horizon_hours: Forecast horizon
        
        Returns:
            RiskAnalysisResult with all metrics
        """
        # Compute returns
        returns = np.log(data['close'] / data['close'].shift(1))
        
        # 1. Compute signals
        vol_sigs = self.vol_signals.compute_all(data)
        lev_sigs = self.lev_signals.compute_all(data)
        micro_sigs = self.micro_signals.compute_all(data)
        
        # 2. Fit regime model
        self.regime_model.fit(returns)
        regime_probs = self.regime_model.predict_proba(returns)
        regime = self.regime_model.predict_regime(returns)
        
        # 3. Fit EVT model
        self.evt_model.fit(returns)
        
        # 4. Calculate crash probability
        signals_dict = {
            'volatility': vol_sigs,
            'leverage': lev_sigs,
            'microstructure': micro_sigs,
            'regime_probs': regime_probs,
            'evt_tail_shape': pd.Series(
                self.evt_model.tail_index(),
                index=data.index
            )
        }
        
        crash_model = CrashProbabilityModel(
            self.config['models']['crash_probability'],
            profile.weights
        )
        crash_prob_series = crash_model.calculate(signals_dict)
        
        # 5. Get latest values
        latest_idx = data.index[-1]
        crash_prob = crash_prob_series.iloc[-1]
        current_regime = regime.iloc[-1]
        lcvi = lev_sigs['lcvi'].iloc[-1]
        vol_regime = vol_sigs['vol_regime'].iloc[-1]
        realized_vol = vol_sigs['realized_vol'].iloc[-1]
        
        # 6. Calculate exposure recommendation
        recommended_exposure, rationale = self._calculate_exposure(
            crash_prob=crash_prob,
            lcvi=lcvi,
            vol_regime=vol_regime,
            regime=current_regime,
            profile=profile
        )
        
        # 7. Return result
        return RiskAnalysisResult(
            crash_prob=float(crash_prob),
            regime=current_regime,
            regime_probs={
                'Calm': float(regime_probs['prob_Calm'].iloc[-1]),
                'Volatile': float(regime_probs['prob_Volatile'].iloc[-1]),
                'Crash': float(regime_probs['prob_Crash'].iloc[-1]),
            },
            lcvi=float(lcvi),
            vol_regime=float(vol_regime),
            realized_vol=float(realized_vol),
            var_1d=float(self.evt_model.var()),
            es_1d=float(self.evt_model.expected_shortfall()),
            tail_shape=float(self.evt_model.tail_index()),
            recommended_exposure=float(recommended_exposure),
            exposure_rationale=rationale,
            current_price=float(data['close'].iloc[-1]),
            analysis_timestamp=datetime.utcnow().isoformat()
        )
    
    def _calculate_exposure(
        self,
        crash_prob: float,
        lcvi: float,
        vol_regime: float,
        regime: str,
        profile: RiskProfile
    ) -> tuple[float, str]:
        """
        Calculate recommended exposure based on risk metrics.
        
        DETERMINISTIC LOGIC - NO LLM.
        
        Returns:
            (exposure, rationale)
        """
        reasons = []
        
        # Start with profile's max normal exposure
        exposure = profile.max_exposure_normal
        
        # Adjust based on crash probability
        if crash_prob > profile.crash_cutoff_high:
            exposure = min(exposure, profile.max_exposure_stress)
            reasons.append(f"crash_prob={crash_prob:.2f} (HIGH)")
        elif crash_prob > profile.crash_cutoff_medium:
            exposure = min(exposure, profile.max_exposure_normal * 0.6)
            reasons.append(f"crash_prob={crash_prob:.2f} (MEDIUM)")
        
        # Adjust based on LCVI
        lcvi_critical = self.config['thresholds']['lcvi_critical']
        lcvi_warning = self.config['thresholds']['lcvi_warning']
        
        if lcvi > lcvi_critical:
            exposure = min(exposure, profile.max_exposure_stress)
            reasons.append(f"LCVI={lcvi:.2f} (CRITICAL)")
        elif lcvi > lcvi_warning:
            exposure = min(exposure, profile.max_exposure_normal * 0.7)
            reasons.append(f"LCVI={lcvi:.2f} (WARNING)")
        
        # Adjust based on regime
        if regime == 'Crash':
            exposure = min(exposure, profile.max_exposure_stress)
            reasons.append("regime=Crash")
        elif regime == 'Volatile':
            exposure = min(exposure, profile.max_exposure_normal * 0.8)
            reasons.append("regime=Volatile")
        
        # Build rationale
        if not reasons:
            rationale = "Normal market conditions - full exposure"
        else:
            rationale = "Reduced exposure due to: " + ", ".join(reasons)
        
        return exposure, rationale
