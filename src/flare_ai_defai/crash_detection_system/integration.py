"""
Integration layer between ChatRouter and RiskEngine.

This is where the LLM is ALLOWED to operate - but ONLY for:
1. Parsing user intent
2. Interpreting numerical results in natural language

ALL MATH IS DONE IN RISK ENGINE.
"""
import pandas as pd
import structlog
from typing import Dict, Any
from pathlib import Path

from .types import UserIntent, RiskAppetite, RISK_PROFILES, RiskAnalysisResult
from .engine.risk_engine import RiskEngine

logger = structlog.get_logger(__name__)


class RiskAnalysisIntegration:
    """
    Integration between LLM chat and deterministic risk engine.
    
    LLM responsibilities:
    - Parse user intent from natural language
    - Format numerical results as human-readable text
    
    RiskEngine responsibilities:
    - ALL mathematical calculations
    - ALL risk metrics
    - ALL trading recommendations
    """
    
    def __init__(self):
        self.engine = RiskEngine()
        self.data = self._load_data()
    
    def _load_data(self) -> pd.DataFrame:
        """Load BTC 15min data"""
        data_path = Path(__file__).parent / "data" / "btc_15m_data.csv"
        
        if not data_path.exists():
            logger.warning("btc_15m_data.csv not found - using mock data")
            return self._create_mock_data()
        
        df = pd.read_csv(data_path)
        
        # Parse timestamp
        timestamp_col = [col for col in df.columns if 'time' in col.lower()][0]
        df['timestamp'] = pd.to_datetime(df[timestamp_col])
        df.set_index('timestamp', inplace=True)
        
        # Standardize columns
        df = df.rename(columns={
            col: col.lower().replace(' ', '_') 
            for col in df.columns
        })
        
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def _create_mock_data(self) -> pd.DataFrame:
        """Create mock data for testing"""
        import numpy as np
        from datetime import datetime, timedelta
        
        n = 2000
        base_price = 50000
        timestamps = [datetime.now() - timedelta(minutes=15*i) for i in range(n)][::-1]
        
        returns = np.random.normal(0, 0.01, n)
        prices = base_price * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame({
            'open': prices * (1 + np.random.normal(0, 0.001, n)),
            'high': prices * (1 + abs(np.random.normal(0, 0.002, n))),
            'low': prices * (1 - abs(np.random.normal(0, 0.002, n))),
            'close': prices,
            'volume': np.random.lognormal(10, 1, n)
        }, index=pd.DatetimeIndex(timestamps))
        
        return df
    
    def analyze(self, intent: UserIntent) -> RiskAnalysisResult:
        """
        Run risk analysis based on user intent.
        
        Args:
            intent: Parsed user intent (from LLM)
        
        Returns:
            Deterministic risk analysis result
        """
        profile = RISK_PROFILES[intent.risk_appetite]
        
        logger.info(
            "risk_analysis_started",
            position_btc=intent.position_size_btc,
            risk_appetite=intent.risk_appetite.value,
            horizon_hours=intent.horizon_hours
        )
        
        result = self.engine.evaluate(
            data=self.data,
            profile=profile,
            horizon_hours=intent.horizon_hours
        )
        
        logger.info(
            "risk_analysis_complete",
            crash_prob=result.crash_prob,
            regime=result.regime,
            recommended_exposure=result.recommended_exposure
        )
        
        return result
    
    @staticmethod
    def format_response(result: RiskAnalysisResult, intent: UserIntent) -> str:
        """
        Format analysis result as human-readable text.
        
        THIS IS WHERE LLM CAN BE USED - but only for formatting.
        All numbers come from deterministic models.
        
        Args:
            result: Risk analysis result
            intent: User intent
        
        Returns:
            Formatted response string
        """
        # Determine risk level
        if result.crash_prob > 0.6:
            risk_level = "HIGH RISK"
        elif result.crash_prob > 0.3:
            risk_level = "MEDIUM RISK"
        else:
            risk_level = "LOW RISK"
        
        # Format main response
        response_parts = [
            f"📊 **Risk Analysis for {intent.position_size_btc} BTC ({intent.risk_appetite.value} risk profile)**",
            "",
            f"**Crash Probability ({intent.horizon_hours}h):** {result.crash_prob:.1%} ({risk_level})",
            f"**Market Regime:** {result.regime}",
            f"**LCVI:** {result.lcvi:.2f} {'⚠️ ELEVATED' if result.lcvi > 2.0 else '✓ Normal'}",
            f"**Realized Volatility:** {result.realized_vol:.1%} annualized",
            "",
            f"**99% VaR (1-day):** {result.var_1d:.1%} potential loss",
            f"**Expected Shortfall:** {result.es_1d:.1%}",
            "",
            f"**Recommended Exposure:** {result.recommended_exposure:.0%} of position",
            f"**Rationale:** {result.exposure_rationale}",
            "",
            f"_Current BTC Price: ${result.current_price:,.2f}_",
            f"_Analysis Time: {result.analysis_timestamp}_"
        ]
        
        return "\n".join(response_parts)


def parse_user_intent_with_llm(ai_provider, user_message: str) -> UserIntent:
    """
    Use LLM to extract structured intent from user message.
    
    THIS IS THE ONLY PLACE WHERE LLM GENERATES VALUES.
    It ONLY extracts user preferences - no market analysis.
    
    Args:
        ai_provider: LLM provider (Gemini)
        user_message: Raw user input
    
    Returns:
        Structured UserIntent
    """
    import json
    
    extraction_prompt = f"""
Extract the following information from the user's message:

User message: "{user_message}"

Return ONLY a JSON object with these fields:
{{
    "position_size_btc": <float, default 1.0 if not specified>,
    "risk_appetite": "<low|medium|high, default medium>",
    "horizon_hours": <int, default 24 if not specified>,
    "specific_concerns": "<any specific worries mentioned>"
}}

Example:
User: "I hold 2 BTC, medium risk, next 24h"
Output: {{"position_size_btc": 2.0, "risk_appetite": "medium", "horizon_hours": 24, "specific_concerns": ""}}

JSON:
"""
    
    response = ai_provider.generate(
        prompt=extraction_prompt,
        response_mime_type="application/json"
    )
    
    try:
        parsed = json.loads(response.text)
        
        return UserIntent(
            position_size_btc=float(parsed.get('position_size_btc', 1.0)),
            risk_appetite=RiskAppetite(parsed.get('risk_appetite', 'medium')),
            horizon_hours=int(parsed.get('horizon_hours', 24)),
            specific_concerns=parsed.get('specific_concerns', '')
        )
    except Exception as e:
        logger.error("intent_parsing_failed", error=str(e), response=response.text)
        
        # Fallback to defaults
        return UserIntent(
            position_size_btc=1.0,
            risk_appetite=RiskAppetite.MEDIUM,
            horizon_hours=24,
            specific_concerns=user_message
        )
