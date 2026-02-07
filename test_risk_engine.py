"""Quick test of risk engine"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.flare_ai_defai.crash_detection_system.types import RiskAppetite, RISK_PROFILES, UserIntent
from src.flare_ai_defai.crash_detection_system.integration import RiskAnalysisIntegration

# Create integration
integration = RiskAnalysisIntegration()

# Create test intent
intent = UserIntent(
    position_size_btc=2.0,
    risk_appetite=RiskAppetite.MEDIUM,
    horizon_hours=24
)

# Run analysis
print("Running risk analysis...")
result = integration.analyze(intent)

# Format response
response = RiskAnalysisIntegration.format_response(result, intent)
print("\n" + response)

print("\n✅ Risk engine test complete!")
