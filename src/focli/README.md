# Folio CLI

Folio CLI is an interactive command-line interface for portfolio analysis and simulation. It gives you immediate insights into your investment portfolio through a streamlined, keyboard-driven experience.

## Getting Started

To start Folio CLI, you can use one of these methods:

```bash
# Using make
make focli

# Or directly with Python
python scripts/focli.py
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
portfolio summary
```
Get a high-level overview of your portfolio, including total value, exposure breakdown, and key risk metrics. This helps you understand your overall positioning at a glance.

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
simulate spy [options]
```
See how your portfolio might perform across different market scenarios:
- `--range 20` - Set the range of market movement to analyze (±20%)
- `--steps 13` - Set the number of data points in the simulation
- `--detailed` - Show position-level details in the simulation
- `--focus SPY,AAPL` - Focus on specific positions
- `--preset <name>` - Use a saved parameter preset
- `--save-preset <name>` - Save current parameters as a preset
- `--filter options` - Run simulation only on positions with options

### Position Analysis

```
position <ticker> [subcommand] [options]
```
Analyze specific positions in depth:
- `position AAPL` - Show basic position details
- `position AAPL details --detailed` - Show comprehensive position information
- `position SPY risk` - Show risk metrics for the position
- `position AAPL simulate` - Simulate this position with different market movements

### Help and Navigation

```
help [command]
```
Get detailed help on available commands and options.

```
exit
```
Exit the application.

## Tips for Effective Use

1. **Start with portfolio summary** to understand your overall positioning
2. **Use simulate spy** to see how market movements might affect your portfolio
3. **Drill down with position commands** to understand specific holdings
4. **Save presets** for analyses you run frequently
5. **Use filtering** to focus on segments of your portfolio

## Example Workflow

```
folio> portfolio load private-data/portfolio-private.csv
folio> portfolio summary
folio> simulate spy --range 15 --steps 11
folio> position SPY risk
folio> position AAPL simulate --range 20
folio> portfolio list --options --sort value
```

This workflow gives you a complete picture of your portfolio's risk profile and behavior in different market conditions, focusing on the positions that matter most.

## Getting Help

Type `help` at any time to see available commands, or `help <command>` for detailed information about a specific command.
