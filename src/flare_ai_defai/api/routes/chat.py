"""
Chat Router Module

This module implements the main chat routing system for the AI Agent API.
It handles message routing, blockchain interactions, attestations, and AI responses.

The module provides a ChatRouter class that integrates various services:
- AI capabilities through GeminiProvider
- Blockchain operations through FlareProvider
- Attestation services through Vtpm
- Prompt management through PromptService
- Risk Analysis through RiskEngine (NEW)
"""

import json
import re


from pathlib import Path
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from web3 import Web3
from web3.exceptions import Web3RPCError

from flare_ai_defai.ai import GeminiProvider
from flare_ai_defai.attestation import Vtpm, VtpmAttestationError
from flare_ai_defai.blockchain import FlareProvider
from flare_ai_defai.prompts import PromptService, SemanticRouterResponse
from flare_ai_defai.settings import settings

# 🔹 NEW: Import risk analysis components
#from flare_ai_defai.crash_detection_system.integration import (
#    RiskAnalysisIntegration,
#    parse_user_intent_with_llm,
#)

logger = structlog.get_logger(__name__)
router = APIRouter()

def wants_analysis(message: str) -> bool:
    """
    Only enter structured snapshot analysis when explicitly requested.
    Default is normal chat.
    """
    msg = message.lower()
    triggers = [
        "snapshot",
        "summaris",   # summarize / summarise
        "analy",      # analyze / analysis
        "risk",
        "entropy",
        "kl",
        "what to watch",
        "state",
    ]
    return any(t in msg for t in triggers)


def coerce_json(text: str) -> dict[str, Any]:
    """
    Accepts:
      - raw JSON
      - ```json ... ``` fenced JSON
      - extra text around a JSON object (best-effort extraction)
    """
    t = text.strip()

    # unwrap fenced code block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, flags=re.S)
    if m:
        t = m.group(1).strip()

    # best-effort: extract first {...}
    if not (t.startswith("{") and t.endswith("}")):
        m2 = re.search(r"(\{.*\})", t, flags=re.S)
        if m2:
            t = m2.group(1).strip()

    return json.loads(t)


def load_snapshot() -> dict[str, Any] | None:
    p = Path(settings.latest_update_path).resolve()
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


class ChatMessage(BaseModel):
    """
    Pydantic model for chat message validation.

    Attributes:
        message (str): The chat message content, must not be empty
    """

    message: str = Field(..., min_length=1)


class ChatRouter:
    """
    Main router class handling chat messages and their routing to appropriate handlers.

    This class integrates various services and provides routing logic for different
    types of chat messages including blockchain operations, attestations, and general
    conversation.

    Attributes:
        ai (GeminiProvider): Provider for AI capabilities
        blockchain (FlareProvider): Provider for blockchain operations
        attestation (Vtpm): Provider for attestation services
        prompts (PromptService): Service for managing prompts
        risk_integration (RiskAnalysisIntegration): Risk analysis engine (NEW)
        logger (BoundLogger): Structured logger for the chat router
    """

    def __init__(
        self,
        ai: GeminiProvider,
        blockchain: FlareProvider,
        attestation: Vtpm,
        prompts: PromptService,
    ) -> None:
        """
        Initialize the ChatRouter with required service providers.

        Args:
            ai: Provider for AI capabilities
            blockchain: Provider for blockchain operations
            attestation: Provider for attestation services
            prompts: Service for managing prompts
        """
        self._router = APIRouter()
        self.ai = ai
        self.blockchain = blockchain
        self.attestation = attestation
        self.prompts = prompts
        self.logger = logger.bind(router="chat")
        
        # 🔹 NEW: Initialize risk analysis integration
        #try:
        #    self.risk_integration = RiskAnalysisIntegration()
        #    self.logger.info("risk_engine_initialized")
        #except Exception as e:
        #    self.logger.warning("risk_engine_init_failed", error=str(e))
        self.risk_integration = None
        
        self._setup_routes()

    def _setup_routes(self) -> None:
        """
        Set up FastAPI routes for the chat endpoint.
        Handles message routing, command processing, and transaction confirmations.
        """

        @self._router.post("/")
        async def chat(message: ChatMessage): # -> dict[str, Any]:  # pyright: ignore [reportUnusedFunction]
            """
            Process incoming chat messages and route them to appropriate handlers.

            Args:
                message: Validated chat message

            Returns:
                dict[str, str]: Response containing handled message result

            Raises:
                HTTPException: If message handling fails
            """
            try:
                self.logger.debug("received_message", message=message.message)

                if message.message.startswith("/"):
                    return await self.handle_command(message.message)
                if (
                    self.blockchain.tx_queue
                    and message.message == self.blockchain.tx_queue[-1].msg
                ):
                    try:
                        tx_hash = self.blockchain.send_tx_in_queue()
                    except Web3RPCError as e:
                        self.logger.exception("send_tx_failed", error=str(e))
                        msg = (
                            f"Unfortunately the tx failed with the error:\n{e.args[0]}"
                        )
                        return {"response": msg}

                    prompt, mime_type, schema = self.prompts.get_formatted_prompt(
                        "tx_confirmation",
                        tx_hash=tx_hash,
                        block_explorer=settings.web3_explorer_url,
                    )
                    tx_confirmation_response = self.ai.generate(
                        prompt=prompt,
                        response_mime_type=mime_type,
                        response_schema=schema,
                    )
                    return {"response": tx_confirmation_response.text}
                if self.attestation.attestation_requested:
                    try:
                        resp = self.attestation.get_token([message.message])
                    except VtpmAttestationError as e:
                        resp = f"The attestation failed with  error:\n{e.args[0]}"
                    self.attestation.attestation_requested = False
                    return {"response": resp}
                
                # Commented out to test
                #

                # 🔹 NEW: Check if this is a risk analysis request BEFORE semantic routing
                #if self._is_risk_query(message.message):
                #    return await self.handle_risk_analysis(message.message)

                route = await self.get_semantic_route(message.message)
                return await self.route_message(route, message.message)

            except Exception as e:
                self.logger.exception("message_handling_failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e)) from e

    @property
    def router(self) -> APIRouter:
        """Get the FastAPI router with registered routes."""
        return self._router

    # 🔹 NEW: Risk query detection
    def _is_risk_query(self, message: str) -> bool:
        """
        Detect if message is a risk analysis query.
        
        Args:
            message: User message
        
        Returns:
            True if risk-related query
        """
        risk_keywords = [
            'risk', 'crash', 'exposure', 'volatile', 'volatility',
            'btc', 'bitcoin', 'position', 'hedge', 'drawdown',
            'liquidation', 'var', 'downside', 'portfolio'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in risk_keywords)

    # 🔹 NEW: Risk analysis handler
    async def handle_risk_analysis(self, message: str) -> dict[str, str]:
        """
        Handle risk analysis requests.
        
        Flow:
        1. LLM parses user intent (position size, risk appetite, horizon)
        2. RiskEngine performs ALL mathematical analysis (NO LLM)
        3. Format results as natural language
        
        Args:
            message: User's natural language request
        
        Returns:
            dict[str, str]: Formatted risk analysis response
        """
        try:
            # Check if risk engine is available
            if not self.risk_integration:
                return {
                    "response": "Risk analysis is currently unavailable. "
                    "Please ensure btc_15m_data.csv is present or contact support."
                }
            
            self.logger.info("risk_analysis_requested", message=message)
            
            # Step 1: LLM ONLY extracts user preferences (NO MATH)
            intent = parse_user_intent_with_llm(self.ai, message)
            
            self.logger.debug(
                "parsed_intent",
                position_btc=intent.position_size_btc,
                risk_appetite=intent.risk_appetite.value,
                horizon_hours=intent.horizon_hours
            )
            
            # Step 2: DETERMINISTIC risk analysis (ALL MATH HERE, NO LLM)
            result = self.risk_integration.analyze(intent)
            
            # Step 3: Format response (can use LLM for natural language)
            response = RiskAnalysisIntegration.format_response(result, intent)
            
            self.logger.info(
                "risk_analysis_complete",
                crash_prob=result.crash_prob,
                regime=result.regime,
                recommended_exposure=result.recommended_exposure
            )
            
            return {"response": response}
            
        except Exception as e:
            self.logger.exception("risk_analysis_failed", error=str(e))
            return {
                "response": f"Risk analysis encountered an error: {str(e)}\n\n"
                "Please try again or contact support if the issue persists."
            }

    async def handle_command(self, command: str) -> dict[str, str]:
        """
        Handle special command messages starting with '/'.

        Args:
            command: Command string to process

        Returns:
            dict[str, str]: Response containing command result
        """
        if command == "/reset":
            self.blockchain.reset()
            self.ai.reset()
            return {"response": "Reset complete"}
        return {"response": "Unknown command"}

    async def get_semantic_route(self, message: str) -> SemanticRouterResponse:
        """
        Determine the semantic route for a message using AI provider.

        Args:
            message: Message to route

        Returns:
            SemanticRouterResponse: Determined route for the message
        """
        try:
            prompt, mime_type, schema = self.prompts.get_formatted_prompt(
                "semantic_router", user_input=message
            )
            route_response = self.ai.generate(
                prompt=prompt, response_mime_type=mime_type, response_schema=schema
            )
            return SemanticRouterResponse(route_response.text)
        except Exception as e:
            self.logger.exception("routing_failed", error=str(e))
            return SemanticRouterResponse.CONVERSATIONAL

    async def route_message(
        self, route: SemanticRouterResponse, message: str
    ) -> dict[str, str]:
        """
        Route a message to the appropriate handler based on semantic route.

        Args:
            route: Determined semantic route
            message: Original message to handle

        Returns:
            dict[str, str]: Response from the appropriate handler
        """
        handlers = {
            SemanticRouterResponse.GENERATE_ACCOUNT: self.handle_generate_account,
            SemanticRouterResponse.SEND_TOKEN: self.handle_send_token,
            SemanticRouterResponse.SWAP_TOKEN: self.handle_swap_token,
            SemanticRouterResponse.REQUEST_ATTESTATION: self.handle_attestation,
            SemanticRouterResponse.CONVERSATIONAL: self.handle_conversation,
        }

        handler = handlers.get(route)
        if not handler:
            return {"response": "Unsupported route"}

        return await handler(message)

    async def handle_generate_account(self, _: str) -> dict[str, str]:
        """
        Handle account generation requests.

        Args:
            _: Unused message parameter

        Returns:
            dict[str, str]: Response containing new account information
                or existing account
        """
        if self.blockchain.address:
            return {"response": f"Account exists - {self.blockchain.address}"}
        address = self.blockchain.generate_account()
        prompt, mime_type, schema = self.prompts.get_formatted_prompt(
            "generate_account", address=address
        )
        gen_address_response = self.ai.generate(
            prompt=prompt, response_mime_type=mime_type, response_schema=schema
        )
        return {"response": gen_address_response.text}

    async def handle_send_token(self, message: str) -> dict[str, str]:
        """
        Handle token sending requests.

        Args:
            message: Message containing token sending details

        Returns:
            dict[str, str]: Response containing transaction preview or follow-up prompt
        """
        if not self.blockchain.address:
            await self.handle_generate_account(message)

        prompt, mime_type, schema = self.prompts.get_formatted_prompt(
            "token_send", user_input=message
        )
        send_token_response = self.ai.generate(
            prompt=prompt, response_mime_type=mime_type, response_schema=schema
        )
        send_token_json = json.loads(send_token_response.text)
        expected_json_len = 2
        if (
            len(send_token_json) != expected_json_len
            or send_token_json.get("amount") == 0.0
        ):
            prompt, _, _ = self.prompts.get_formatted_prompt("follow_up_token_send")
            follow_up_response = self.ai.generate(prompt)
            return {"response": follow_up_response.text}

        tx = self.blockchain.create_send_flr_tx(
            to_address=send_token_json.get("to_address"),
            amount=send_token_json.get("amount"),
        )
        self.logger.debug("send_token_tx", tx=tx)
        self.blockchain.add_tx_to_queue(msg=message, tx=tx)
        formatted_preview = (
            "Transaction Preview: "
            + f"Sending {Web3.from_wei(tx.get('value', 0), 'ether')} "
            + f"FLR to {tx.get('to')}\nType CONFIRM to proceed."
        )
        return {"response": formatted_preview}

    async def handle_swap_token(self, _: str) -> dict[str, str]:
        """
        Handle token swap requests (currently unsupported).

        Args:
            _: Unused message parameter

        Returns:
            dict[str, str]: Response indicating unsupported operation
        """
        return {"response": "Sorry I can't do that right now"}

    async def handle_attestation(self, _: str) -> dict[str, str]:
        """
        Handle attestation requests.

        Args:
        _: Unused message parameter

        Returns:
        dict[str, str]: Response containing attestation request
        """
        prompt = self.prompts.get_formatted_prompt("request_attestation")[0]
        request_attestation_response = self.ai.generate(prompt=prompt)
        self.attestation.attestation_requested = True
        return {"response": request_attestation_response.text}

    
    
    async def handle_conversation(self, message: str) -> dict[str, Any]:
        use_snapshot = wants_analysis(message)  # you might rename this to wants_snapshot()
        
        snapshot = load_snapshot() if use_snapshot else None
        grounding_snapshot = (
            f"\nSNAPSHOT_JSON (background context):\n{json.dumps(snapshot, indent=2)}\n"
            if snapshot is not None
            else ""
        )

        prompt = f"""
        SYSTEM:
        You are Artemis, a helpful assistant for a demo Flare DeFAI app.
        You are NOT a financial advisor.
        Do not provide personalized financial advice.
        Do NOT tell the user to buy/sell/hold or give trade instructions.
        You MAY provide general, educational "things to consider".

        INSTRUCTIONS:
        - Answer in normal conversational text (no JSON).
        - If snapshot values are provided and relevant, weave them naturally into the answer.
        - Never invent missing values. If a field is null/missing, say "not provided".

        {grounding_snapshot}

        USER:
        {message}
        """.strip()

        resp = self.ai.send_message(prompt)
        text = getattr(resp, "text", None)
        if not isinstance(text, str) or not text.strip():
                return {"response": "Sorry, I got an unexpected response from the server."}
        return {"response": text}
