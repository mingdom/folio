from dataclasses import dataclass
from typing import Literal, TypedDict

from .logger import logger
from .options import OptionContract, calculate_bs_price

# Circular dependency between data_model.py and portfolio_value.py has been fixed
# by moving common calculation functions to calculations.py


class PositionDict(TypedDict):
    """Type definition for position dictionary representation"""

    ticker: str
    position_type: Literal["stock", "option"]
    quantity: float
    beta: float
    beta_adjusted_exposure: float
    market_exposure: (
        float  # Quantity * Price (for stocks) or Delta * Notional Value (for options)
    )
    market_value: float  # Actual market value of the position (quantity * price)
    price: float  # Price per share/contract


class StockPositionDict(PositionDict):
    """Type definition for stock position dictionary"""

    price: float
    cost_basis: float


class OptionPositionDict(PositionDict):
    """Type definition for option position dictionary

    TODO: Extend with additional option Greeks (gamma, theta, vega)
    to match the planned OptionPosition class enhancements.
    """

    strike: float
    expiry: str
    option_type: Literal["CALL", "PUT"]
    delta: float
    delta_exposure: float  # Delta * Notional Value * sign(Quantity)
    notional_value: float  # 100 * Underlying Price * |Quantity|
    underlying_beta: float
    cost_basis: float


class ExposureBreakdownDict(TypedDict):
    """Type definition for exposure breakdown dictionary"""

    stock_exposure: float  # Represents the market exposure from stock positions
    stock_beta_adjusted: float  # Risk-adjusted stock exposure
    option_delta_exposure: float  # Represents the market exposure from option positions
    option_beta_adjusted: float  # Risk-adjusted option exposure
    total_exposure: float  # Combined market exposure from stocks and options
    total_beta_adjusted: float  # Combined risk-adjusted exposure
    description: str  # Human-readable explanation
    formula: str  # Calculation formula used
    components: dict[str, float]  # Detailed breakdown of components


class PortfolioGroupDict(TypedDict):
    """Type definition for portfolio group dictionary"""

    ticker: str
    stock_position: StockPositionDict | None
    option_positions: list[OptionPositionDict]
    net_exposure: float  # Stock Exposure + Sum(Option Delta Exposures)
    beta: float  # Underlying beta
    beta_adjusted_exposure: float  # Sum of all beta-adjusted exposures
    total_delta_exposure: float  # Sum of all option delta exposures
    options_delta_exposure: float  # Same as total_delta_exposure
    call_count: int  # Number of call option positions
    put_count: int  # Number of put option positions


class PortfolioSummaryDict(TypedDict):
    """Type definition for portfolio summary dictionary"""

    net_market_exposure: float  # Long - Short (excluding cash)
    portfolio_beta: float  # Weighted average beta of all positions
    long_exposure: ExposureBreakdownDict  # Detailed breakdown of long exposures
    short_exposure: ExposureBreakdownDict  # Detailed breakdown of short exposures
    options_exposure: ExposureBreakdownDict  # Detailed breakdown of option exposures
    short_percentage: float  # Short / (Long + Short)
    cash_like_positions: list[StockPositionDict]  # List of cash positions
    cash_like_value: float  # Total value of cash positions
    cash_like_count: int  # Number of cash positions
    cash_percentage: float  # Cash / Portfolio Estimated Value
    stock_value: float  # Total value of stock positions
    option_value: float  # Total value of option positions
    pending_activity_value: float  # Value of pending activity
    portfolio_estimate_value: (
        float  # Stock Value + Option Value + Cash + Pending Activity
    )
    help_text: dict[str, str]  # Explanations of each metric
    price_updated_at: (
        str | None
    )  # ISO format timestamp of when prices were last updated


@dataclass
class Position:
    """Base class for all positions"""

    ticker: str
    position_type: Literal["stock", "option"]
    quantity: float
    beta: float
    beta_adjusted_exposure: float
    market_exposure: float  # Quantity * Current Price (for stocks) or Delta * Notional Value (for options)
    market_value: float  # Actual market value of the position (quantity * price)

    def __init__(
        self,
        ticker: str,
        position_type: Literal["stock", "option"],
        quantity: float,
        beta: float,
        beta_adjusted_exposure: float,
        market_exposure: float,
        market_value: float
        | None = None,  # Default to None to calculate from market_exposure
    ):
        """Initialize a Position.

        Args:
            ticker: Security ticker symbol
            position_type: Type of position (stock or option)
            quantity: Number of shares or contracts
            beta: Position beta
            beta_adjusted_exposure: Beta-adjusted market exposure
            market_exposure: Market exposure (quantity * price for stocks, delta * notional for options)
            market_value: Actual market value of the position (quantity * price)
        """

        self.ticker = ticker
        self.position_type = position_type
        self.quantity = quantity
        self.beta = beta
        self.beta_adjusted_exposure = beta_adjusted_exposure
        self.market_exposure = market_exposure

        # Set market_value to market_exposure if not provided
        # This maintains backward compatibility
        if market_value is None:
            self.market_value = market_exposure
        else:
            self.market_value = market_value

    def to_dict(self) -> PositionDict:
        """Convert to a typed dictionary"""
        return {
            "ticker": self.ticker,
            "position_type": self.position_type,
            "quantity": self.quantity,
            "beta": self.beta,
            "beta_adjusted_exposure": self.beta_adjusted_exposure,
            "market_exposure": self.market_exposure,
            "market_value": self.market_value,  # Add market_value to the dictionary
            "price": 0.0,  # Base Position class doesn't have price, but the dict type requires it
        }

    @classmethod
    def from_dict(cls, data: PositionDict) -> "Position":
        """Create a Position from a dictionary

        Args:
            data: Dictionary representation of a Position

        Returns:
            A new Position instance
        """
        # Get market_value if it exists in the data, otherwise use market_exposure
        market_value = data.get("market_value", data["market_exposure"])

        return cls(
            ticker=data["ticker"],
            position_type=data["position_type"],
            quantity=data["quantity"],
            beta=data["beta"],
            beta_adjusted_exposure=data["beta_adjusted_exposure"],
            market_exposure=data["market_exposure"],
            market_value=market_value,
        )


@dataclass
class OptionPosition(Position):
    """Class for option positions"""

    strike: float
    expiry: str
    option_type: Literal["CALL", "PUT"]
    delta: float
    delta_exposure: float  # Delta * Notional Value * sign(Quantity)
    notional_value: float  # 100 * Underlying Price * |Quantity|
    underlying_beta: float
    price: float = 0.0  # Price per contract
    cost_basis: float = 0.0  # Cost basis per contract

    def __init__(
        self,
        ticker: str,
        position_type: Literal["stock", "option"],
        quantity: float,
        beta: float,
        beta_adjusted_exposure: float,
        strike: float,
        expiry: str,
        option_type: Literal["CALL", "PUT"],
        delta: float,
        delta_exposure: float,
        notional_value: float,
        underlying_beta: float,
        market_exposure: float,
        price: float = 0.0,
        cost_basis: float = 0.0,
        market_value: float
        | None = None,  # Default to None to calculate from price and quantity
    ):
        """Initialize an OptionPosition.

        Args:
            ticker: Security ticker symbol
            position_type: Type of position (should be "option")
            quantity: Number of contracts
            beta: Position beta
            beta_adjusted_exposure: Beta-adjusted market exposure
            strike: Option strike price
            expiry: Option expiration date
            option_type: Option type (CALL or PUT)
            delta: Option delta
            delta_exposure: Delta-adjusted exposure
            notional_value: Notional value of the option
            underlying_beta: Beta of the underlying security
            market_exposure: Market exposure (quantity * price)
            price: Price per contract
            cost_basis: Cost basis per contract (for P&L calculations)
        """
        # Calculate market_value if not provided
        if market_value is None:
            # Apply 100x multiplier for option contracts
            market_value = price * quantity * 100

        # Call the parent class constructor
        super().__init__(
            ticker=ticker,
            position_type=position_type,
            quantity=quantity,
            beta=beta,
            beta_adjusted_exposure=beta_adjusted_exposure,
            market_exposure=market_exposure,
            market_value=market_value,
        )

        # Set option-specific fields
        self.strike = strike
        self.expiry = expiry
        self.option_type = option_type
        self.delta = delta
        self.delta_exposure = delta_exposure
        self.notional_value = notional_value
        self.underlying_beta = underlying_beta
        self.price = price
        self.cost_basis = cost_basis

        # Ensure position_type is always "option"
        self.position_type = "option"

    def recalculate_with_price(
        self,
        new_underlying_price: float,
        risk_free_rate: float = 0.05,
        implied_volatility: float | None = None,
    ) -> "OptionPosition":
        """Create a new OptionPosition with recalculated values based on a new underlying price.

        Args:
            new_underlying_price: The new price of the underlying asset
            risk_free_rate: The risk-free interest rate
            implied_volatility: Optional override for implied volatility

        Returns:
            A new OptionPosition instance with updated values
        """
        # Import from calculations module to avoid circular imports
        from .calculations import calculate_notional_value, calculate_option_exposure

        # Create a temporary OptionContract for calculations
        temp_contract = OptionContract(
            underlying=self.ticker,
            expiry=self.expiry,
            strike=self.strike,
            option_type=self.option_type,
            quantity=self.quantity,
            delta=self.delta,
            underlying_beta=self.underlying_beta,
        )

        # Calculate new notional value using the canonical implementation
        new_notional_value = calculate_notional_value(
            self.quantity, new_underlying_price
        )

        # Calculate new exposures using the canonical implementation
        exposures = calculate_option_exposure(
            temp_contract,
            new_underlying_price,
            risk_free_rate,
            implied_volatility,
        )

        # Create a new instance with updated values
        return OptionPosition(
            ticker=self.ticker,
            position_type=self.position_type,
            quantity=self.quantity,
            beta=self.beta,
            beta_adjusted_exposure=exposures["beta_adjusted_exposure"],
            strike=self.strike,
            expiry=self.expiry,
            option_type=self.option_type,
            delta=exposures["delta"],
            delta_exposure=exposures["delta_exposure"],
            notional_value=new_notional_value,  # Use the new notional value
            underlying_beta=self.underlying_beta,
            market_exposure=exposures["delta_exposure"],
            price=calculate_bs_price(
                temp_contract, new_underlying_price, risk_free_rate, implied_volatility
            ),
            cost_basis=self.cost_basis,
            market_value=calculate_bs_price(
                temp_contract, new_underlying_price, risk_free_rate, implied_volatility
            )
            * self.quantity
            * 100,
        )

    def to_dict(self) -> OptionPositionDict:
        base_dict = super().to_dict()
        return {
            **base_dict,
            "strike": self.strike,
            "expiry": self.expiry,
            "option_type": self.option_type,
            "delta": self.delta,
            "delta_exposure": self.delta_exposure,
            "notional_value": self.notional_value,
            "underlying_beta": self.underlying_beta,
            "price": self.price,
            "cost_basis": self.cost_basis,
        }

    @classmethod
    def from_dict(cls, data: OptionPositionDict) -> "OptionPosition":
        """Create an OptionPosition from a dictionary

        Args:
            data: Dictionary representation of an OptionPosition

        Returns:
            A new OptionPosition instance
        """

        logger.debug(f"OptionPosition.from_dict called with keys: {list(data.keys())}")

        # Handle price and cost_basis if they exist in the data
        price = data.get("price", 0.0)
        cost_basis = data.get("cost_basis", 0.0)

        # Get market_value if it exists in the data
        if "market_value" in data:
            market_value = data["market_value"]
            logger.debug(f"Using provided market_value: {market_value}")
        else:
            # Calculate market_value using the 100x multiplier
            market_value = price * data["quantity"] * 100
            logger.debug(
                f"Calculated market_value: {market_value} (price: {price}, quantity: {data['quantity']})"
            )

        try:
            return cls(
                ticker=data["ticker"],
                position_type=data["position_type"],
                quantity=data["quantity"],
                beta=data["beta"],
                beta_adjusted_exposure=data["beta_adjusted_exposure"],
                market_exposure=data["market_exposure"],
                strike=data["strike"],
                expiry=data["expiry"],
                option_type=data["option_type"],
                delta=data["delta"],
                delta_exposure=data["delta_exposure"],
                notional_value=data["notional_value"],
                underlying_beta=data["underlying_beta"],
                price=price,
                cost_basis=cost_basis,
                market_value=market_value,
            )
        except Exception as e:
            logger.error(f"Error creating option position: {e}", exc_info=True)
            logger.debug(f"Problematic option data: {data}")
            raise


@dataclass
class StockPosition:
    """Details of a stock position

    A stock position represents a holding of shares in a particular security.
    Negative quantity values represent short positions.
    """

    ticker: str
    quantity: int
    beta: float
    market_exposure: float  # Quantity * Price (fetched at runtime)
    beta_adjusted_exposure: float  # Market Exposure * Beta
    price: float = 0.0  # Price per share
    position_type: str = "stock"  # Always "stock" for StockPosition
    cost_basis: float = 0.0  # Cost basis per share
    market_value: float = 0.0  # Actual market value of the position (quantity * price)

    def __init__(
        self,
        ticker: str,
        quantity: int,
        beta: float,
        beta_adjusted_exposure: float,
        market_exposure: float,
        price: float = 0.0,
        position_type: str = "stock",
        cost_basis: float = 0.0,
        market_value: float
        | None = None,  # Default to None to calculate from price and quantity
    ):
        """Initialize a StockPosition.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            beta: Stock beta
            beta_adjusted_exposure: Beta-adjusted market exposure
            market_exposure: Market exposure (quantity * price)
            price: Price per share
            position_type: Type of position, always "stock" for StockPosition
            cost_basis: Cost basis per share (for P&L calculations)
            market_value: Actual market value of the position (quantity * price), calculated if None
        """

        self.ticker = ticker
        self.quantity = quantity
        self.beta = beta
        self.beta_adjusted_exposure = beta_adjusted_exposure
        self.position_type = position_type
        self.price = price
        self.cost_basis = cost_basis
        self.market_exposure = market_exposure

        # For stocks, market_value is the same as market_exposure
        # But we explicitly calculate it to ensure consistency
        if market_value is None:
            self.market_value = price * quantity
        else:
            self.market_value = market_value

    def recalculate_with_price(self, new_price: float) -> "StockPosition":
        """Create a new StockPosition with recalculated values based on a new price.

        Args:
            new_price: The new price to use for calculations

        Returns:
            A new StockPosition instance with updated values
        """
        # Calculate new market exposure and beta-adjusted exposure
        new_market_exposure = self.quantity * new_price

        # Calculate beta-adjusted exposure consistently
        # For stocks, beta-adjusted exposure is simply market_exposure * beta
        new_beta_adjusted_exposure = new_market_exposure * self.beta

        # Create a new instance with updated values
        return StockPosition(
            ticker=self.ticker,
            quantity=self.quantity,
            beta=self.beta,
            beta_adjusted_exposure=new_beta_adjusted_exposure,
            market_exposure=new_market_exposure,
            price=new_price,
            position_type=self.position_type,
            cost_basis=self.cost_basis,
            market_value=new_market_exposure,
        )

    def to_dict(self) -> StockPositionDict:
        """Convert to a Dash-compatible dictionary"""
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "beta": self.beta,
            "market_exposure": self.market_exposure,
            "beta_adjusted_exposure": self.beta_adjusted_exposure,
            "price": self.price,
            "position_type": "stock",
            "cost_basis": self.cost_basis,
            "market_value": self.market_value,  # Add market_value to the dictionary
        }

    @classmethod
    def from_dict(cls, data: StockPositionDict) -> "StockPosition":
        """Create a StockPosition from a dictionary

        Args:
            data: Dictionary representation of a StockPosition

        Returns:
            A new StockPosition instance
        """

        logger.debug(f"StockPosition.from_dict called with keys: {list(data.keys())}")

        # Handle price if it exists in the data
        price = data.get("price", 0.0)

        # Get market_value if it exists in the data
        if "market_value" in data:
            market_value = data["market_value"]
            logger.debug(f"Using provided market_value: {market_value}")
        else:
            # Calculate market_value from price and quantity
            market_value = price * data["quantity"]
            logger.debug(
                f"Calculated market_value: {market_value} (price: {price}, quantity: {data['quantity']})"
            )

        try:
            return cls(
                ticker=data["ticker"],
                quantity=data["quantity"],
                beta=data["beta"],
                market_exposure=data["market_exposure"],
                beta_adjusted_exposure=data["beta_adjusted_exposure"],
                price=price,
                position_type=data.get("position_type", "stock"),  # Pass position_type
                cost_basis=data.get("cost_basis", 0.0),  # Get cost_basis if it exists
                market_value=market_value,  # Pass market_value if it exists
            )
        except Exception as e:
            logger.error(f"Error creating stock position: {e}", exc_info=True)
            logger.debug(f"Problematic stock data: {data}")
            raise


@dataclass
class PortfolioGroup:
    """Group of related positions (stock + options)"""

    ticker: str
    stock_position: StockPosition | None
    option_positions: list[OptionPosition]

    # Group metrics
    net_exposure: float  # Stock Exposure + Sum(Option Delta Exposures)
    beta: float  # Underlying beta
    beta_adjusted_exposure: float  # Sum of all beta-adjusted exposures
    total_delta_exposure: float  # Sum of all option delta exposures
    options_delta_exposure: float  # Same as total_delta_exposure

    def __init__(
        self,
        ticker: str,
        stock_position: StockPosition | None,
        option_positions: list[OptionPosition],
        net_exposure: float,
        beta: float,
        beta_adjusted_exposure: float,
        total_delta_exposure: float,
        options_delta_exposure: float,
    ):
        """Initialize a PortfolioGroup.

        Args:
            ticker: Ticker symbol
            stock_position: Stock position (if any)
            option_positions: List of option positions
            net_exposure: Net market exposure
            beta: Underlying beta
            beta_adjusted_exposure: Beta-adjusted exposure
            total_delta_exposure: Total delta exposure
            options_delta_exposure: Options delta exposure
        """

        self.ticker = ticker
        self.stock_position = stock_position
        self.option_positions = option_positions
        self.beta = beta
        self.beta_adjusted_exposure = beta_adjusted_exposure
        self.total_delta_exposure = total_delta_exposure
        self.options_delta_exposure = options_delta_exposure
        self.net_exposure = net_exposure

        # Calculate option counts
        self._calculate_option_counts()

    @property
    def total_value(self) -> float:
        """DEPRECATED: Use net_exposure instead.

        This property exists for backward compatibility and will be removed in a future version.
        """
        return self.net_exposure

    @total_value.setter
    def total_value(self, value: float):
        """Set total_value (also sets net_exposure)."""
        # Update both total_value and net_exposure
        self._total_value = value
        self.net_exposure = value

    # net_option_value property removed as it's based on unreliable market values

    # Option counts
    call_count: int = 0
    put_count: int = 0

    def __post_init__(self) -> None:
        """Calculate option-specific metrics"""
        # This method is called after __init__ when using @dataclass
        # but we have a custom __init__, so we need to call it explicitly
        self._calculate_option_counts()

    def recalculate_net_exposure(self) -> None:
        """Recalculate net exposure using the canonical function."""
        from .calculations import (
            calculate_beta_adjusted_exposure,
            calculate_net_exposure,
        )

        self.net_exposure = calculate_net_exposure(
            self.stock_position, self.option_positions
        )

        self.beta_adjusted_exposure = calculate_beta_adjusted_exposure(
            self.stock_position, self.option_positions
        )

    def _calculate_option_counts(self) -> None:
        """Calculate the number of calls and puts"""
        self.call_count = sum(
            1 for opt in self.option_positions if opt.option_type == "CALL"
        )
        self.put_count = sum(
            1 for opt in self.option_positions if opt.option_type == "PUT"
        )

    def to_dict(self) -> PortfolioGroupDict:
        """Convert to a Dash-compatible dictionary"""
        return {
            "ticker": self.ticker,
            "stock_position": self.stock_position.to_dict()
            if self.stock_position
            else None,
            "option_positions": [opt.to_dict() for opt in self.option_positions],
            "net_exposure": self.net_exposure,
            "beta": self.beta,
            "beta_adjusted_exposure": self.beta_adjusted_exposure,
            "total_delta_exposure": self.total_delta_exposure,
            "options_delta_exposure": self.options_delta_exposure,
            "call_count": self.call_count,
            "put_count": self.put_count,
        }

    @classmethod
    def from_dict(cls, data: PortfolioGroupDict) -> "PortfolioGroup":
        """Create a PortfolioGroup from a dictionary

        Args:
            data: Dictionary representation of a PortfolioGroup

        Returns:
            A new PortfolioGroup instance
        """

        logger.debug(f"PortfolioGroup.from_dict called with keys: {list(data.keys())}")

        # Create stock position if present
        stock_position = None
        if data.get("stock_position"):
            try:
                stock_position = StockPosition.from_dict(data["stock_position"])
                logger.debug(f"Created stock position for {data['ticker']}")
            except Exception as e:
                logger.error(
                    f"Error creating stock position for {data['ticker']}: {e}",
                    exc_info=True,
                )
                logger.debug(f"Problematic stock data: {data['stock_position']}")
                raise

        # Create option positions
        option_positions = []
        for i, opt_data in enumerate(data.get("option_positions", [])):
            try:
                option_position = OptionPosition.from_dict(opt_data)
                option_positions.append(option_position)
                logger.debug(f"Created option position {i} for {data['ticker']}")
            except Exception as e:
                logger.error(
                    f"Error creating option position {i} for {data['ticker']}: {e}",
                    exc_info=True,
                )
                logger.debug(f"Problematic option data: {opt_data}")
                raise

        # Create the group
        try:
            group = cls(
                ticker=data["ticker"],
                stock_position=stock_position,
                option_positions=option_positions,
                net_exposure=data["net_exposure"],
                beta=data["beta"],
                beta_adjusted_exposure=data["beta_adjusted_exposure"],
                total_delta_exposure=data["total_delta_exposure"],
                options_delta_exposure=data["options_delta_exposure"],
            )

            # Set call_count and put_count directly
            group.call_count = data.get("call_count", 0)
            group.put_count = data.get("put_count", 0)

            return group
        except Exception as e:
            logger.error(
                f"Error creating portfolio group for {data['ticker']}: {e}",
                exc_info=True,
            )
            raise

    def get_details(
        self,
    ) -> dict[str, dict[str, float] | list[dict[str, str | float]]]:
        """Get detailed breakdown of the group's exposures"""
        return {
            "Stock Position": {
                "Market Exposure": self.stock_position.market_exposure
                if self.stock_position
                else 0,
                "Beta-Adjusted": self.stock_position.beta_adjusted_exposure
                if self.stock_position
                else 0,
            },
            "Options": [
                {
                    "Type": opt.option_type,
                    "Strike": opt.strike,
                    "Expiry": opt.expiry,
                    "Delta": opt.delta,
                    "Delta Exposure": opt.delta_exposure,
                    "Beta-Adjusted": opt.beta_adjusted_exposure,
                }
                for opt in self.option_positions
            ],
            "Total": {
                "Net Exposure": self.net_exposure,
                "Beta-Adjusted": self.beta_adjusted_exposure,
            },
        }


@dataclass
class ExposureBreakdown:
    """Detailed breakdown of exposure by type

    This class provides a comprehensive view of market exposure, separating
    stock exposure from options exposure to help users understand the
    different risk components in their portfolio.
    """

    stock_exposure: float  # Represents the market exposure from stock positions
    stock_beta_adjusted: float  # Risk-adjusted stock exposure
    option_delta_exposure: float  # Represents the market exposure from option positions
    option_beta_adjusted: float  # Risk-adjusted option exposure
    total_exposure: float  # Combined market exposure from stocks and options
    total_beta_adjusted: float  # Combined risk-adjusted exposure
    description: str  # Human-readable explanation
    formula: str  # Calculation formula used
    components: dict[str, float]  # Detailed breakdown of components

    def __init__(
        self,
        stock_exposure: float | None = None,
        stock_beta_adjusted: float | None = None,
        option_delta_exposure: float | None = None,
        option_beta_adjusted: float | None = None,
        total_exposure: float | None = None,
        total_beta_adjusted: float | None = None,
        description: str | None = None,
        formula: str | None = None,
        components: dict[str, float] | None = None,
    ):
        """Initialize an ExposureBreakdown.

        Args:
            stock_exposure: Market exposure from stock positions
            stock_beta_adjusted: Risk-adjusted stock exposure
            option_delta_exposure: Market exposure from option positions
            option_beta_adjusted: Risk-adjusted option exposure
            total_exposure: Combined market exposure
            total_beta_adjusted: Combined risk-adjusted exposure
            description: Human-readable explanation
            formula: Calculation formula
            components: Detailed breakdown
        """
        # Set fields directly
        self.stock_exposure = stock_exposure
        self.option_delta_exposure = option_delta_exposure
        self.total_exposure = total_exposure
        self.stock_beta_adjusted = stock_beta_adjusted
        self.option_beta_adjusted = option_beta_adjusted
        self.total_beta_adjusted = total_beta_adjusted
        self.description = description
        self.formula = formula
        self.components = components

        # Set backward compatibility properties
        self._stock_value = stock_exposure
        self._option_delta_value = option_delta_exposure
        self._total_value = total_exposure

    @property
    def stock_value(self) -> float:
        """DEPRECATED: Use stock_exposure instead."""
        return self.stock_exposure

    @stock_value.setter
    def stock_value(self, value: float):
        """Set stock_value (also sets stock_exposure)."""
        self._stock_value = value
        self.stock_exposure = value

    @property
    def option_delta_value(self) -> float:
        """DEPRECATED: Use option_delta_exposure instead."""
        return self.option_delta_exposure

    @option_delta_value.setter
    def option_delta_value(self, value: float):
        """Set option_delta_value (also sets option_delta_exposure)."""
        self._option_delta_value = value
        self.option_delta_exposure = value

    @property
    def total_value(self) -> float:
        """DEPRECATED: Use total_exposure instead."""
        return self.total_exposure

    @total_value.setter
    def total_value(self, value: float):
        """Set total_value (also sets total_exposure)."""
        self._total_value = value
        self.total_exposure = value

    def to_dict(self) -> ExposureBreakdownDict:
        """Convert to a Dash-compatible dictionary"""
        return {
            "stock_exposure": self.stock_exposure,
            "stock_beta_adjusted": self.stock_beta_adjusted,
            "option_delta_exposure": self.option_delta_exposure,
            "option_beta_adjusted": self.option_beta_adjusted,
            "total_exposure": self.total_exposure,
            "total_beta_adjusted": self.total_beta_adjusted,
            "description": self.description,
            "formula": self.formula,
            "components": self.components,
        }

    @classmethod
    def from_dict(cls, data: ExposureBreakdownDict) -> "ExposureBreakdown":
        """Create an ExposureBreakdown from a dictionary

        Args:
            data: Dictionary representation of an ExposureBreakdown

        Returns:
            A new ExposureBreakdown instance
        """
        return cls(
            stock_exposure=data["stock_exposure"],
            stock_beta_adjusted=data["stock_beta_adjusted"],
            option_delta_exposure=data["option_delta_exposure"],
            option_beta_adjusted=data["option_beta_adjusted"],
            total_exposure=data["total_exposure"],
            total_beta_adjusted=data["total_beta_adjusted"],
            description=data["description"],
            formula=data["formula"],
            components=data["components"],
        )


@dataclass
class PortfolioSummary:
    """Summary of portfolio metrics with detailed breakdowns

    This class provides a comprehensive view of your portfolio's market exposure,
    risk characteristics, and defensive positioning. It helps you understand your
    portfolio's directional bias, sensitivity to market movements, and overall
    risk profile.
    """

    # Market exposure metrics (excluding cash)
    net_market_exposure: float  # Long - Short (excluding cash)
    portfolio_beta: float  # Weighted average beta of all positions

    # Exposure breakdowns
    long_exposure: ExposureBreakdown  # Detailed breakdown of long exposures
    short_exposure: ExposureBreakdown  # Detailed breakdown of short exposures
    options_exposure: ExposureBreakdown  # Detailed breakdown of option exposures

    # Derived metrics
    short_percentage: float  # Short / (Long + Short)

    # Price update timestamp
    price_updated_at: (
        str | None
    )  # ISO format timestamp of when prices were last updated

    @property
    def total_exposure(self) -> float:
        """DEPRECATED: Use net_market_exposure instead.

        This property exists for backward compatibility and will be removed in a future version.
        """
        return self.net_market_exposure

    @total_exposure.setter
    def total_exposure(self, value: float):
        """Set total_exposure (also sets net_market_exposure)."""
        self._total_exposure = value
        self.net_market_exposure = value

    # Cash metrics (separate from market exposure)
    cash_like_positions: list[StockPosition] = None  # List of cash positions
    cash_like_value: float = 0.0  # Total value of cash positions
    cash_like_count: int = 0  # Number of cash positions
    cash_percentage: float = 0.0  # Cash / Portfolio Estimated Value

    # Value metrics
    stock_value: float = 0.0  # Total value of stock positions
    option_value: float = 0.0  # Total value of option positions
    pending_activity_value: float = 0.0  # Value of pending activity

    # Portfolio estimated value (for reference only)
    portfolio_estimate_value: float = (
        0.0  # Stock Value + Option Value + Cash + Pending Activity
    )

    # Help text for each metric
    help_text: dict[str, str] | None = None

    def __post_init__(self):
        """Initialize help text for metrics"""
        self.help_text = {
            "net_market_exposure": """
                Net Market Exposure: Your portfolio's overall directional bias

                This metric shows whether your portfolio is net long or short the market.
                A positive value means you have more long exposure than short exposure,
                indicating a bullish stance. A negative value indicates a bearish stance.

                Use this to understand how your portfolio might perform in different market
                environments and to ensure your market exposure aligns with your outlook.
            """,
            "portfolio_beta": """
                Portfolio Beta: Your portfolio's sensitivity to market movements

                This metric shows how much your portfolio is expected to move relative to
                the overall market. A beta of 1.5 means your portfolio would be expected
                to move 1.5% for every 1% move in the market.

                Use this to gauge your portfolio's risk level and to ensure it matches
                your risk tolerance and market outlook.
            """,
            "long_exposure": """
                Long Exposure: Your portfolio's bullish positioning

                This metric shows your total positive market exposure from both stocks
                and options. It includes long stock positions, long call options, and
                short put options.

                Use this to understand your potential upside in rising markets and to
                ensure your bullish positioning aligns with your market outlook.
            """,
            "short_exposure": """
                Short Exposure: Your portfolio's bearish positioning

                This metric shows your total negative market exposure from both stocks
                and options. It includes short stock positions, short call options, and
                long put options.

                Use this to understand your downside protection in falling markets and
                to ensure your hedging strategy is adequate for your risk tolerance.
            """,
            "options_exposure": """
                Options Exposure: Your market exposure from options

                This breakdown shows how options contribute to your overall market exposure.
                Options can provide leverage, income, or hedging depending on the strategy.

                Use this to understand how much of your market risk comes from options
                versus stocks, and to ensure your options strategies align with your
                investment goals.
            """,
            "short_percentage": """
                Short Percentage: Your portfolio's hedge ratio

                This metric shows what percentage of your market exposure is short.
                A higher percentage indicates more downside protection.

                Use this to gauge your defensive positioning and to ensure your
                hedging strategy aligns with your market outlook and risk tolerance.
            """,
            "cash_like_positions": """
                Cash-like Positions: Your portfolio's defensive assets

                These are positions with very low market correlation, such as money
                market funds, short-term treasuries, and other highly liquid assets.

                Use this to understand your defensive positioning and available capital
                for new opportunities.
            """,
            "cash_like_value": """
                Cash-like Value: Your portfolio's defensive capital

                This is the total value of your cash and cash-equivalent positions.
                It represents your most liquid and lowest-risk assets.

                Use this to understand your defensive positioning and available
                dry powder for new investment opportunities.
            """,
            "cash_like_count": """
                Cash-like Count: Diversification of your defensive assets

                This shows how many different cash or cash-equivalent positions
                you hold in your portfolio.

                Use this to ensure you're not overly concentrated in a single
                cash-like instrument.
            """,
            "cash_percentage": """
                Cash Percentage: Your portfolio's defensive allocation

                This shows what percentage of your portfolio is in cash or cash equivalents.
                A higher percentage indicates more safety in market downturns but potentially
                lower returns in bull markets.

                Use this to gauge your defensive positioning and to ensure it aligns with
                your market outlook and risk tolerance.
            """,
            "portfolio_estimate_value": """
                Portfolio Estimated Value: Your portfolio's total size

                This is an estimate of your portfolio's total value, including both
                market exposure and cash. It provides a baseline for calculating
                percentage allocations.

                Use this to track your portfolio's overall size and to calculate
                meaningful percentage allocations for different exposures.
            """,
        }

    def to_dict(self) -> PortfolioSummaryDict:
        """Convert to a Dash-compatible dictionary"""
        if self.help_text is None:
            self.__post_init__()

        # Initialize empty list if None
        if self.cash_like_positions is None:
            self.cash_like_positions = []

        return {
            "net_market_exposure": self.net_market_exposure,
            "portfolio_beta": self.portfolio_beta,
            "long_exposure": self.long_exposure.to_dict(),
            "short_exposure": self.short_exposure.to_dict(),
            "options_exposure": self.options_exposure.to_dict(),
            "short_percentage": self.short_percentage,
            "cash_like_positions": [pos.to_dict() for pos in self.cash_like_positions],
            "cash_like_value": self.cash_like_value,
            "cash_like_count": self.cash_like_count,
            "cash_percentage": self.cash_percentage,
            "stock_value": self.stock_value,
            "option_value": self.option_value,
            "pending_activity_value": self.pending_activity_value,
            "portfolio_estimate_value": self.portfolio_estimate_value,
            "help_text": self.help_text if self.help_text is not None else {},
            "price_updated_at": self.price_updated_at,
        }

    @classmethod
    def from_dict(cls, data: PortfolioSummaryDict) -> "PortfolioSummary":
        """Create a PortfolioSummary from a dictionary

        Args:
            data: Dictionary representation of a PortfolioSummary

        Returns:
            A new PortfolioSummary instance
        """

        logger.debug(
            f"PortfolioSummary.from_dict called with keys: {list(data.keys())}"
        )

        # Create exposure breakdowns
        long_exposure = ExposureBreakdown.from_dict(data["long_exposure"])
        short_exposure = ExposureBreakdown.from_dict(data["short_exposure"])
        options_exposure = ExposureBreakdown.from_dict(data["options_exposure"])

        # Create cash-like positions
        cash_like_positions = []
        for pos_data in data.get("cash_like_positions", []):
            cash_like_positions.append(StockPosition.from_dict(pos_data))

        # Support both old and new field names for backward compatibility
        net_market_exposure = data.get(
            "net_market_exposure", data.get("total_value_net", 0.0)
        )
        cash_percentage = data.get("cash_percentage", 0.0)
        portfolio_estimate_value = data.get("portfolio_estimate_value", 0.0)
        stock_value = data.get("stock_value", 0.0)
        option_value = data.get("option_value", 0.0)

        # Handle missing pending_activity_value field
        if "pending_activity_value" not in data:
            logger.warning(
                "pending_activity_value missing from PortfolioSummary data, using default value 0.0"
            )
        pending_activity_value = data.get("pending_activity_value", 0.0)

        return cls(
            net_market_exposure=net_market_exposure,
            portfolio_beta=data["portfolio_beta"],
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            options_exposure=options_exposure,
            short_percentage=data["short_percentage"],
            cash_like_positions=cash_like_positions,
            cash_like_value=data["cash_like_value"],
            cash_like_count=data["cash_like_count"],
            cash_percentage=cash_percentage,
            stock_value=stock_value,
            option_value=option_value,
            pending_activity_value=pending_activity_value,
            portfolio_estimate_value=portfolio_estimate_value,
            help_text=data.get("help_text"),
            price_updated_at=data.get("price_updated_at"),
        )


def create_portfolio_group(
    stock_data: dict[str, str | int | float] | None = None,
    option_data: list[dict[str, str | int | float]] | None = None,
) -> PortfolioGroup | None:
    """Create a PortfolioGroup from stock and option data"""
    if not stock_data and not option_data:
        return None

    # Create stock position if data exists
    stock_position = None
    if stock_data:
        # Get price if it exists in the data
        price = stock_data.get("price", 0.0)

        stock_position = StockPosition(
            ticker=stock_data["ticker"],
            quantity=stock_data["quantity"],
            beta=stock_data["beta"],
            market_exposure=stock_data["market_exposure"],
            beta_adjusted_exposure=stock_data["beta_adjusted_exposure"],
            price=price,
            cost_basis=stock_data.get("cost_basis", 0.0),  # Get cost_basis if it exists
        )

    # Create option positions if data exists
    option_positions = []
    if option_data:
        for opt in option_data:
            # Get price if it exists in the data
            price = opt.get("price", 0.0)

            option_positions.append(
                OptionPosition(
                    # Base Position fields
                    ticker=opt["ticker"],
                    position_type="option",
                    quantity=opt["quantity"],
                    beta=opt["beta"],
                    beta_adjusted_exposure=opt["beta_adjusted_exposure"],
                    market_exposure=opt["market_exposure"],
                    # OptionPosition specific fields
                    strike=opt["strike"],
                    expiry=opt["expiry"],
                    option_type=opt["option_type"],
                    delta=opt["delta"],
                    delta_exposure=opt["delta_exposure"],
                    notional_value=opt["notional_value"],
                    underlying_beta=opt["beta"],  # Use same beta for underlying
                    price=price,
                    cost_basis=opt.get(
                        "cost_basis", price
                    ),  # Use price as default cost basis
                )
            )

    # Calculate group metrics
    # For stock positions, market_exposure is quantity * price
    # For option positions, delta_exposure is delta * notional_value * sign(quantity)
    # where notional_value is calculated using the canonical implementation in options.py

    # Add debug logging

    # Log stock position details
    if stock_position:
        logger.debug(f"Stock position for {stock_data['ticker']}:")
        logger.debug(f"  Quantity: {stock_position.quantity}")
        logger.debug(f"  Price: {stock_position.price}")
        logger.debug(f"  Market Exposure: {stock_position.market_exposure}")
        logger.debug(
            f"  Beta-Adjusted Exposure: {stock_position.beta_adjusted_exposure}"
        )

    # Log option position details
    for i, opt in enumerate(option_positions):
        logger.debug(f"Option position {i + 1} for {opt.ticker}:")
        logger.debug(
            f"  Type: {opt.option_type}, Strike: {opt.strike}, Expiry: {opt.expiry}"
        )
        logger.debug(f"  Quantity: {opt.quantity}")
        logger.debug(f"  Delta: {opt.delta}")
        logger.debug(f"  Delta Exposure: {opt.delta_exposure}")
        logger.debug(f"  Beta-Adjusted Exposure: {opt.beta_adjusted_exposure}")
        logger.debug(f"  Notional Value: {opt.notional_value}")

    # Use the canonical functions to calculate net exposure and beta-adjusted exposure
    from .calculations import calculate_beta_adjusted_exposure, calculate_net_exposure

    net_exposure = calculate_net_exposure(stock_position, option_positions)
    beta_adjusted_exposure = calculate_beta_adjusted_exposure(
        stock_position, option_positions
    )

    beta = stock_position.beta if stock_position else 0  # Use stock beta as base

    total_delta_exposure = sum(opt.delta_exposure for opt in option_positions)

    options_delta_exposure = sum(opt.delta_exposure for opt in option_positions)

    # Log group metrics
    logger.debug(
        f"Group metrics for {stock_data['ticker'] if stock_data else option_data[0]['ticker']}:"
    )
    logger.debug(f"  Net Exposure: {net_exposure}")
    logger.debug(f"  Beta-Adjusted Exposure: {beta_adjusted_exposure}")
    logger.debug(f"  Total Delta Exposure: {total_delta_exposure}")
    logger.debug(f"  Options Delta Exposure: {options_delta_exposure}")

    return PortfolioGroup(
        ticker=stock_data["ticker"] if stock_data else option_data[0]["ticker"],
        stock_position=stock_position,
        option_positions=option_positions,
        net_exposure=net_exposure,
        beta=beta,
        beta_adjusted_exposure=beta_adjusted_exposure,
        total_delta_exposure=total_delta_exposure,
        options_delta_exposure=options_delta_exposure,
    )
