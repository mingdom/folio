#!/bin/bash
# E2E test script for position commands

# Set up
echo "Running E2E tests for position commands..."
CLI_CMD="python -m src.cli"
DEFAULT_PORTFOLIO="private-data/portfolios/portfolio-default.csv"

# We need to determine a ticker that exists in the portfolio
# For now, we'll assume SPY exists in the default portfolio
TEST_TICKER="SPY"

# Test position details command
echo "Testing 'position details' command..."
$CLI_CMD position details $TEST_TICKER --file $DEFAULT_PORTFOLIO > /tmp/position_details_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'position details' command failed"
    exit 1
fi
echo "PASS: 'position details' command succeeded"

# Test position details command with show-legs option
echo "Testing 'position details' command with --show-legs option..."
$CLI_CMD position details $TEST_TICKER --file $DEFAULT_PORTFOLIO --show-legs > /tmp/position_details_legs_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'position details' command with --show-legs option failed"
    exit 1
fi
echo "PASS: 'position details' command with --show-legs option succeeded"

# Test position risk command
echo "Testing 'position risk' command..."
$CLI_CMD position risk $TEST_TICKER --file $DEFAULT_PORTFOLIO > /tmp/position_risk_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'position risk' command failed"
    exit 1
fi
echo "PASS: 'position risk' command succeeded"

# Test position risk command with show-greeks option
echo "Testing 'position risk' command with --show-greeks option..."
$CLI_CMD position risk $TEST_TICKER --file $DEFAULT_PORTFOLIO --show-greeks > /tmp/position_risk_greeks_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'position risk' command with --show-greeks option failed"
    exit 1
fi
echo "PASS: 'position risk' command with --show-greeks option succeeded"

# Summary
echo "All position command tests passed!"
exit 0
