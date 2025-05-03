"""Google Gemini AI client for portfolio analysis."""

import logging
import os
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from .ai_utils import PORTFOLIO_ADVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Model configuration
# https://ai.google.dev/gemini-api/docs/models#model-versions
GEMINI_MODEL_NAME = (
    # alternatively: gemini-2.5-pro-exp-03-25
    "gemini-2.5-flash-preview-04-17"
)
GEMINI_TEMPERATURE = 0.7
GEMINI_TOP_P = 0.95
GEMINI_TOP_K = 40
GEMINI_MAX_OUTPUT_TOKENS = 4096
CONVERSATION_HISTORY_LIMIT = 10

# Analysis prompt template
PORTFOLIO_ANALYSIS_PROMPT_TEMPLATE = """
You are a professional financial advisor analyzing a stock portfolio.
Remember that you should ONLY answer questions related to finance, investments, and the client's portfolio.

Provide a comprehensive analysis of the following portfolio data:

PORTFOLIO SUMMARY:
- Total Portfolio Value: ${total_value:.2f}
- Net Market Exposure: ${net_exposure:.2f}
- Long Exposure: ${long_exposure:.2f}
- Short Exposure: ${short_exposure:.2f}
- Beta-Adjusted Net Exposure: ${beta_adjusted_net_exposure:.2f}

POSITIONS:
{positions_text}

Please analyze this portfolio and provide insights on:
1. Overall risk assessment (based on exposures, diversification, and position sizes)
2. Sector concentration and diversification analysis
3. Quality of the companies in the portfolio
4. Specific improvement recommendations

Format your response in clear sections with headers. Be specific and actionable in your recommendations.

If the user asks about topics unrelated to finance or investments, politely redirect them back to discussing their portfolio.
"""


class GeminiClient:
    """Client for interacting with Google Gemini AI API."""

    def __init__(self):
        """Initialize the Gemini client with API key from environment."""
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.is_available = False

        if not self.api_key:
            logger.error("GEMINI_API_KEY environment variable not set")
            raise ValueError("GEMINI_API_KEY environment variable not set")

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=GEMINI_MODEL_NAME,
                generation_config=GenerationConfig(
                    temperature=GEMINI_TEMPERATURE,
                    top_p=GEMINI_TOP_P,
                    top_k=GEMINI_TOP_K,
                    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
                ),
                # Set the system prompt to ensure the AI stays focused on portfolio advising
                system_instruction=PORTFOLIO_ADVISOR_SYSTEM_PROMPT,
            )
            self.is_available = True
            logger.info(
                f"Gemini client initialized successfully with model {GEMINI_MODEL_NAME}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e!s}")
            raise ValueError(f"Failed to initialize Gemini client: {e!s}") from e

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]],
        portfolio_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a response to a user message in the context of their portfolio (async version).

        Args:
            message: The user's message
            history: List of previous messages in the conversation
            portfolio_data: Optional dictionary containing portfolio information

        Returns:
            Dictionary with the AI response and any additional data
        """
        try:
            # Create the conversation context with portfolio data if available
            context = self._create_conversation_context(portfolio_data)

            # Format the conversation history for the model
            formatted_history = []
            for msg in history[
                -CONVERSATION_HISTORY_LIMIT:
            ]:  # Limit to last N messages for context window
                formatted_history.append({
                    "role": msg["role"],
                    "parts": [msg["content"]],
                })

            # Add the current message
            formatted_history.append({"role": "user", "parts": [message]})

            # If we have portfolio context, add it to the first user message
            if context and formatted_history:
                for i, msg in enumerate(formatted_history):
                    if msg["role"] == "user":
                        formatted_history[i]["parts"] = [
                            context + "\n\n" + msg["parts"][0]
                        ]
                        break

            # Generate response
            response = await self.model.generate_content_async(formatted_history)

            return {"response": response.text, "complete": True}

        except Exception as e:
            logger.error(f"Error in chat: {e!s}")
            return {
                "response": f"I encountered an error: {e!s}",
                "complete": False,
                "error": True,
            }

    def chat_sync(
        self,
        message: str,
        history: list[dict[str, str]],
        portfolio_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a response to a user message in the context of their portfolio (synchronous version).

        This method is provided for environments where async/await cannot be used.

        Args:
            message: The user's message
            history: List of previous messages in the conversation
            portfolio_data: Optional dictionary containing portfolio information

        Returns:
            Dictionary with the AI response and any additional data
        """
        try:
            # Log the start of the process
            logger.info(
                f"Starting chat_sync with message: '{message[:50]}...' and {len(history)} history items"
            )

            # Create the conversation context with portfolio data if available
            context = self._create_conversation_context(portfolio_data)
            logger.info(f"Created conversation context: {len(context)} characters")

            # Prepare the user message with context if available
            user_message = message
            if context:
                user_message = context + "\n\n" + message
                logger.info("Added portfolio context to user message")

            # Use the Gemini SDK's built-in chat functionality
            logger.info("Using Gemini SDK chat functionality")

            # Properly format history for the Gemini API
            formatted_history = []

            # Add previous messages to the history in the correct format
            if history:
                logger.info(
                    f"Formatting {len(history)} previous messages for chat history"
                )
                for msg in history[
                    -CONVERSATION_HISTORY_LIMIT:
                ]:  # Limit to last N messages for context window
                    role = "user" if msg["role"] == "user" else "model"
                    formatted_history.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}],
                    })

            # Create a chat session with history
            logger.info("Creating new chat session with history")
            chat = self.model.start_chat(history=formatted_history)

            # Send the current message
            logger.info("Sending message to chat session")
            response = chat.send_message(user_message)
            logger.info(
                f"Received response from Gemini API: {len(response.text)} characters"
            )

            return {"response": response.text, "complete": True}

        except Exception as e:
            logger.error(f"Error in chat_sync: {e!s}", exc_info=True)
            return {
                "response": f"I encountered an error: {e!s}",
                "complete": False,
                "error": True,
            }

    async def analyze_portfolio(self, portfolio_data: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze portfolio data using Gemini AI.

        Args:
            portfolio_data: Dictionary containing portfolio information

        Returns:
            Dictionary with structured analysis results
        """
        prompt = self._create_analysis_prompt(portfolio_data)

        try:
            response = await self.model.generate_content_async(prompt)

            # Process and structure the response
            structured_analysis = self._process_analysis_response(response.text)
            logger.info("Portfolio analysis completed successfully")
            return structured_analysis

        except Exception as e:
            logger.error(f"Error during portfolio analysis: {e!s}")
            return {
                "error": True,
                "message": f"Analysis failed: {e!s}",
            }

    def _create_analysis_prompt(self, portfolio_data: dict[str, Any]) -> str:
        """
        Create a structured prompt for portfolio analysis.

        Args:
            portfolio_data: Dictionary containing portfolio information

        Returns:
            Formatted prompt string
        """
        # Extract key portfolio metrics
        positions = portfolio_data["positions"]
        summary = portfolio_data["summary"]

        # Format positions data
        positions_text = "\n".join([
            f"- {pos['ticker']}: {pos['position_type'].upper()}, "
            f"Value: ${pos['market_value']:.2f}, "
            f"Beta: {pos['beta']:.2f}, "
            f"Weight: {pos['weight']:.2%}"
            for pos in positions
        ])

        # Format summary data
        # Extract key metrics from the summary
        total_value = summary["portfolio_value"]
        net_exposure = summary["net_market_exposure"]
        long_exposure = summary["long_exposure"]["total_exposure"]
        short_exposure = summary["short_exposure"]["total_exposure"]
        beta_adjusted_net_exposure = (
            summary["long_exposure"]["total_beta_adjusted"]
            + summary["short_exposure"]["total_beta_adjusted"]
        )

        # Construct the prompt using the template
        prompt = PORTFOLIO_ANALYSIS_PROMPT_TEMPLATE.format(
            total_value=total_value,
            net_exposure=net_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            beta_adjusted_net_exposure=beta_adjusted_net_exposure,
            positions_text=positions_text,
        )

        return prompt

    def _create_conversation_context(
        self, portfolio_data: dict[str, Any] | None
    ) -> str:
        """
        Create a context string with portfolio information for the AI.

        Args:
            portfolio_data: Dictionary containing portfolio information

        Returns:
            Formatted context string
        """
        if not portfolio_data:
            return ""

        # Extract key portfolio metrics
        positions = portfolio_data["positions"]
        summary = portfolio_data["summary"]
        allocations = portfolio_data["allocations"]

        # Get values and percentages
        values = allocations["values"]
        percentages = allocations["percentages"]

        # Format positions data (limit to top 10 by absolute value for context size)
        # Note: We still use abs() here because we want to sort by magnitude, not sign
        # This is appropriate for sorting to find the largest positions by impact
        sorted_positions = sorted(
            positions, key=lambda p: abs(p["market_value"]), reverse=True
        )[:10]

        # Build context using multi-line f-strings
        context = f"""Portfolio Analysis Context:

Portfolio Summary:
- Total Portfolio Value: ${summary["portfolio_value"]:,.2f}
- Net Market Exposure: ${summary["net_market_exposure"]:,.2f}
- Beta-Adjusted Net Exposure: ${summary["long_exposure"]["total_beta_adjusted"] + summary["short_exposure"]["total_beta_adjusted"]:,.2f}

Exposure Breakdown:
- Long Exposure: ${summary["long_exposure"]["total_exposure"]:,.2f} ({percentages["long_stock"] + percentages["long_option"]:.1f}% of portfolio)
- Short Exposure: ${summary["short_exposure"]["total_exposure"]:,.2f} ({percentages["short_stock"] + percentages["short_option"]:.1f}% of portfolio)
- Options Exposure: ${summary["options_exposure"]["total_exposure"]:,.2f} ({percentages["long_option"] + percentages["short_option"]:.1f}% of portfolio)
- Cash & Equivalents: ${summary["cash_like_value"]:,.2f} ({percentages["cash"]:.1f}% of portfolio)

Portfolio Allocation:
- Long Stocks: ${values["long_stock"]:,.2f} ({percentages["long_stock"]:.1f}%)
- Long Options: ${values["long_option"]:,.2f} ({percentages["long_option"]:.1f}%)
- Short Stocks: ${values["short_stock"]:,.2f} ({percentages["short_stock"]:.1f}%)
- Short Options: ${values["short_option"]:,.2f} ({percentages["short_option"]:.1f}%)
- Cash: ${values["cash"]:,.2f} ({percentages["cash"]:.1f}%)
- Pending Activity: ${values["pending"]:,.2f} ({percentages["pending"]:.1f}%)

Top Positions (by market value):
"""

        # Add top positions
        for i, pos in enumerate(sorted_positions, 1):
            ticker = pos["ticker"]
            pos_type = pos["position_type"]
            market_value = pos["market_value"]
            weight = pos["weight"] * 100  # Convert to percentage

            if pos_type == "option":
                option_type = pos["option_type"]
                strike = pos["strike"]
                expiry = pos["expiry"]
                delta = pos["delta"]
                context += f"{i}. {ticker} {option_type.upper()} ${strike} {expiry} - ${market_value:,.2f} ({weight:.1f}% of portfolio, delta: {delta:.2f})\n"
            else:
                context += f"{i}. {ticker} - ${market_value:,.2f} ({weight:.1f}% of portfolio)\n"

        return context

    def _process_analysis_response(self, response_text: str) -> dict[str, Any]:
        """
        Process and structure the raw AI response.

        Args:
            response_text: Raw text response from Gemini

        Returns:
            Dictionary with structured analysis sections
        """
        # Simple processing for MVP - future versions can implement more sophisticated parsing
        sections = {
            "risk_assessment": "",
            "sector_concentration": "",
            "diversification": "",
            "recommendations": "",
            "raw_response": response_text,
        }

        # Extract sections based on headers in the response
        current_section = None

        for line_text in response_text.split("\n"):
            line = line_text.strip()

            if "risk assessment" in line.lower():
                current_section = "risk_assessment"
                continue
            elif "sector concentration" in line.lower():
                current_section = "sector_concentration"
                continue
            elif "diversification" in line.lower():
                current_section = "diversification"
                continue
            elif "recommendation" in line.lower():
                current_section = "recommendations"
                continue

            if current_section and line:
                sections[current_section] += line + "\n"

        return sections
