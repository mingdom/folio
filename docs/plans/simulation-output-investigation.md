# Investigation of Simulation Output Issues

## WHY
The user reported that despite making major logic updates to the calculation code, the rendered view of `make sim` still shows the same results. This suggests that there might be an issue with how the simulation is being executed or how the results are being displayed.

## WHAT
This document outlines the findings from our investigation into why changes to the calculation logic don't seem to affect the output of `make sim`.

## HOW

### Experimental Approach

We took an experimental approach to verify if there's actually an issue with the simulation code:

1. First, we ran `make sim` to see the current output
2. Then, we modified the `simulate_portfolio` function in `simulator_v2.py` to return hardcoded values that would be obviously different from real calculations
3. We ran `make sim` again and confirmed that our changes were reflected in the output
4. We then modified the `simulate_position_group` function to return hardcoded values with a dramatic pattern based on SPY changes
5. We ran `make sim` again to see if changes to this function were also reflected in the output

### Findings

Our experiments confirmed that changes to both `simulate_portfolio` and `simulate_position_group` functions in `simulator_v2.py` are properly reflected in the output of `make sim`.

When we replaced the real calculation in `simulate_portfolio` with hardcoded values, the output showed our hardcoded values as expected. Similarly, when we modified `simulate_position_group` to return values that change dramatically with SPY changes, the output reflected this pattern.

This means that the issue is not with the calculation code being ignored or bypassed. There are several other possibilities to consider:

1. **Calculation Logic Issues**: The changes made to the calculation logic might not be having the expected effect. For example, if you're changing how a specific position type is calculated, but your portfolio doesn't contain that position type, you won't see any changes in the output.

2. **Data Issues**: The input data might be such that your changes don't affect the output. For example, if you're changing how options are priced, but all options in the portfolio are deep in-the-money or deep out-of-the-money, the changes might have minimal impact.

3. **Parameter Issues**: The parameters used in `make sim` might be limiting the visibility of your changes. The Makefile uses a very limited range of SPY changes (`--min-spy-change -0.1 --max-spy-change 0.1 --steps 5`), which might not be sufficient to see the effects of your changes.

4. **Caching in yfinance**: While our experiment showed that the calculation code is being executed, there might still be caching in the yfinance library that's causing stale market data to be used. This could make it appear as if your changes aren't having an effect.

### Recommended Next Steps

1. **Examine Your Specific Changes**: Since we've confirmed that the simulation framework is working correctly, the issue is likely with the specific changes you've made. Review your changes to `simulate_position_group` and consider whether they would have a noticeable effect on your portfolio.

2. **Check Position Types in Your Portfolio**: If your changes affect a specific position type (e.g., options), verify that your portfolio contains positions of that type. You can add debug logging to count how many positions of each type are being processed.

3. **Verify Calculation Logic**: Add detailed logging to your calculation code to see the before and after values for each step. This will help you understand if your changes are having the expected effect but are being masked by other factors.

4. **Expand SPY Change Range**: The Makefile uses a limited range of SPY changes (`--min-spy-change -0.1 --max-spy-change 0.1 --steps 5`). Try running the simulation with a wider range to see if your changes have a more noticeable effect at extreme values.

5. **Test with a Simplified Portfolio**: Create a simple test portfolio with known values that should be affected by your changes. This will help isolate the issue from the complexity of your real portfolio.

6. **Check for Offsetting Effects**: It's possible that your changes have the expected effect on individual positions, but these effects are being offset when aggregated at the portfolio level. Try running the simulation with the `--detailed` flag to see position-level results.

### Conclusion

Our investigation has conclusively demonstrated that both the `simulate_portfolio` and `simulate_position_group` functions in `simulator_v2.py` are being properly executed, and their outputs are correctly reflected in the results displayed by `make sim`.

The issue you're experiencing is not due to the calculation code being ignored, bypassed, or overwritten. Instead, it's likely related to one of the following:

1. The specific changes you've made might not have a significant impact on your particular portfolio composition
2. The effects of your changes might be visible only under certain conditions (e.g., more extreme SPY changes)
3. The effects might be visible at the position level but are being averaged out at the portfolio level
4. There might be offsetting effects between different position types

By following the recommended next steps, particularly adding detailed logging and testing with a simplified portfolio, you should be able to identify why your changes aren't having the expected effect on the simulation results.
