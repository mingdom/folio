# Folio CLI

Folio CLI is an interactive command-line interface for portfolio analysis and simulation. It gives you immediate insights into your investment portfolio through a streamlined, keyboard-driven experience.

## Getting Started

To start Folio CLI, you can use one of these methods:

```bash
# Using make
make focli

# Or directly with Python
python src/focli/focli.py
```

This will launch the interactive shell where you can enter commands.

## Why Use Folio CLI?

- **Speed**: Get answers in seconds without waiting for GUI elements to load
- **Focus**: Analyze exactly what you need without visual distractions
- **Workflow**: Chain analyses together in a natural, exploratory way
- **Efficiency**: Perfect for regular portfolio check-ups and quick "what if" scenarios

## Key Commands

### Portfolio Management

```
portfolio load <path>
```
Load your portfolio data from a CSV file. This is typically the first command you'll run to begin your analysis session.

```
portfolio
```
Get a high-level overview of your portfolio, including total value, exposure breakdown, and key risk metrics. This helps you understand your overall positioning at a glance. (Same as `portfolio summary`)

```
portfolio list [options]
```
View all positions in your portfolio with filtering and sorting options:
- `--focus SPY,AAPL` - Focus on specific tickers
- `--options` - Show only positions with options
- `--stocks` - Show only positions with stocks
- `--sort value` - Sort by position value (also: beta, ticker)
- `--min-value 10000` - Show positions above a certain value

### Simulation

```
sim [options]
```
See how your portfolio might perform across different market scenarios:
- `--min-spy-change -0.2` - Set the minimum SPY change to simulate (-20%)
- `--max-spy-change 0.2` - Set the maximum SPY change to simulate (+20%)
- `--steps 21` - Set the number of data points in the simulation
- `--ticker AAPL` - Focus on a specific ticker
- `--detailed` - Show position-level details in the simulation
- `--position-type stock` - Filter to show only stock positions
- `--position-type option` - Filter to show only option positions
- `--analyze-correlation` - Analyze how positions perform when SPY increases

### Position Analysis

```
position <ticker> [subcommand] [options]
```
Analyze specific positions in depth:
- `position AAPL` - Show basic position details
- `position AAPL details --detailed` - Show comprehensive position information
- `position SPY risk` - Show risk metrics for the position
- `position AAPL sim` - Simulate this position with different market movements

### Help and Navigation

```
help [command]
```
Get detailed help on available commands and options.

```
exit
```
Exit the application.

## Using Make Commands

You can also run simulations directly from the command line using make commands:

```bash
# Run simulation with default parameters
make sim

# Run simulation for a specific portfolio file
make sim portfolio=path/to/portfolio.csv

# Run simulation focusing on a specific ticker
make sim ticker=AAPL

# Show detailed position-level results
make sim detailed=1

# Filter to show only stock positions
make sim type=stock

# Filter to show only option positions
make sim type=option

# Combine multiple options
make sim ticker=AAPL detailed=1 type=stock
```

The `make sim` command uses these default parameters:
- SPY change range: -10% to +10%
- Steps: 5
- Portfolio file: Uses @private-data/private-portfolio.csv if available

## Tips for Effective Use

1. **Start with portfolio summary** to understand your overall positioning
2. **Use `sim` to see how market movements might affect your portfolio**
3. **Use `sim type=stock` or `sim type=option` to analyze specific position types**
4. **Drill down with position commands** to understand specific holdings
5. **Use filtering** to focus on segments of your portfolio

## Example Workflow

```
folio> portfolio load private-data/portfolio-private.csv
folio> portfolio
folio> sim --min-spy-change -0.15 --max-spy-change 0.15 --steps 11
folio> sim --ticker SPY --detailed
folio> sim --position-type stock
folio> position AAPL sim
folio> portfolio list --options --sort value
```

This workflow gives you a complete picture of your portfolio's risk profile and behavior in different market conditions, focusing on the positions that matter most.

## Getting Help

Type `help` at any time to see available commands, or `help <command>` for detailed information about a specific command.
