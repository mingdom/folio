# Position Group Simulation Analysis

## WHY
The user reported that despite fixing code to include both stock and option positions in the simulation, the overall simulated results remained the same. This raised concerns that options might still be ignored when there are stocks in the same position group.

## WHAT
This document outlines the findings from our investigation into how stock and option positions contribute to the simulation results in position groups that contain both types.

## HOW

### Experimental Approach

We added detailed logging to the `simulate_position_group` function in `simulator_v2.py` to track and report the contributions of stock positions versus option positions to the total PNL. We then ran the simulation focusing on the AMZN position group, which contains both stock and option positions.

### Findings

Our investigation conclusively demonstrated that both stock and option positions are being properly simulated and contributing to the total PNL. The options are not being ignored when there are stocks in the same position group.

#### AMZN Position Group Analysis

The AMZN position group includes:
1. A stock position with original value of $283,485.01
2. Several option positions with a combined original value of -$75,420.00 (these are short options)

At different SPY change levels, both stock and option positions contribute to the total PNL:

1. For AMZN at SPY 0.0% (baseline):
   - Stock contribution: $0.00 (0.00% of PNL)
   - Options contribution: $13,940.39 (100.00% of PNL)
   - This makes sense since at 0% SPY change, the stock price doesn't change, but options can still change in value due to other factors like time decay.

2. For AMZN at SPY -10.0%:
   - Stock contribution: -$34,627.49 (82.68% of PNL)
   - Options contribution: -$7,255.27 (17.32% of PNL)
   - Both are contributing to the negative PNL.

3. For AMZN at SPY -5.0%:
   - Stock contribution: -$17,313.74 (170.09% of PNL)
   - Options contribution: $7,134.58 (-70.09% of PNL)
   - Interestingly, the options are actually offsetting some of the stock losses here.

4. For AMZN at SPY +5.0%:
   - Stock contribution: $17,313.74 (57.76% of PNL)
   - Options contribution: $12,661.43 (42.24% of PNL)
   - Both are contributing positively to the PNL.

5. For AMZN at SPY +10.0%:
   - Stock contribution: $34,627.49 (84.52% of PNL)
   - Options contribution: $6,341.83 (15.48% of PNL)
   - Both are contributing positively to the PNL.

### Detailed Position Analysis

The detailed view of the AMZN position group at 0% SPY change shows:
- The stock position has $0.00 PNL (as expected)
- The option positions have various PNLs, totaling $13,940.39

This confirms that both stock and option positions are being properly simulated and contributing to the total PNL.

### Possible Explanations for Unchanged Results

If your fix to include both stock and option positions didn't change the overall simulation results, there are several possible explanations:

1. **The fix was already working**: It's possible that the code was already correctly simulating both stock and option positions, and your fix addressed an edge case that wasn't present in your portfolio.

2. **Offsetting effects**: As seen in the AMZN position at -5.0% SPY change, options can sometimes offset stock losses. If your portfolio has a mix of positions where the effects cancel out, the overall results might appear unchanged.

3. **Small contribution from options**: If options make up a small percentage of your portfolio value, their contribution to the overall PNL might not be noticeable in the aggregate results.

4. **Portfolio composition**: If most of your position groups don't have both stock and option positions, the fix would only affect a small subset of your portfolio.

### Conclusion

Our investigation confirms that the simulation is correctly accounting for both stock and option positions within the same position group. The unchanged results after your fix are likely due to one of the explanations above rather than a problem with the simulation logic.

### Recommended Next Steps

1. **Analyze your portfolio composition**: Determine how many position groups have both stock and option positions, and what percentage of your portfolio value they represent.

2. **Run simulations with different SPY change ranges**: Try running the simulation with a wider range of SPY changes to see if the effects become more noticeable at extreme values.

3. **Focus on specific position groups**: Use the `--ticker` flag to focus on specific position groups that have both stock and option positions, and analyze their individual behavior.

4. **Compare before and after**: If possible, compare the detailed position-level results before and after your fix to see if there are any differences at that level.
