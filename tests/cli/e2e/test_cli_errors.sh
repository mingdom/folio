#!/bin/bash
# E2E test script for checking CLI errors and $nan values
# This script tests all major CLI commands and checks for errors and $nan values in the output

# Set up
echo "Running E2E tests for CLI error detection..."
CLI_CMD="python -m src.cli"
DEFAULT_PORTFOLIO="private-data/portfolios/portfolio-default.csv"
OUTPUT_DIR="/tmp/folio_cli_test_output"
REPORT_FILE="tests/cli/reports/cli-error-report.md"

# Create output directory
mkdir -p $OUTPUT_DIR

# Initialize report file
cat > $REPORT_FILE << EOF
# Folio CLI Error Report

This report documents errors and issues found in the Folio CLI output.

## Test Environment

- Date: $(date)
- CLI Command: $CLI_CMD
- Default Portfolio: $DEFAULT_PORTFOLIO

## Issues Found

EOF

# Function to check for errors in output
check_for_errors() {
    local output_file=$1
    local command_name=$2
    local error_count=0
    local nan_count=0
    local warning_count=0
    local exception_count=0
    local none_count=0
    local total_issues=0

    # Check for $nan values
    if grep -q "\$nan" $output_file; then
        nan_count=$(grep -c "\$nan" $output_file)
        echo "WARNING: $command_name contains $nan_count \$nan values"

        # Add to report
        cat >> $REPORT_FILE << EOF
### $nan_count \$nan values in \`$command_name\`

\`\`\`
$(grep -n "\$nan" $output_file | head -10)
$(if [ $nan_count -gt 10 ]; then echo "... and $(($nan_count - 10)) more instances"; fi)
\`\`\`

EOF
        total_issues=$((total_issues + nan_count))
    fi

    # Check for error messages (case insensitive)
    if grep -i -q "error" $output_file; then
        error_count=$(grep -i -c "error" $output_file)
        echo "WARNING: $command_name contains $error_count error messages"

        # Add to report
        cat >> $REPORT_FILE << EOF
### $error_count Error messages in \`$command_name\`

\`\`\`
$(grep -i -n "error" $output_file | head -10)
$(if [ $error_count -gt 10 ]; then echo "... and $(($error_count - 10)) more instances"; fi)
\`\`\`

EOF
        total_issues=$((total_issues + error_count))
    fi

    # Check for warning messages
    if grep -i -q "warning" $output_file; then
        warning_count=$(grep -i -c "warning" $output_file)
        echo "WARNING: $command_name contains $warning_count warning messages"

        # Add to report
        cat >> $REPORT_FILE << EOF
### $warning_count Warning messages in \`$command_name\`

\`\`\`
$(grep -i -n "warning" $output_file | head -10)
$(if [ $warning_count -gt 10 ]; then echo "... and $(($warning_count - 10)) more instances"; fi)
\`\`\`

EOF
        total_issues=$((total_issues + warning_count))
    fi

    # Check for exception messages
    if grep -i -q "exception" $output_file; then
        exception_count=$(grep -i -c "exception" $output_file)
        echo "WARNING: $command_name contains $exception_count exception messages"

        # Add to report
        cat >> $REPORT_FILE << EOF
### $exception_count Exception messages in \`$command_name\`

\`\`\`
$(grep -i -n "exception" $output_file | head -10)
$(if [ $exception_count -gt 10 ]; then echo "... and $(($exception_count - 10)) more instances"; fi)
\`\`\`

EOF
        total_issues=$((total_issues + exception_count))
    fi

    # Check for None values
    if grep -q "None" $output_file; then
        none_count=$(grep -c "None" $output_file)
        echo "WARNING: $command_name contains $none_count None values"

        # Add to report
        cat >> $REPORT_FILE << EOF
### $none_count None values in \`$command_name\`

\`\`\`
$(grep -n "None" $output_file | head -10)
$(if [ $none_count -gt 10 ]; then echo "... and $(($none_count - 10)) more instances"; fi)
\`\`\`

EOF
        total_issues=$((total_issues + none_count))
    fi

    # Return total issues found
    echo $total_issues
}

# Function to run a command and check for errors
run_and_check() {
    local command=$1
    local output_file=$2
    local command_name=$3

    echo "Testing '$command_name'..."
    $command > $output_file 2>&1

    # Check if command succeeded
    if [ $? -ne 0 ]; then
        echo "FAIL: '$command_name' command failed with exit code $?"

        # Add to report
        cat >> $REPORT_FILE << EOF
### Command Failure: \`$command_name\`

The command failed with a non-zero exit code.

\`\`\`
$(cat $output_file | head -20)
$(if [ $(wc -l < $output_file) -gt 20 ]; then echo "... (output truncated)"; fi)
\`\`\`

EOF
        return 1
    fi

    # Check for errors in output
    issues=$(check_for_errors $output_file "$command_name")

    if [ "$issues" -eq 0 ]; then
        echo "PASS: '$command_name' command succeeded with no issues"
        return 0
    else
        echo "WARN: '$command_name' command succeeded but has $issues issues"
        return 0
    fi
}

# Test portfolio commands
run_and_check "$CLI_CMD portfolio load $DEFAULT_PORTFOLIO" "$OUTPUT_DIR/portfolio_load.txt" "portfolio load"
run_and_check "$CLI_CMD portfolio summary --file $DEFAULT_PORTFOLIO" "$OUTPUT_DIR/portfolio_summary.txt" "portfolio summary"
run_and_check "$CLI_CMD portfolio list --file $DEFAULT_PORTFOLIO" "$OUTPUT_DIR/portfolio_list.txt" "portfolio list"
run_and_check "$CLI_CMD portfolio list --file $DEFAULT_PORTFOLIO type=stock sort=value:desc" "$OUTPUT_DIR/portfolio_list_filtered.txt" "portfolio list type=stock sort=value:desc"

# Find a ticker that exists in the portfolio for position tests
# We'll use SPY as it's likely to exist in most portfolios
FIRST_TICKER="SPY"

if [ -z "$FIRST_TICKER" ]; then
    echo "FAIL: Could not find a ticker in the portfolio"
    exit 1
fi

echo "Using ticker $FIRST_TICKER for position tests"

# Test position commands with the found ticker
run_and_check "$CLI_CMD position details $FIRST_TICKER --file $DEFAULT_PORTFOLIO" "$OUTPUT_DIR/position_details.txt" "position details $FIRST_TICKER"
run_and_check "$CLI_CMD position details $FIRST_TICKER --file $DEFAULT_PORTFOLIO --show-legs" "$OUTPUT_DIR/position_details_legs.txt" "position details $FIRST_TICKER --show-legs"
run_and_check "$CLI_CMD position risk $FIRST_TICKER --file $DEFAULT_PORTFOLIO" "$OUTPUT_DIR/position_risk.txt" "position risk $FIRST_TICKER"
run_and_check "$CLI_CMD position risk $FIRST_TICKER --file $DEFAULT_PORTFOLIO --show-greeks" "$OUTPUT_DIR/position_risk_greeks.txt" "position risk $FIRST_TICKER --show-greeks"

# Test interactive mode
echo "Testing interactive mode..."
INTERACTIVE_INPUT_FILE="$OUTPUT_DIR/interactive_input.txt"
INTERACTIVE_OUTPUT_FILE="$OUTPUT_DIR/interactive_output.txt"

# Create input file for interactive mode
cat > $INTERACTIVE_INPUT_FILE << EOF
help
portfolio load $DEFAULT_PORTFOLIO
portfolio summary
portfolio list type=stock sort=symbol:asc
position $FIRST_TICKER details
position $FIRST_TICKER risk
exit
EOF

# Run interactive mode with input file
$CLI_CMD < $INTERACTIVE_INPUT_FILE > $INTERACTIVE_OUTPUT_FILE 2>&1

# Check for errors in interactive mode output
check_for_errors $INTERACTIVE_OUTPUT_FILE "interactive mode"

# Add summary to report
cat >> $REPORT_FILE << EOF

## Summary

The test script executed the following commands:
- \`portfolio load $DEFAULT_PORTFOLIO\`
- \`portfolio summary --file $DEFAULT_PORTFOLIO\`
- \`portfolio list --file $DEFAULT_PORTFOLIO\`
- \`portfolio list --file $DEFAULT_PORTFOLIO type=stock sort=value:desc\`
- \`position details $FIRST_TICKER --file $DEFAULT_PORTFOLIO\`
- \`position details $FIRST_TICKER --file $DEFAULT_PORTFOLIO --show-legs\`
- \`position risk $FIRST_TICKER --file $DEFAULT_PORTFOLIO\`
- \`position risk $FIRST_TICKER --file $DEFAULT_PORTFOLIO --show-greeks\`
- Interactive mode with basic commands

All test outputs are available in the \`$OUTPUT_DIR\` directory.

## Next Steps

1. Review the issues found and prioritize them for fixing
2. Focus on fixing \$nan values in the output, as these indicate calculation issues
3. Address any error messages that might affect user experience
4. Create unit tests to prevent regression of fixed issues

EOF

echo "All tests completed. Report generated at $REPORT_FILE"
echo "Test outputs are available in $OUTPUT_DIR"
