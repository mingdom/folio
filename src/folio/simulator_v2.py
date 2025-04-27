"""
Portfolio simulator v2 module.

This module provides enhanced functionality for simulating portfolio performance
under different market scenarios, leveraging the PNL calculation logic for
consistent and accurate pricing.
"""





def calculate_price_adjustment(spy_change: float, beta: float) -> float:
    """
    Calculate price adjustment factor based on SPY change and beta.

    Args:
        spy_change: SPY price change as a decimal (e.g., 0.05 for 5% increase)
        beta: Beta of the position

    Returns:
        Price adjustment factor (e.g., 1.05 for 5% increase)
    """
    return 1.0 + (spy_change * beta)


def calculate_underlying_price(current_price: float, adjustment_factor: float) -> float:
    """
    Calculate new underlying price based on current price and adjustment factor.

    Args:
        current_price: Current price of the underlying
        adjustment_factor: Price adjustment factor

    Returns:
        New underlying price
    """
    return current_price * adjustment_factor
