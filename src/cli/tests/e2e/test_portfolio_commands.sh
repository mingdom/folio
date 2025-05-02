#!/bin/bash
# E2E test script for portfolio commands

# Set up
echo "Running E2E tests for portfolio commands..."
CLI_CMD="python -m src.cli"
DEFAULT_PORTFOLIO="private-data/portfolios/portfolio-default.csv"

# Test portfolio load command
echo "Testing 'portfolio load' command..."
$CLI_CMD portfolio load $DEFAULT_PORTFOLIO
if [ $? -ne 0 ]; then
    echo "FAIL: 'portfolio load' command failed"
    exit 1
fi
echo "PASS: 'portfolio load' command succeeded"

# Test portfolio summary command
echo "Testing 'portfolio summary' command..."
$CLI_CMD portfolio summary --file $DEFAULT_PORTFOLIO > /tmp/portfolio_summary_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'portfolio summary' command failed"
    exit 1
fi
echo "PASS: 'portfolio summary' command succeeded"

# Test portfolio list command
echo "Testing 'portfolio list' command..."
$CLI_CMD portfolio list --file $DEFAULT_PORTFOLIO > /tmp/portfolio_list_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'portfolio list' command failed"
    exit 1
fi
echo "PASS: 'portfolio list' command succeeded"

# Test portfolio list with filters
echo "Testing 'portfolio list' command with filters..."
$CLI_CMD portfolio list --file $DEFAULT_PORTFOLIO --type stock --sort value:desc > /tmp/portfolio_list_filtered_output.txt
if [ $? -ne 0 ]; then
    echo "FAIL: 'portfolio list' command with filters failed"
    exit 1
fi
echo "PASS: 'portfolio list' command with filters succeeded"

# Summary
echo "All portfolio command tests passed!"
exit 0
