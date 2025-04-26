"""Portfolio data processing and CSV loading functionality.

This module provides core functionality for portfolio analysis, including:
- Portfolio data processing and grouping
- CSV loading and parsing
- Cash-like instrument detection
- Portfolio metrics and summary calculations
"""

import os

import pandas as pd
import yaml

from src.stockdata import get_data_fetcher

from .cash_detection import is_cash_or_short_term
from .data_model import (
    ExposureBreakdown,
    PortfolioGroup,
    PortfolioSummary,
    StockPosition,
    create_portfolio_group,
)
from .formatting import format_beta, format_currency
from .logger import logger
from .portfolio_value import (
    calculate_portfolio_metrics,
    calculate_portfolio_values,
    create_value_breakdowns,
    process_option_positions,
    process_stock_positions,
)
from .utils import clean_currency_value, get_beta

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "folio.yaml")
config = {}
if os.path.exists(config_path):
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Failed to load folio.yaml: {e}. Using default configuration.")

# Get the singleton data fetcher instance
data_fetcher = get_data_fetcher(config=config)


def process_portfolio_data(
    df: pd.DataFrame,
    update_prices: bool = True,
) -> tuple[list[PortfolioGroup], PortfolioSummary, list[dict]]:
    """Process portfolio data from a DataFrame into structured groups and summary.

    This function transforms raw portfolio data into an organized structure by:
    1. Validating and cleaning the input data
    2. Identifying cash-like positions (money market funds, etc.)
    3. Grouping related positions (stocks with their options)
    4. Calculating exposure metrics for each position and group
    5. Generating a comprehensive portfolio summary

    The processing flow includes:
    - Validating required columns in the DataFrame
    - Cleaning data (stripping whitespace, handling missing values)
    - Identifying options based on description patterns
    - Processing stock positions with beta calculations
    - Matching options to their underlying stocks
    - Calculating option metrics (delta, notional value, exposures)
    - Creating portfolio groups that combine stocks with their options
    - Identifying cash-like positions for separate tracking
    - Calculating portfolio-level summary statistics

    Args:
        df: A pandas DataFrame containing the portfolio positions, expected to have columns like
            'Symbol', 'Description', 'Quantity', 'Current Value', 'Last Price', 'Type' (account type: Cash/Margin), etc.

    Returns:
        A tuple containing:
        - list[PortfolioGroup]: A list where each element groups a stock and its related options.
        - PortfolioSummary: An object containing aggregated metrics for the entire portfolio.
        - list[dict]: A list of cash-like positions identified during processing.

    Raises:
        ValueError: If the input DataFrame is None, empty, missing required columns, or if no
                    valid portfolio groups can be created after processing.
        RuntimeError: If the `DataFetcher` (needed for beta calculation) is not initialized.

    TODO:
        - Handle cash positions (like SPAXX) explicitly instead of skipping them due to missing quantity.
          Perhaps aggregate them into a separate 'Cash' group or add to the summary.
        - Improve robustness of `is_option_desc` to handle various option formats (weeklies, LEAPS).
        - Make risk-free rate and default implied volatility configurable for delta calculations.
        - Add support for other asset types (bonds, futures, crypto) if needed.
        - Refactor the main loop for clarity and potential performance improvements.
    """
    if df is None or df.empty:
        logger.warning("Input DataFrame is empty or None. Returning empty results.")
        # Return empty results instead of raising an error
        # Create empty exposure breakdowns with all required fields
        empty_exposure = ExposureBreakdown(
            stock_value=0.0,
            stock_beta_adjusted=0.0,
            option_delta_value=0.0,
            option_beta_adjusted=0.0,
            total_value=0.0,
            total_beta_adjusted=0.0,
            description="Empty exposure",
            formula="N/A",
            components={},
        )

        empty_summary = PortfolioSummary(
            total_exposure=0,
            portfolio_beta=0,
            long_exposure=empty_exposure,
            short_exposure=empty_exposure,
            options_exposure=empty_exposure,
            short_percentage=0,
            cash_like_positions=[],
            cash_like_value=0.0,
            cash_like_count=0,
        )
        return [], empty_summary, []

    logger.debug("=== Portfolio Loading Started ===")
    logger.debug(f"Processing portfolio with {len(df)} initial rows")

    # Validate required columns
    required_columns = [
        "Symbol",
        "Description",
        "Quantity",
        "Current Value",
        "Percent Of Account",  # Needed for weights calculation later
        "Last Price",
        "Type",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"Missing required columns: {', '.join(missing_columns)}")
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Clean and prepare data
    logger.debug("Cleaning and validating data...")
    df = df.copy()  # Avoid SettingWithCopyWarning
    df["Symbol"] = df["Symbol"].str.strip()
    df["Type"] = df["Type"].fillna("")  # Ensure Type is never NaN
    df["Description"] = df["Description"].fillna("")  # Ensure Description is never NaN

    # Capture Pending Activity value before filtering it out
    pending_activity_value = 0.0
    pending_activity_rows = df[df["Symbol"] == "Pending Activity"]
    if not pending_activity_rows.empty:
        for _, row in pending_activity_rows.iterrows():
            # Check multiple columns for the pending activity value
            # The column containing the value seems to vary between CSV files
            value_columns = [
                "Current Value",
                "Last Price Change",
                "Today's Gain/Loss Dollar",
            ]

            for col in value_columns:
                if col in row and pd.notna(row[col]) and str(row[col]).strip():
                    try:
                        value = clean_currency_value(row[col])
                        if value != 0:
                            pending_activity_value = (
                                value  # Use the first non-zero value found
                            )
                            logger.debug(
                                f"Found Pending Activity with value: {format_currency(pending_activity_value)} in column '{col}'"
                            )
                            break  # Stop checking other columns once we find a value
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Error parsing Pending Activity value from column '{col}': {e}"
                        )

            if pending_activity_value == 0:
                logger.warning(
                    "No valid Pending Activity value found in any expected column"
                )

    # Filter out invalid entries like "Pending Activity" which aren't actual positions
    invalid_symbols = ["Pending Activity", "021ESC017"]
    valid_rows = ~df["Symbol"].isin(invalid_symbols)
    if (~valid_rows).any():
        filtered_count = (~valid_rows).sum()
        filtered_symbols = df.loc[~valid_rows, "Symbol"].tolist()
        logger.debug(
            f"Filtered out {filtered_count} invalid entries: {filtered_symbols}"
        )
        df = df[valid_rows].reset_index(drop=True)
        logger.debug(f"Continuing with {len(df)} remaining rows")

    # Function to identify options based on description format
    def is_option_desc(desc: str) -> bool:
        """Checks if a description string matches a specific option format.

        Example format: 'TSM APR 17 2025 $190 CALL'

        Args:
            desc: The description string to check.

        Returns:
            True if the description appears to be an option in the expected format, False otherwise.

        TODO:
            - Implement more robust option description detection that handles different formats
              and edge cases, including weekly options, non-standard date formats, and LEAPS.
              Current implementation is very brittle and only works with one specific format (6 parts).
            - Consider using regular expressions for more flexible parsing.
        """
        if not isinstance(desc, str):
            return False
        parts = desc.strip().split()
        # Expecting format: UNDERLYING MONTH DAY YEAR $STRIKE TYPE (6 parts)
        if len(parts) != 6:
            return False
        # Check if the 5th part starts with '$' and the 6th is CALL/PUT
        return parts[4].startswith("$") and parts[5].upper() in ["CALL", "PUT"]

    # Basic portfolio statistics
    total_positions = len(df)
    # Note: We no longer calculate portfolio_value from the CSV as it may be out of date

    # Filter for non-options and options using the description parser
    is_opt_mask = df["Description"].apply(is_option_desc)
    stock_df = df[~is_opt_mask]
    option_df = df[is_opt_mask]

    unique_stocks = len(stock_df["Symbol"].unique())
    # Unique options might be better counted by the full description or parsed details later
    unique_options = len(
        option_df["Description"].unique()
    )  # Using description as proxy

    logger.debug("=== Portfolio Overview ===")
    logger.debug(f"Total Input Rows: {total_positions}")
    logger.debug(f"Identified Stocks Rows: {len(stock_df)}")
    logger.debug(f"Identified Option Rows: {len(option_df)}")
    # We no longer calculate or display the total portfolio value from the CSV
    logger.debug(f"Unique Stock Symbols: {unique_stocks}")
    logger.debug(
        f"Unique Option Descriptions: {unique_options}"
    )  # Might include duplicates if format varies slightly

    # Create a map of stock positions and prices for option delta calculations
    stock_positions = {}
    cash_like_positions = []
    # Create a dictionary to track cash-like positions by ticker for deduplication
    cash_like_by_ticker = {}
    logger.debug("Processing stock-like positions...")
    # Process non-option positions
    for index, row in stock_df.iterrows():
        symbol_raw = row["Symbol"]
        description = row["Description"]

        # Proceed with processing potentially valid stock/ETF positions
        try:
            # Skip invalid symbols
            if (
                pd.isna(symbol_raw)
                or not isinstance(symbol_raw, str)
                or not symbol_raw.strip()
            ):
                logger.debug(f"Row {index}: Invalid symbol: {symbol_raw}. Skipping.")
                continue

            # Clean symbol (remove trailing asterisks for preferred shares)
            symbol = symbol_raw.rstrip("*")

            # Process quantity
            if pd.isna(row["Quantity"]) or row["Quantity"] == "--":
                current_val = clean_currency_value(row["Current Value"])
                if current_val == 0:
                    logger.warning(
                        f"Row {index}: {symbol} has no quantity and zero value. Skipping."
                    )
                    continue
                # Process based on value only
                logger.debug(
                    f"Row {index}: {symbol} missing quantity but has value. Using quantity=0."
                )
                quantity = 0
            else:
                try:
                    # Parse quantity, preserving negative values for short positions
                    raw_quantity = row["Quantity"]
                    # Check if this is a short position (indicated by negative value)
                    quantity = float(raw_quantity)
                    # Convert to int but preserve the sign
                    quantity = int(quantity)

                    logger.debug(f"Row {index}: {symbol} quantity parsed as {quantity}")
                except (ValueError, TypeError):
                    logger.debug(
                        f"Row {index}: {symbol} has invalid quantity: '{row['Quantity']}'. Skipping."
                    )
                    continue

            # Check if this is a known cash-like position
            is_known_cash = is_cash_or_short_term(
                symbol, beta=None, description=description
            )

            # Process price
            if pd.isna(row["Last Price"]) or row["Last Price"] in ("--", ""):
                if is_known_cash:
                    # Use default values for cash-like positions with missing price
                    price = 0.0
                    beta = 0.0
                    is_cash_like = True
                    logger.debug(
                        f"Row {index}: Cash-like position {symbol} missing price. Using defaults."
                    )
                else:
                    # Try to fetch the current price for non-cash positions with missing price
                    try:
                        df = data_fetcher.fetch_data(symbol, period="1d")
                        if not df.empty:
                            price = df.iloc[-1]["Close"]
                            logger.info(
                                f"Row {index}: Updated price for {symbol}: {price}"
                            )
                        else:
                            logger.warning(
                                f"Row {index}: Could not fetch price for {symbol}. Skipping."
                            )
                            continue
                    except Exception as e:
                        logger.warning(
                            f"Row {index}: Error fetching price for {symbol}: {e}. Skipping."
                        )
                        continue
            else:
                price = clean_currency_value(row["Last Price"])
                if price < 0:
                    logger.debug(
                        f"Row {index}: {symbol} has negative price ({price}). Skipping."
                    )
                    continue
                elif price == 0:
                    # Try to fetch the current price if the price is zero
                    try:
                        logger.debug(
                            f"Row {index}: {symbol} has zero price. Attempting to fetch current price."
                        )
                        df = data_fetcher.fetch_data(symbol, period="1d")
                        if not df.empty:
                            price = df.iloc[-1]["Close"]
                            logger.info(
                                f"Row {index}: Updated price for {symbol}: {price}"
                            )
                        else:
                            logger.warning(
                                f"Row {index}: Could not fetch price for {symbol}. Calculations may be affected."
                            )
                    except Exception as e:
                        logger.warning(
                            f"Row {index}: Error fetching price for {symbol}: {e}. Calculations may be affected."
                        )

            # Calculate position value
            cleaned_current_value = clean_currency_value(row["Current Value"])
            value_to_use = (
                price * quantity
                if quantity != 0 and price != 0
                else cleaned_current_value
            )

            # Get Beta - requires valid ticker and fetcher
            beta = get_beta(symbol, description)

            # Determine if position is cash-like
            is_cash_like = is_cash_or_short_term(
                symbol, beta=beta, description=description
            )

            if is_cash_like:
                # Process cash-like position
                logger.debug(
                    f"Identified cash-like position: {symbol}, Value: {format_currency(value_to_use)}"
                )

                # Add to existing cash position or create new one
                if symbol in cash_like_by_ticker:
                    cash_like_by_ticker[symbol]["market_value"] += value_to_use
                    if quantity != 0:
                        cash_like_by_ticker[symbol]["quantity"] += quantity
                    cash_like_by_ticker[symbol]["beta_adjusted_exposure"] = (
                        cash_like_by_ticker[symbol]["market_value"] * beta
                    )
                else:
                    # Create new cash-like position
                    cash_like_position = {
                        "ticker": symbol,
                        "quantity": quantity,
                        "market_value": value_to_use,  # Keep market_value for cash positions
                        "beta": beta,
                        "beta_adjusted_exposure": value_to_use * beta,
                        "description": description,
                        "price": price,  # Store the price
                    }
                    cash_like_by_ticker[symbol] = cash_like_position
                    cash_like_positions.append(cash_like_position)
            else:
                # Process regular stock position
                percent_of_account = 0.0
                if (
                    pd.notna(row["Percent Of Account"])
                    and row["Percent Of Account"] != "--"
                ):
                    percent_of_account = (
                        float(str(row["Percent Of Account"]).replace("%", "")) / 100.0
                    )

                # Sector determination removed - will be implemented in a separate task

                # Get cost basis if available
                cost_basis = 0.0
                if (
                    pd.notna(row["Average Cost Basis"])
                    and row["Average Cost Basis"] != "--"
                ):
                    try:
                        cost_basis = clean_currency_value(row["Average Cost Basis"])
                    except (ValueError, TypeError):
                        logger.debug(
                            f"Row {index}: {symbol} has invalid cost basis: '{row['Average Cost Basis']}'. Using 0.0."
                        )

                stock_positions[symbol] = {
                    "price": price,
                    "quantity": quantity,
                    "value": value_to_use,
                    "beta": beta,
                    "percent_of_account": percent_of_account,
                    "account_type": row["Type"],
                    "description": description,
                    "cost_basis": cost_basis,
                }

        except (ValueError, TypeError) as e:
            # Handle data conversion and type errors
            logger.debug(
                f"Row {index}: Error processing '{symbol_raw}': {e}. Skipping row."
            )
            continue
        except Exception as e:
            # Catch unexpected errors
            logger.error(
                f"Row {index}: Unexpected error for '{symbol_raw}': {e}", exc_info=True
            )
            continue

    # Group by underlying symbol (using stock symbols as base)
    logger.debug("=== Position Grouping and Analysis ===")
    groups = []
    processed_option_indices = (
        set()
    )  # Keep track of options already assigned to a group

    # Import the canonical function for calculating net exposure

    # Process stock positions first to form the basis of groups
    for symbol, stock_info in stock_positions.items():
        try:
            logger.debug(f"Processing Group for Underlying: {symbol}")

            # Create stock position data structure for the group
            value = stock_info["value"]
            quantity = stock_info["quantity"]
            beta = stock_info["beta"]
            percent_of_account = stock_info["percent_of_account"]

            logger.debug("  Stock Details:")
            logger.debug(f"    Symbol: {symbol}")
            logger.debug(f"    Quantity: {quantity:,.0f}")
            logger.debug(f"    Market Value: {format_currency(value)}")
            logger.debug(f"    Beta: {format_beta(beta)}")
            logger.debug(f"    Beta-Adjusted Exposure: {format_currency(value * beta)}")
            logger.debug(f"    Percent of Account: {percent_of_account:.2%}")

            stock_data_for_group = {
                "ticker": symbol,
                "quantity": quantity,
                "beta": beta,
                "market_exposure": value,  # This is the market exposure (quantity * price)
                "beta_adjusted_exposure": value * beta,
                "description": stock_info.get("description", ""),
                "price": stock_info["price"],  # Store the price
                "cost_basis": stock_info.get("cost_basis", 0.0),  # Store the cost basis
            }

            # Find and process related options from the filtered option_df
            option_data_for_group = []
            # Filter option_df for options whose description contains the stock symbol as the first word
            # This is a potential point of failure if descriptions aren't standard.
            potential_options = option_df[
                option_df["Description"].str.startswith(symbol + " ")
            ]

            logger.debug(
                f"  Found {len(potential_options)} potential option(s) for {symbol} based on description prefix."
            )

            # Import the necessary functions
            from .options import process_options
            from .validation import extract_option_data

            # Extract and validate option data using our utility function
            # This replaces all the manual validation and extraction code
            options_data = extract_option_data(
                potential_options,
                # Filter function to skip already processed options
                filter_func=lambda row: row.name not in processed_option_indices,
                include_row_index=True,
            )

            # Process all options at once using our new function
            prices = {symbol: stock_info["price"]}  # Use the fetched stock price
            betas = {symbol: beta}  # Use the beta we already calculated

            try:
                processed_options = process_options(options_data, prices, betas)

                # Filter out options with mismatched underlying
                processed_options = [
                    opt for opt in processed_options if opt["ticker"] == symbol
                ]

                # Convert to the format expected by create_portfolio_group
                option_data_for_group = []
                for opt in processed_options:
                    # Mark the option as processed
                    row_index = next(
                        data["row_index"]
                        for data in options_data
                        if data["description"] == opt["description"]
                        and data["quantity"] == opt["quantity"]
                    )
                    processed_option_indices.add(row_index)

                    # Log the option details
                    logger.debug(f"    Option Added: {opt['description']}")
                    logger.debug(f"      Quantity: {opt['quantity']:,.0f}")
                    logger.debug(f"      Delta: {opt['delta']:.3f}")
                    logger.debug(
                        f"      Notional Value: {format_currency(opt['notional_value'])}"
                    )
                    logger.debug(
                        f"      Delta Exposure: {format_currency(opt['delta_exposure'])}"
                    )
                    logger.debug(
                        f"      Beta-Adjusted Exposure: {format_currency(opt['beta_adjusted_exposure'])}"
                    )

                    # Add to the group data
                    option_data_for_group.append(
                        {
                            "ticker": opt["ticker"],
                            "option_symbol": opt["option_symbol"],
                            "description": opt["description"],
                            "quantity": opt["quantity"],
                            "beta": opt["beta"],
                            "beta_adjusted_exposure": opt["beta_adjusted_exposure"],
                            "market_exposure": opt[
                                "delta_exposure"
                            ],  # Delta-adjusted exposure is the market exposure
                            "strike": opt["strike"],
                            "expiry": opt["expiry"],
                            "option_type": opt["option_type"],
                            "delta": opt["delta"],
                            "delta_exposure": opt["delta_exposure"],
                            "notional_value": opt["notional_value"],
                            "price": opt["price"],
                            "cost_basis": opt.get(
                                "cost_basis", opt["price"]
                            ),  # Use price as default cost basis
                        }
                    )
            except Exception as e:
                logger.error(
                    f"    Error processing options for {symbol}: {e}", exc_info=True
                )
                option_data_for_group = []  # Use an empty list if processing fails

            # Create portfolio group using the dedicated function from data_model
            # Ensure the create function handles cases with stock only, or stock + options
            group = create_portfolio_group(stock_data_for_group, option_data_for_group)
            if group:
                groups.append(group)
                logger.debug(
                    f"  Successfully created group for {symbol} with {len(option_data_for_group)} options."
                )
            else:
                logger.warning(
                    f"  Failed to create a portfolio group for {symbol}. Check 'create_portfolio_group' logic."
                )

        except Exception as group_err:
            # Catch errors during the processing of an entire stock group
            logger.error(
                f"Critical error processing group for underlying '{symbol}': {group_err}",
                exc_info=True,
            )
            # Decide if one group failure should stop everything or just skip the group
            # If it's the first group failing, maybe raise to avoid empty results
            if not groups:
                logger.critical(
                    "First portfolio group failed processing, cannot continue with potentially empty portfolio."
                )
                raise  # Stop processing if the very first group fails
            else:
                logger.warning(f"Skipping group '{symbol}' due to error.")
                continue  # Continue processing other groups

    # Process any options that were not matched to a stock position
    unprocessed_options = set(option_df.index) - processed_option_indices
    if unprocessed_options:
        logger.debug(
            f"{len(unprocessed_options)} options without matching stock positions found - creating standalone option groups"
        )

        # Group unprocessed options by underlying symbol
        orphaned_options_by_underlying = {}
        for idx in unprocessed_options:
            opt_row = option_df.loc[idx]
            opt_desc = opt_row["Description"]

            # Extract the underlying symbol from the description
            # Description format is expected to be: "SPY JUN 20 2025 $580 CALL"
            parts = opt_desc.strip().split()
            if len(parts) >= 1:
                underlying = parts[0]  # First part should be the underlying symbol

                # Add to the dictionary, grouped by underlying
                if underlying not in orphaned_options_by_underlying:
                    orphaned_options_by_underlying[underlying] = []
                orphaned_options_by_underlying[underlying].append(idx)
                logger.debug(
                    f"  - Orphaned option: {opt_desc} (Underlying: {underlying})"
                )
            else:
                logger.warning(
                    f"  - Could not extract underlying from option description: {opt_desc}"
                )

        # Process each group of orphaned options
        for underlying, option_indices in orphaned_options_by_underlying.items():
            logger.debug(
                f"Creating standalone option group for {underlying} with {len(option_indices)} options"
            )

            # Import the necessary functions
            from .options import process_options
            from .validation import extract_option_data

            # Extract option data for the specified indices
            orphaned_df = option_df.loc[option_indices]

            # Extract and validate option data using our utility function
            options_data = extract_option_data(orphaned_df, include_row_index=True)

            # Get beta for the underlying
            try:
                beta = get_beta(underlying)
            except ValueError as beta_err:
                # Only handle specific ValueError cases that we know how to handle
                if "No historical data available" in str(beta_err):
                    logger.warning(
                        f"No historical data for {underlying}: {beta_err}. Cannot calculate beta."
                    )
                    # Re-raise with more context to be handled by the caller
                    raise ValueError(
                        f"Cannot process orphaned options for {underlying} without beta data"
                    ) from beta_err
                else:
                    # Re-raise other ValueError cases
                    raise
            except Exception as beta_err:
                # Log unexpected errors and re-raise
                logger.error(
                    f"Unexpected error getting beta for {underlying}: {beta_err}",
                    exc_info=True,
                )
                raise

            # Get the latest price for the underlying
            try:
                # Try to fetch the latest price
                price_data = data_fetcher.fetch_data(underlying, period="1d")
                if price_data is not None and not price_data.empty:
                    underlying_price = price_data.iloc[-1]["Close"]
                    if underlying_price <= 0:
                        # If we get an invalid price, we can't process the options
                        logger.error(
                            f"Invalid price for {underlying}: {underlying_price}"
                        )
                        raise ValueError(
                            f"Cannot process options for {underlying} with invalid price: {underlying_price}"
                        )
                else:
                    # If we can't get the price data, we can't process the options
                    logger.error(f"Could not fetch price data for {underlying}")
                    raise ValueError(
                        f"Cannot process options for {underlying} without price data"
                    )
            except (pd.errors.EmptyDataError, KeyError) as data_err:
                # Handle specific data errors
                logger.error(f"Data error for {underlying}: {data_err}", exc_info=True)
                raise ValueError(
                    f"Cannot process options for {underlying} due to data error"
                ) from data_err
            except Exception as price_err:
                # Log unexpected errors and re-raise
                logger.error(
                    f"Error fetching price for {underlying}: {price_err}", exc_info=True
                )
                raise ValueError(
                    f"Cannot process options for {underlying} without price data"
                ) from price_err

            # Process all options at once using our new function
            prices = {underlying: underlying_price}
            betas = {underlying: beta}

            try:
                processed_options = process_options(options_data, prices, betas)

                # Convert to the format expected by create_portfolio_group
                option_data_for_group = []
                for opt in processed_options:
                    # Mark the option as processed
                    row_index = next(
                        data["row_index"]
                        for data in options_data
                        if data["description"] == opt["description"]
                        and data["quantity"] == opt["quantity"]
                    )
                    processed_option_indices.add(row_index)

                    # Log the option details
                    logger.debug(f"Orphaned Option Added: {opt['description']}")
                    logger.debug(f"  Quantity: {opt['quantity']:,.0f}")
                    logger.debug(f"  Delta: {opt['delta']:.3f}")
                    logger.debug(
                        f"  Notional Value: {format_currency(opt['notional_value'])}"
                    )
                    logger.debug(
                        f"  Delta Exposure: {format_currency(opt['delta_exposure'])}"
                    )
                    logger.debug(
                        f"  Beta-Adjusted Exposure: {format_currency(opt['beta_adjusted_exposure'])}"
                    )

                    # Add to the group data
                    option_data_for_group.append(
                        {
                            "ticker": opt["ticker"],
                            "option_symbol": opt["option_symbol"],
                            "description": opt["description"],
                            "quantity": opt["quantity"],
                            "beta": opt["beta"],
                            "beta_adjusted_exposure": opt["beta_adjusted_exposure"],
                            "market_exposure": opt[
                                "delta_exposure"
                            ],  # Delta-adjusted exposure is the market exposure
                            "strike": opt["strike"],
                            "expiry": opt["expiry"],
                            "option_type": opt["option_type"],
                            "delta": opt["delta"],
                            "delta_exposure": opt["delta_exposure"],
                            "notional_value": opt["notional_value"],
                            "price": opt["price"],
                            "cost_basis": opt.get(
                                "cost_basis", opt["price"]
                            ),  # Use price as default cost basis
                        }
                    )
            except Exception as e:
                logger.error(
                    f"Error processing orphaned options for {underlying}: {e}",
                    exc_info=True,
                )
                option_data_for_group = []  # Use an empty list if processing fails

            # Create a portfolio group with just options (no stock position)
            if option_data_for_group:
                # For options-only groups, we'll create the group with a zero-quantity stock position
                # We need to pass a minimal stock_data dictionary to create_portfolio_group
                # but we'll set the quantity to 0 so it doesn't affect calculations
                stock_data_for_group = {
                    "ticker": underlying,
                    "quantity": 0,
                    "beta": beta,
                    "market_exposure": 0,
                    "beta_adjusted_exposure": 0,
                    "description": f"{underlying} (Options Only)",
                    "price": 0,
                }

                # Create the group
                group = create_portfolio_group(
                    stock_data_for_group, option_data_for_group
                )
                if group:
                    # We'll keep the stock_position with quantity=0 to maintain the ticker information
                    # This ensures the group is properly displayed in the UI
                    groups.append(group)
                    logger.debug(
                        f"Successfully created options-only group for {underlying} with {len(option_data_for_group)} options"
                    )

                    # Log the group details
                    logger.debug(f"Group details for {underlying}:")
                    logger.debug(
                        f"  Net Exposure: {format_currency(group.net_exposure)}"
                    )
                    logger.debug(f"  Beta: {format_beta(group.beta)}")
                    logger.debug(
                        f"  Beta-Adjusted Exposure: {format_currency(group.beta_adjusted_exposure)}"
                    )
                    logger.debug(
                        f"  Options Delta Exposure: {format_currency(group.options_delta_exposure)}"
                    )
                    logger.debug(f"  Number of Options: {len(group.option_positions)}")
                    logger.debug(
                        f"  Stock Position: {'Yes' if group.stock_position else 'No'}"
                    )
                    if group.stock_position:
                        logger.debug(
                            f"  Stock Quantity: {group.stock_position.quantity}"
                        )
                        logger.debug(
                            f"  Stock Market Exposure: {format_currency(group.stock_position.market_exposure)}"
                        )
                        logger.debug(
                            f"  Stock Beta-Adjusted Exposure: {format_currency(group.stock_position.beta_adjusted_exposure)}"
                        )
                    logger.debug(
                        f"  Option Types: {group.call_count} calls, {group.put_count} puts"
                    )
                else:
                    logger.warning(
                        f"Failed to create options-only group for {underlying}"
                    )

    # Check if we have any valid groups after processing
    if not groups:
        logger.warning(
            "No valid portfolio groups were created after processing. This may be an all-cash portfolio."
        )
        # Instead of raising an error, proceed with just cash-like positions if any exist
        if not cash_like_positions:
            logger.warning(
                "No cash-like positions found either. Returning empty summary."
            )
            # Create empty exposure breakdowns with all required fields
            empty_exposure = ExposureBreakdown(
                stock_exposure=0.0,
                stock_beta_adjusted=0.0,
                option_delta_exposure=0.0,
                option_beta_adjusted=0.0,
                total_exposure=0.0,
                total_beta_adjusted=0.0,
                description="Empty exposure",
                formula="N/A",
                components={},
            )

            empty_summary = PortfolioSummary(
                net_market_exposure=0.0,
                portfolio_beta=0.0,
                long_exposure=empty_exposure,
                short_exposure=empty_exposure,
                options_exposure=empty_exposure,
                short_percentage=0.0,
                cash_like_positions=[],
                cash_like_value=0.0,
                cash_like_count=0,
                cash_percentage=0.0,
                stock_value=0.0,
                option_value=0.0,
                portfolio_estimate_value=pending_activity_value,  # Include pending activity value
            )
            return [], empty_summary, []

    # Update prices if requested
    if update_prices:
        logger.debug("Updating prices in portfolio groups...")
        groups = update_all_prices(groups)

    # Calculate portfolio summary using the final list of groups
    logger.debug("Calculating final portfolio summary...")
    try:
        summary = calculate_portfolio_summary(
            groups, cash_like_positions, pending_activity_value
        )
        if pending_activity_value > 0:
            logger.debug(
                f"Including Pending Activity value: {format_currency(pending_activity_value)}"
            )
        logger.debug("Portfolio summary calculated successfully.")
    except Exception as summary_err:
        logger.error(
            f"Failed to calculate portfolio summary: {summary_err}", exc_info=True
        )
        # Decide how to handle summary failure - raise or return groups with None summary?
        raise  # Raising seems safer to indicate incomplete results

    logger.info(
        f"=== Portfolio Loading Finished: {len(groups)} groups created, {len(cash_like_positions)} cash-like positions identified. ==="
    )
    return groups, summary, cash_like_positions


def calculate_portfolio_summary(
    groups: list[PortfolioGroup],
    cash_like_positions: list[dict] | None = None,
    pending_activity_value: float = 0.0,
) -> PortfolioSummary:
    """Calculate comprehensive summary metrics for the entire portfolio.

    This function aggregates data from all portfolio groups to produce a complete
    portfolio summary with exposure breakdowns, risk metrics, and cash analysis.

    The calculation process:
    1. Processes each portfolio group (stock + options)
    2. Categorizes exposures into long and short components
    3. Calculates beta-adjusted values for risk assessment
    4. Computes portfolio-level statistics and ratios
    5. Incorporates cash-like positions into the analysis

    Exposure categorization rules:
    - Long stocks → long exposure
    - Short stocks → short exposure
    - Long calls & short puts → long options exposure
    - Short calls & long puts → short options exposure

    IMPORTANT: Short values are stored as negative numbers throughout this function
    and in the returned PortfolioSummary object.

    Args:
        groups: List of PortfolioGroup objects containing processed positions
        cash_like_positions: List of dictionaries representing cash-like positions
                           (money markets, short-term bonds, etc.)
        pending_activity_value: Value of pending activity

    Returns:
        A PortfolioSummary object with calculated metrics including:
        - Total values (net and absolute)
        - Portfolio beta
        - Exposure breakdowns (long/short/options)
        - Risk ratios (short percentage, exposure reduction)
        - Cash position analysis

    Raises:
        RuntimeError: If calculation fails due to data issues
    """
    logger.debug(f"Starting portfolio summary calculations for {len(groups)} groups.")

    # Validate inputs
    if not groups and not cash_like_positions and pending_activity_value == 0.0:
        logger.warning(
            "Cannot calculate summary for an empty portfolio. Returning default summary."
        )
        # Return a default or empty summary object to avoid downstream errors
        empty_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=0.0,
            option_beta_adjusted=0.0,
            total_exposure=0.0,
            total_beta_adjusted=0.0,
            description="Empty exposure",
            formula="N/A",
            components={},
        )

        return PortfolioSummary(
            net_market_exposure=0.0,
            portfolio_beta=0.0,
            long_exposure=empty_exposure,
            short_exposure=empty_exposure,
            options_exposure=empty_exposure,
            short_percentage=0.0,
            cash_like_positions=[],
            cash_like_value=0.0,
            cash_like_count=0,
            cash_percentage=0.0,
            stock_value=0.0,
            option_value=0.0,
            portfolio_estimate_value=pending_activity_value,  # Include pending activity value
        )

    # Initialize cash-like positions list if None
    if cash_like_positions is None:
        cash_like_positions = []

    # Recalculate net exposure for each group using the canonical function
    logger.debug(
        "Recalculating net exposure for all groups using the canonical function"
    )
    for group in groups:
        # Store the original net exposure for logging
        original_net_exposure = group.net_exposure

        # Recalculate net exposure using the canonical function
        group.recalculate_net_exposure()

        # Log the change if there's a significant difference
        if abs(original_net_exposure - group.net_exposure) > 0.01:
            logger.debug(
                f"Group {group.ticker}: Net exposure recalculated from {format_currency(original_net_exposure)} to {format_currency(group.net_exposure)}"
            )

    try:
        # Process positions using modular functions
        long_stocks, short_stocks = process_stock_positions(groups)
        long_options, short_options = process_option_positions(groups)

        # Create value breakdowns
        long_value, short_value, options_value = create_value_breakdowns(
            long_stocks, short_stocks, long_options, short_options
        )

        # Calculate portfolio metrics
        net_market_exposure, portfolio_beta, short_percentage = (
            calculate_portfolio_metrics(long_value, short_value)
        )

        # Calculate portfolio values
        (
            stock_value,
            option_value,
            cash_like_value,
            portfolio_estimate_value,
            cash_percentage,
        ) = calculate_portfolio_values(
            groups, cash_like_positions, pending_activity_value
        )

        # Convert cash-like positions to StockPosition objects for consistent handling
        cash_like_stock_positions = [
            StockPosition(
                ticker=pos["ticker"],
                quantity=pos["quantity"],
                beta=pos["beta"],
                market_exposure=pos[
                    "market_value"
                ],  # Cash has no market exposure, but we store the value
                beta_adjusted_exposure=pos["beta_adjusted_exposure"],
                price=pos.get("price", 0.0),  # Get price if it exists
                cost_basis=pos.get("price", 0.0),  # For cash, use price as cost basis
            )
            for pos in cash_like_positions
        ]

        # Get current timestamp in ISO format
        from datetime import UTC, datetime

        current_time = datetime.now(UTC).isoformat()

        # Create and return the portfolio summary
        summary = PortfolioSummary(
            net_market_exposure=net_market_exposure,
            portfolio_beta=portfolio_beta,
            long_exposure=long_value,  # Using value breakdown
            short_exposure=short_value,  # Using value breakdown
            options_exposure=options_value,  # Using value breakdown
            short_percentage=short_percentage,
            cash_like_positions=cash_like_stock_positions,
            cash_like_value=cash_like_value,
            cash_like_count=len(cash_like_positions),
            cash_percentage=cash_percentage,
            stock_value=stock_value,
            option_value=option_value,
            pending_activity_value=pending_activity_value,
            portfolio_estimate_value=portfolio_estimate_value,
            price_updated_at=current_time,
        )

        logger.debug("Portfolio summary created successfully.")
        log_summary_details(summary)
        return summary

    except Exception as e:
        logger.error("Error calculating portfolio summary", exc_info=True)
        raise RuntimeError("Failed to calculate portfolio summary") from e


def update_portfolio_prices(
    portfolio_groups: list[PortfolioGroup], data_fetcher=None
) -> str:
    """Update prices for all positions in the portfolio groups.

    Args:
        portfolio_groups: List of portfolio groups to update prices for
        data_fetcher: Optional data fetcher to use for price updates

    Returns:
        ISO format timestamp of when prices were updated
    """
    from datetime import UTC, datetime

    # Use the default data fetcher if none is provided
    if data_fetcher is None:
        data_fetcher = get_data_fetcher()

    # Extract unique tickers from all positions
    tickers = set()
    for group in portfolio_groups:
        # Add stock position ticker
        if group.stock_position:
            tickers.add(group.stock_position.ticker)

        # Add option position tickers
        for option in group.option_positions:
            tickers.add(option.ticker)

    # Remove cash-like instruments as we don't need to update their prices
    tickers = [ticker for ticker in tickers if not is_cash_or_short_term(ticker)]

    if not tickers:
        logger.info("No tickers to update prices for")
        return datetime.now(UTC).isoformat()

    # Fetch latest prices for all tickers
    logger.info(f"Fetching latest prices for {len(tickers)} tickers")

    # Use a small period to get just the latest price
    latest_prices = {}
    for ticker in tickers:
        try:
            # Fetch data for the last day
            df = data_fetcher.fetch_data(ticker, period="1d")
            if not df.empty:
                # Get the latest close price
                latest_prices[ticker] = df.iloc[-1]["Close"]
                logger.debug(f"Updated price for {ticker}: {latest_prices[ticker]}")
            else:
                logger.warning(f"No price data available for {ticker}")
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e!s}")

    # Update prices for all positions
    for group in portfolio_groups:
        # Update stock position price
        if group.stock_position and group.stock_position.ticker in latest_prices:
            group.stock_position.price = latest_prices[group.stock_position.ticker]
            # Update market exposure and market value based on new price
            group.stock_position.market_exposure = (
                group.stock_position.price * group.stock_position.quantity
            )
            group.stock_position.market_value = (
                group.stock_position.price * group.stock_position.quantity
            )
            group.stock_position.beta_adjusted_exposure = (
                group.stock_position.market_exposure * group.stock_position.beta
            )

        # Update option position prices
        for option in group.option_positions:
            if option.ticker in latest_prices:
                option.price = latest_prices[option.ticker]
                # Update market_value based on new price
                option.market_value = option.price * option.quantity
                # We don't update market_exposure for options as it's based on notional value

    # Recalculate net exposure for each group using the canonical function
    logger.debug("Recalculating net exposure for all groups after price updates")
    for group in portfolio_groups:
        # Store the original net exposure for logging
        original_net_exposure = group.net_exposure

        # Recalculate net exposure using the canonical function
        group.recalculate_net_exposure()

        # Log the change if there's a significant difference
        if abs(original_net_exposure - group.net_exposure) > 0.01:
            logger.debug(
                f"Group {group.ticker}: Net exposure recalculated from {format_currency(original_net_exposure)} to {format_currency(group.net_exposure)}"
            )

    # Return the current timestamp
    current_time = datetime.now(UTC).isoformat()
    logger.info(f"Prices updated at {current_time}")
    return current_time


def update_zero_price_positions(
    portfolio_groups: list[PortfolioGroup], data_fetcher=None
) -> list[PortfolioGroup]:
    """Update positions with zero prices by fetching current market prices.

    Args:
        portfolio_groups: List of portfolio groups to update
        data_fetcher: Optional data fetcher to use for price updates

    Returns:
        Updated list of portfolio groups
    """
    logger.debug("Updating positions with zero prices...")

    # Use the default data fetcher if none is provided
    if data_fetcher is None:
        data_fetcher = get_data_fetcher()

    # Find positions with zero prices
    zero_price_tickers = []
    for group in portfolio_groups:
        if group.stock_position and group.stock_position.price == 0:
            zero_price_tickers.append(group.ticker)

    if not zero_price_tickers:
        logger.debug("No positions with zero prices found.")
        return portfolio_groups

    logger.info(
        f"Found {len(zero_price_tickers)} positions with zero prices: {', '.join(zero_price_tickers)}"
    )

    # Fetch prices for tickers with zero prices
    for ticker in zero_price_tickers:
        try:
            # Fetch data for the last day
            df = data_fetcher.fetch_data(ticker, period="1d")
            if not df.empty:
                # Get the latest close price
                new_price = df.iloc[-1]["Close"]
                logger.info(f"Fetched price for {ticker}: {new_price}")

                # Update the price in all matching groups
                for group in portfolio_groups:
                    if group.ticker == ticker and group.stock_position:
                        # Update the stock position
                        group.stock_position.price = new_price
                        group.stock_position.market_exposure = (
                            new_price * group.stock_position.quantity
                        )
                        group.stock_position.market_value = (
                            new_price * group.stock_position.quantity
                        )
                        group.stock_position.beta_adjusted_exposure = (
                            group.stock_position.market_exposure
                            * group.stock_position.beta
                        )

                        logger.info(f"Updated price for {ticker} to {new_price}")
            else:
                logger.warning(f"Could not fetch price data for {ticker}")
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e!s}")

    # Recalculate net exposure for each group using the canonical function
    logger.debug("Recalculating net exposure for groups with updated prices")
    for group in portfolio_groups:
        if group.ticker in zero_price_tickers:
            # Store the original net exposure for logging
            original_net_exposure = group.net_exposure

            # Recalculate net exposure using the canonical function
            group.recalculate_net_exposure()

            # Log the change if there's a significant difference
            if abs(original_net_exposure - group.net_exposure) > 0.01:
                logger.debug(
                    f"Group {group.ticker}: Net exposure recalculated from {format_currency(original_net_exposure)} to {format_currency(group.net_exposure)}"
                )

    return portfolio_groups


def update_all_prices(
    portfolio_groups: list[PortfolioGroup], data_fetcher=None
) -> list[PortfolioGroup]:
    """Update prices for all positions by fetching current market prices.

    Args:
        portfolio_groups: List of portfolio groups to update
        data_fetcher: Optional data fetcher to use for price updates

    Returns:
        Updated list of portfolio groups
    """
    logger.debug("Updating prices for all positions...")

    # Use the default data fetcher if none is provided
    if data_fetcher is None:
        data_fetcher = get_data_fetcher()

    # Get all tickers that need price updates
    tickers_to_update = []
    for group in portfolio_groups:
        if group.stock_position:
            tickers_to_update.append(group.ticker)

    if not tickers_to_update:
        logger.debug("No positions to update prices for.")
        return portfolio_groups

    logger.info(f"Updating prices for {len(tickers_to_update)} positions")

    # Fetch prices for all tickers
    for ticker in tickers_to_update:
        try:
            # Fetch data for the last day
            df = data_fetcher.fetch_data(ticker, period="1d")
            if not df.empty:
                # Get the latest close price
                new_price = df.iloc[-1]["Close"]
                logger.debug(f"Fetched price for {ticker}: {new_price}")

                # Update the price in all matching groups
                for group in portfolio_groups:
                    if group.ticker == ticker and group.stock_position:
                        # Update the stock position
                        group.stock_position.price = new_price
                        group.stock_position.market_exposure = (
                            new_price * group.stock_position.quantity
                        )
                        group.stock_position.market_value = (
                            new_price * group.stock_position.quantity
                        )
                        group.stock_position.beta_adjusted_exposure = (
                            group.stock_position.market_exposure
                            * group.stock_position.beta
                        )

                        logger.debug(f"Updated price for {ticker} to {new_price}")
            else:
                logger.warning(f"Could not fetch price data for {ticker}")
        except Exception as e:
            logger.error(f"Error fetching price for {ticker}: {e!s}")

    return portfolio_groups


def update_portfolio_summary_with_prices(
    portfolio_groups: list[PortfolioGroup], summary: PortfolioSummary, data_fetcher=None
) -> PortfolioSummary:
    """Update the portfolio summary with the latest prices.

    Args:
        portfolio_groups: List of portfolio groups to update prices for
        summary: The current portfolio summary
        data_fetcher: Optional data fetcher to use for price updates

    Returns:
        Updated portfolio summary with the latest prices
    """
    # Update prices for all positions
    price_updated_at = update_portfolio_prices(portfolio_groups, data_fetcher)

    # Recalculate the portfolio summary with the updated prices
    # Preserve the pending activity value from the original summary
    updated_summary = calculate_portfolio_summary(
        portfolio_groups, summary.cash_like_positions, summary.pending_activity_value
    )

    # Set the price_updated_at timestamp
    updated_summary.price_updated_at = price_updated_at

    return updated_summary


def log_summary_details(summary: PortfolioSummary):
    """Log detailed portfolio summary information for monitoring and debugging.

    This function outputs formatted portfolio metrics to the logger, including:
    - Portfolio valuation (net and absolute)
    - Risk metrics (beta, exposure percentages)
    - Cash position details
    - Exposure breakdowns (long, short, options)

    Args:
        summary: The PortfolioSummary object containing calculated metrics
    """
    # Portfolio overview
    logger.debug("--- Portfolio Summary ---")
    if summary.price_updated_at:
        logger.debug(f"Prices Last Updated: {summary.price_updated_at}")
    logger.debug(f"Net Market Exposure: {format_currency(summary.net_market_exposure)}")

    logger.debug(
        f"Portfolio Estimated Value: {format_currency(summary.portfolio_estimate_value)}"
    )
    logger.debug(f"Stock Value: {format_currency(summary.stock_value)}")
    logger.debug(f"Option Value: {format_currency(summary.option_value)}")
    if summary.pending_activity_value != 0.0:
        logger.debug(
            f"Pending Activity: {format_currency(summary.pending_activity_value)}"
        )
    logger.debug(f"Beta: {format_beta(summary.portfolio_beta)}")
    logger.debug(f"Short %: {summary.short_percentage:.1f}%")
    logger.debug(f"Cash %: {summary.cash_percentage:.1f}%")

    # Cash positions
    logger.debug(
        f"Cash: {format_currency(summary.cash_like_value)} ({summary.cash_like_count} positions)"
    )

    # Long exposure
    logger.debug("Long Exposure:")
    logger.debug(f"  Total: {format_currency(summary.long_exposure.total_exposure)}")
    logger.debug(f"  Stocks: {format_currency(summary.long_exposure.stock_exposure)}")
    logger.debug(
        f"  Options: {format_currency(summary.long_exposure.option_delta_exposure)}"
    )

    # Short exposure
    logger.debug("Short Exposure:")
    logger.debug(f"  Total: {format_currency(summary.short_exposure.total_exposure)}")
    logger.debug(f"  Stocks: {format_currency(summary.short_exposure.stock_exposure)}")
    logger.debug(
        f"  Options: {format_currency(summary.short_exposure.option_delta_exposure)}"
    )

    # Options exposure
    logger.debug("Options Exposure:")
    logger.debug(
        f"  Total Delta: {format_currency(summary.options_exposure.total_exposure)}"
    )
    logger.debug(
        f"  Long Delta: {format_currency(summary.options_exposure.components.get('Long Options Delta Exp', 0))}"
    )
    logger.debug(
        f"  Short Delta: {format_currency(summary.options_exposure.components.get('Short Options Delta Exp', 0))}"
    )
    logger.debug(
        f"  Net Delta: {format_currency(summary.options_exposure.components.get('Net Options Delta Exp', 0))}"
    )
    logger.debug("--------------------------------")


def calculate_position_weight(
    position_market_exposure: float, portfolio_net_exposure: float
) -> float:
    """Calculate a position's weight in the portfolio.

    Args:
        position_market_exposure: The market exposure of the position
        portfolio_net_exposure: The net market exposure of the entire portfolio

    Returns:
        The position's weight as a decimal (0.0 to 1.0)
    """
    if not portfolio_net_exposure:
        raise ValueError("Portfolio net exposure cannot be zero")
    return position_market_exposure / portfolio_net_exposure


def calculate_beta_adjusted_net_exposure(
    long_beta_adjusted: float, short_beta_adjusted: float
) -> float:
    """Calculate the beta-adjusted net exposure.

    This function calculates the beta-adjusted net exposure by adding the
    long and short beta-adjusted exposures. Short exposures should be
    represented as negative values. This is the single source of truth
    for this calculation throughout the application.

    Args:
        long_beta_adjusted: The beta-adjusted exposure of long positions (positive value)
        short_beta_adjusted: The beta-adjusted exposure of short positions (negative value)

    Returns:
        The beta-adjusted net exposure
    """
    return long_beta_adjusted + short_beta_adjusted


def recalculate_portfolio_with_prices(
    groups: list[PortfolioGroup],
    price_adjustments: dict[str, float],
    cash_like_positions: list[dict] | None = None,
    pending_activity_value: float = 0.0,
) -> tuple[list[PortfolioGroup], PortfolioSummary]:
    """Recalculate portfolio groups and summary with adjusted prices.

    Args:
        groups: Original portfolio groups
        price_adjustments: Dictionary mapping tickers to price adjustment factors
                          (e.g., {'SPY': 1.05} for a 5% increase)
        cash_like_positions: Cash-like positions
        pending_activity_value: Value of pending activity

    Returns:
        Tuple of (recalculated_groups, recalculated_summary)
    """
    if not groups:
        logger.warning("Cannot recalculate an empty portfolio")
        # Return empty results
        empty_exposure = ExposureBreakdown(
            stock_exposure=0.0,
            stock_beta_adjusted=0.0,
            option_delta_exposure=0.0,
            option_beta_adjusted=0.0,
            total_exposure=0.0,
            total_beta_adjusted=0.0,
            description="Empty exposure",
            formula="N/A",
            components={},
        )

        empty_summary = PortfolioSummary(
            net_market_exposure=0.0,
            portfolio_beta=0.0,
            long_exposure=empty_exposure,
            short_exposure=empty_exposure,
            options_exposure=empty_exposure,
            short_percentage=0.0,
            cash_like_positions=[],
            cash_like_value=0.0,
            cash_like_count=0,
            cash_percentage=0.0,
            stock_value=0.0,
            option_value=0.0,
            portfolio_estimate_value=pending_activity_value,
        )
        return [], empty_summary

    # Initialize cash-like positions list if None
    if cash_like_positions is None:
        cash_like_positions = []

    # Create new recalculated groups
    recalculated_groups = []

    for group in groups:
        ticker = group.ticker
        adjustment_factor = price_adjustments.get(ticker, 1.0)

        # Recalculate stock position if it exists
        recalculated_stock = None
        if group.stock_position:
            current_price = group.stock_position.price
            new_price = current_price * adjustment_factor
            recalculated_stock = group.stock_position.recalculate_with_price(new_price)

        # Recalculate option positions
        recalculated_options = []
        for option in group.option_positions:
            current_price = group.stock_position.price if group.stock_position else 0.0
            new_price = current_price * adjustment_factor
            recalculated_option = option.recalculate_with_price(new_price)
            recalculated_options.append(recalculated_option)

        # Calculate group metrics
        # For stock positions, market_exposure is quantity * price
        # For option positions, delta_exposure is delta * notional_value * sign(quantity)
        # where notional_value is calculated using the canonical implementation in options.py

        # Use the canonical functions to calculate net exposure and beta-adjusted exposure
        from .portfolio_value import (
            calculate_beta_adjusted_exposure,
            calculate_net_exposure,
        )

        net_exposure = calculate_net_exposure(recalculated_stock, recalculated_options)
        beta_adjusted_exposure = calculate_beta_adjusted_exposure(
            recalculated_stock, recalculated_options
        )

        beta = (
            recalculated_stock.beta if recalculated_stock else 0
        )  # Use stock beta as base

        total_delta_exposure = sum(opt.delta_exposure for opt in recalculated_options)
        options_delta_exposure = sum(opt.delta_exposure for opt in recalculated_options)

        # Create new portfolio group
        recalculated_group = PortfolioGroup(
            ticker=ticker,
            stock_position=recalculated_stock,
            option_positions=recalculated_options,
            net_exposure=net_exposure,
            beta=beta,
            beta_adjusted_exposure=beta_adjusted_exposure,
            total_delta_exposure=total_delta_exposure,
            options_delta_exposure=options_delta_exposure,
        )

        recalculated_groups.append(recalculated_group)

    # Recalculate portfolio summary
    recalculated_summary = calculate_portfolio_summary(
        recalculated_groups, cash_like_positions, pending_activity_value
    )

    return recalculated_groups, recalculated_summary


def calculate_position_metrics(group: PortfolioGroup) -> dict:
    """Format portfolio group metrics for display in the UI.

    This function extracts key metrics from a PortfolioGroup and formats them as
    human-readable strings for presentation. It handles formatting of currency values,
    beta values, and special cases like missing options.

    Args:
        group: The PortfolioGroup object containing a stock and its related options

    Returns:
        A dictionary with formatted metrics including:
        - 'total_value': Combined market value formatted as currency
        - 'beta': Underlying stock beta formatted with precision
        - 'beta_adjusted_exposure': Risk-adjusted exposure formatted as currency
        - 'options_delta_exposure': Net options exposure or "N/A" if no options

    Raises:
        ValueError: If group is None or missing required attributes
    """
    if not group:
        raise ValueError("Input PortfolioGroup cannot be None")

    try:
        # Format the group's metrics for display
        has_options = bool(group.option_positions)

        return {
            "net_exposure": format_currency(group.net_exposure),
            "beta": format_beta(group.beta),
            "beta_adjusted_exposure": format_currency(group.beta_adjusted_exposure),
            "options_delta_exposure": format_currency(group.options_delta_exposure)
            if has_options
            else "N/A",
        }
    except Exception as e:
        logger.error(f"Error formatting metrics for {group.ticker}: {e}", exc_info=True)
        raise ValueError(f"Error calculating metrics for {group.ticker}") from e
