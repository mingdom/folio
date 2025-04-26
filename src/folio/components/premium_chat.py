"""Premium Chat component for the portfolio dashboard."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

from ..logger import logger


def create_premium_chat_component():
    """Create a premium chat component with a sliding panel design."""
    return html.Div(
        [
            # Chat toggle button
            html.Button(
                html.I(className="fas fa-robot"),
                id="premium-chat-toggle",
                className="premium-chat-toggle premium-pulse",
                n_clicks=0,
            ),
            # Chat panel
            html.Div(
                [
                    # Chat header
                    html.Div(
                        [
                            html.H3(
                                [
                                    html.I(className="fas fa-robot me-2"),
                                    "AI Portfolio Advisor",
                                ],
                                className="premium-chat-title",
                            ),
                            html.Button(
                                html.I(className="fas fa-times"),
                                id="premium-chat-close",
                                className="premium-chat-close",
                                n_clicks=0,
                            ),
                        ],
                        className="premium-chat-header",
                    ),
                    # Chat messages container
                    html.Div(
                        [
                            # Welcome message
                            html.Div(
                                [
                                    html.Div(
                                        html.I(className="fas fa-robot"),
                                        className="premium-avatar premium-ai-avatar",
                                    ),
                                    html.Div(
                                        dcc.Markdown(
                                            """
                                            👋 Hello! I'm your AI Portfolio Advisor!

                                            I can help you analyze your portfolio and provide insights on:
                                            - Risk assessment
                                            - Sector concentration
                                            - Diversification
                                            - Improvement recommendations

                                            What would you like to know about your portfolio?
                                            """,
                                            className="premium-message-content",
                                        ),
                                        className="premium-message-bubble premium-ai-bubble",
                                    ),
                                ],
                                className="premium-ai-message",
                            ),
                        ],
                        id="premium-chat-messages",
                        className="premium-chat-messages",
                    ),
                    # Loading indicator
                    html.Div(
                        [
                            dbc.Spinner(
                                color="primary", size="md", spinner_class_name="me-2"
                            ),
                            html.Span("AI is thinking...", className="text-primary"),
                        ],
                        id="premium-chat-loading",
                        className="premium-chat-loading d-none",
                    ),
                    # Chat input area
                    html.Div(
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="premium-chat-input",
                                    placeholder="Ask about your portfolio...",
                                    type="text",
                                    className="premium-chat-input",
                                    autoFocus=False,
                                ),
                                dbc.Button(
                                    html.I(className="fas fa-paper-plane"),
                                    id="premium-chat-send",
                                    className="premium-chat-send",
                                    n_clicks=0,
                                ),
                            ],
                            className="premium-chat-input-group",
                        ),
                        className="premium-chat-input-container",
                    ),
                ],
                id="premium-chat-panel",
                className="premium-chat-panel",
            ),
            # Chat history store
            dcc.Store(id="premium-chat-history", storage_type="session"),
            # Message store for processing
            dcc.Store(id="premium-chat-message-store", storage_type="memory"),
        ],
        id="premium-chat-container",
    )


def register_callbacks(app):
    """Register callbacks for the premium chat component."""

    # Toggle chat panel
    @app.callback(
        [
            Output("premium-chat-panel", "className"),
            Output("main-content", "className"),
            Output("premium-chat-input", "autoFocus", allow_duplicate=True),
            Output(
                "premium-chat-toggle", "style"
            ),  # Add output for toggle button style
        ],
        [
            Input("premium-chat-toggle", "n_clicks"),
            Input("premium-chat-close", "n_clicks"),
        ],
        [
            State("premium-chat-panel", "className"),
            State("main-content", "className"),
        ],
        prevent_initial_call=True,
    )
    def toggle_premium_chat(
        _open_clicks, _close_clicks, current_chat_class, current_main_class
    ):
        """Toggle the premium chat panel when the button is clicked."""
        logger.info(
            f"TOGGLE_PREMIUM_CHAT called with open_clicks: {_open_clicks}, close_clicks: {_close_clicks}"
        )

        # Define styles for visible and hidden toggle button
        visible_style = {"display": "flex"}
        hidden_style = {"display": "none"}

        ctx = dash.callback_context
        if not ctx.triggered:
            logger.info("TOGGLE_PREMIUM_CHAT: No trigger, keeping panel closed")
            return "premium-chat-panel", "main-content-shifted", False, visible_style

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        logger.info(f"TOGGLE_PREMIUM_CHAT: Triggered by {trigger_id}")

        if trigger_id == "premium-chat-toggle":
            # Toggle the panel based on current state
            is_currently_open = "open" in current_chat_class

            if is_currently_open:
                logger.info("TOGGLE_PREMIUM_CHAT: Closing chat panel")
                return (
                    "premium-chat-panel",
                    "main-content-shifted",
                    False,
                    visible_style,
                )
            else:
                logger.info("TOGGLE_PREMIUM_CHAT: Opening chat panel")
                return (
                    "premium-chat-panel open",
                    "main-content-shifted chat-open",
                    True,
                    hidden_style,
                )

        elif trigger_id == "premium-chat-close":
            logger.info("TOGGLE_PREMIUM_CHAT: Closing chat panel")
            return "premium-chat-panel", "main-content-shifted", False, visible_style

        # Default case
        return current_chat_class, current_main_class, False, visible_style

    # Step 1: Send user message and show loading indicator
    @app.callback(
        [
            Output("premium-chat-messages", "children", allow_duplicate=True),
            Output("premium-chat-input", "value", allow_duplicate=True),
            Output("premium-chat-loading", "className", allow_duplicate=True),
            Output("premium-chat-history", "data", allow_duplicate=True),
            Output(
                "premium-chat-message-store", "data"
            ),  # Store the message for processing
        ],
        [
            Input("premium-chat-send", "n_clicks"),
            Input("premium-chat-input", "n_submit"),
        ],
        [
            State("premium-chat-input", "value"),
            State("premium-chat-messages", "children"),
            State("premium-chat-history", "data"),
        ],
        prevent_initial_call=True,
    )
    def send_user_message(
        _send_clicks,
        _input_submit,
        message_text,
        current_messages,
        chat_history,
    ):
        """Send a user message and show loading indicator."""
        if not message_text or message_text.strip() == "":
            logger.info("SEND_USER_MESSAGE: Empty message, not sending")
            return (
                current_messages,
                "",
                "premium-chat-loading d-none",
                chat_history,
                None,
            )

        logger.info(f"SEND_USER_MESSAGE called with message: '{message_text}'")

        # Initialize chat history if needed
        if chat_history is None:
            chat_history = []

        # Get current messages or initialize
        if current_messages is None or len(current_messages) == 0:
            logger.info("SEND_USER_MESSAGE: Initializing empty messages list")
            current_messages = []

        logger.info(
            f"SEND_USER_MESSAGE: Current messages count: {len(current_messages)}"
        )

        # Add user message to display
        user_message = html.Div(
            [
                html.Div(
                    html.I(className="fas fa-user"),
                    className="premium-avatar premium-user-avatar",
                ),
                html.Div(
                    dcc.Markdown(
                        message_text,
                        className="premium-message-content",
                    ),
                    className="premium-message-bubble premium-user-bubble",
                ),
            ],
            className="premium-user-message",
        )

        # Update chat history with user message
        chat_history.append({"role": "user", "content": message_text})

        updated_messages = [*current_messages, user_message]

        # Return immediately with loading indicator visible and store the message
        # This will show the user's message and the loading indicator
        # while the AI is generating a response
        return updated_messages, "", "premium-chat-loading", chat_history, message_text

    # Step 2: Process the message and get AI response
    @app.callback(
        [
            Output("premium-chat-messages", "children", allow_duplicate=True),
            Output("premium-chat-loading", "className", allow_duplicate=True),
            Output("premium-chat-history", "data", allow_duplicate=True),
        ],
        Input("premium-chat-message-store", "data"),
        [
            State("premium-chat-messages", "children"),
            State("premium-chat-history", "data"),
            State("portfolio-groups", "data"),
            State("portfolio-summary", "data"),
        ],
        prevent_initial_call=True,
    )
    def process_ai_response(
        message_text,
        current_messages,
        chat_history,
        groups_data,
        summary_data,
    ):
        """Process the message and get AI response."""
        if not message_text:
            logger.info("PROCESS_AI_RESPONSE: No message to process")
            return current_messages, "premium-chat-loading d-none", chat_history

        logger.info(f"PROCESS_AI_RESPONSE called with message: '{message_text}'")
        logger.info(
            f"PROCESS_AI_RESPONSE has groups_data: {bool(groups_data)}, has summary_data: {bool(summary_data)}"
        )

        # Check if portfolio data is available
        if not groups_data or not summary_data:
            logger.info("PROCESS_AI_RESPONSE: No portfolio data available")
            ai_response = (
                "Please load a portfolio first so I can provide meaningful analysis."
            )
        else:
            try:
                # Import here to avoid circular imports
                from ..ai_utils import prepare_portfolio_data_for_analysis
                from ..data_model import PortfolioGroup, PortfolioSummary
                from ..gemini_client import GeminiClient

                # Check if the message is related to finance/portfolio
                non_financial_keywords = [
                    "weather",
                    "sports",
                    "politics",
                    "movie",
                    "music",
                    "recipe",
                    "cook",
                    "game",
                    "travel",
                    "vacation",
                ]
                is_off_topic = any(
                    keyword in message_text.lower()
                    for keyword in non_financial_keywords
                )

                if is_off_topic:
                    logger.info("PROCESS_AI_RESPONSE: Off-topic message detected")
                    ai_response = (
                        "I'm your portfolio advisor and can only help with financial questions "
                        "related to your investments and portfolio. Please ask me about your "
                        "portfolio, stocks, investment strategies, or financial planning."
                    )
                else:
                    # Prepare portfolio data for analysis
                    groups = [PortfolioGroup.from_dict(g) for g in groups_data]
                    summary = PortfolioSummary.from_dict(summary_data)
                    portfolio_data = prepare_portfolio_data_for_analysis(
                        groups, summary
                    )

                    # Use the synchronous version of the Gemini API call
                    logger.info(
                        "PROCESS_AI_RESPONSE: Calling Gemini API with portfolio data"
                    )
                    try:
                        # Initialize Gemini client
                        logger.info("PROCESS_AI_RESPONSE: Initializing GeminiClient")
                        client = GeminiClient()

                        # Get response from Gemini using the synchronous method
                        logger.info(
                            f"PROCESS_AI_RESPONSE: Calling chat_sync with message: '{message_text}' and {len(chat_history)} history items"
                        )
                        response = client.chat_sync(
                            message_text, chat_history, portfolio_data
                        )

                        # Log the entire response for debugging
                        logger.info(
                            f"PROCESS_AI_RESPONSE: Raw Gemini response: {response}"
                        )

                        if response.get("error", False):
                            logger.error(
                                f"Gemini API error: {response.get('response')}"
                            )
                            ai_response = (
                                "I encountered an error while analyzing your portfolio. "
                                "Please try again with a more specific question."
                            )
                        else:
                            ai_response = response.get(
                                "response", "No response received"
                            )
                            logger.info(
                                f"PROCESS_AI_RESPONSE: Received AI response: {ai_response[:100]}..."
                            )

                        # Log the final AI response that will be displayed
                        logger.info(
                            f"PROCESS_AI_RESPONSE: Final AI response to display: {ai_response[:100]}..."
                        )
                    except Exception as e:
                        logger.error(f"Error calling Gemini API: {e!s}", exc_info=True)
                        ai_response = f"I encountered an error while processing your request: {e!s}. Please try again later."
            except Exception as e:
                logger.error(f"Error in AI chat: {e!s}", exc_info=True)
                ai_response = "I encountered an error while processing your request. Please try again later."

        # Add AI message to display
        ai_message = html.Div(
            [
                html.Div(
                    html.I(className="fas fa-robot"),
                    className="premium-avatar premium-ai-avatar",
                ),
                html.Div(
                    dcc.Markdown(
                        ai_response,
                        className="premium-message-content",
                    ),
                    className="premium-message-bubble premium-ai-bubble",
                ),
            ],
            className="premium-ai-message",
        )

        # Add AI response to chat history
        chat_history.append({"role": "assistant", "content": ai_response})

        # Log the final state before returning
        logger.info(
            f"PROCESS_AI_RESPONSE: Chat history now has {len(chat_history)} items"
        )
        logger.info(
            f"PROCESS_AI_RESPONSE: Updated messages will have {len(current_messages) + 1} items"
        )
        logger.info("PROCESS_AI_RESPONSE: Returning updated messages")

        # Return updated messages with AI response and hide loading indicator
        final_messages = [*current_messages, ai_message]
        logger.info(f"PROCESS_AI_RESPONSE: Final message count: {len(final_messages)}")
        return final_messages, "premium-chat-loading d-none", chat_history


# The register_callbacks function is now the main function above
