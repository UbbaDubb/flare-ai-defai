"""
PATCH FOR chat.py

Add these imports at the top:
"""

from flare_ai_defai.crash_detection_system.integration import (
    RiskAnalysisIntegration,
    parse_user_intent_with_llm
)

"""
Then add this method to ChatRouter class:
"""

def handle_risk_analysis(self, user_message: str) -> str:
    """
    Handle risk analysis requests.
    
    Flow:
    1. LLM parses user intent (position size, risk appetite, horizon)
    2. RiskEngine performs ALL mathematical analysis
    3. LLM formats results as natural language
    
    Args:
        user_message: User's natural language request
    
    Returns:
        Formatted risk analysis response
    """
    try:
        # Initialize risk integration
        risk_integration = RiskAnalysisIntegration()
        
        # LLM ONLY extracts user preferences
        intent = parse_user_intent_with_llm(self.ai, user_message)
        
        # DETERMINISTIC risk analysis
        result = risk_integration.analyze(intent)
        
        # Format response (LLM can assist here)
        response = RiskAnalysisIntegration.format_response(result, intent)
        
        return response
        
    except Exception as e:
        self.logger.error("risk_analysis_failed", error=str(e))
        return f"Risk analysis failed: {str(e)}"

"""
And modify handle_conversation to route risk queries:
"""

def handle_conversation(self, user_message: str, **kwargs) -> str:
    """Route to risk analysis if message contains risk keywords"""
    
    # Check if this is a risk analysis request
    risk_keywords = ['risk', 'crash', 'exposure', 'btc', 'position', 'volatility']
    if any(keyword in user_message.lower() for keyword in risk_keywords):
        return self.handle_risk_analysis(user_message)
    
    # Otherwise, proceed with normal chat flow
    # ... existing code ...
