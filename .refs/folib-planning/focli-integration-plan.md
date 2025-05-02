# Focli Integration Plan

## Current Status

1. **Completed Work**:
   - Implemented core `folib` data structures and models
   - Implemented portfolio data loading in `folib.data.loader`
   - Implemented portfolio processing in `folib.services.portfolio_service`
   - Correctly identified and removed redundant `services/portfolio_loader.py`

2. **Verification**:
   - `folib.data.loader` has full test coverage
   - The loader implementation is being used in production code
   - The module structure follows the architectural plan from master-plan-v2.md

## Areas for Improvement

1. **Interface Consistency**:
   - Current `load_portfolio_from_csv()` returns a pandas DataFrame
   - Consider wrapping this in a domain model to avoid exposing implementation details
   - Could introduce a `RawPortfolioData` class to encapsulate the DataFrame

2. **Error Handling**:
   - Loader module uses mixed error handling strategies (some returns None, some raises)
   - Should standardize on "fail fast" approach per error handling guidelines
   - Need consistent error messaging format

3. **Documentation**:
   - Missing usage examples in docstrings
   - Should add example portfolio CSV format to documentation
   - Could use more detailed logging for debugging

## Integration Steps

1. **Update State Management**:
   - Review current state management in focli
   - Define interface between folib and focli
   - Design state update strategy for new data structures

2. **Update Portfolio Loading**:
   - Create mapping between old and new data structures
   - Update focli's load_portfolio() to use folib
   - Add data validation and error handling

3. **Update Commands**:
   - Identify all commands that use portfolio data
   - Create adapters for incompatible interfaces
   - Update each command progressively

4. **Testing Strategy**:
   - Create integration tests
   - Add comparison tests between old and new implementations
   - Add validation for data structure compatibility

## Risks and Mitigation

1. **Data Structure Compatibility**:
   - Risk: Breaking changes in data structures
   - Mitigation: Create adapter layer if needed
   - Test with real portfolio data

2. **Performance Impact**:
   - Risk: Additional abstraction layers could impact performance
   - Mitigation: Add performance tests
   - Profile critical paths

3. **Error Handling Changes**:
   - Risk: Different error handling could break error reporting
   - Mitigation: Map errors to focli's error display format
   - Add comprehensive error testing

## Next Steps

1. **Pre-Integration Tasks**:
   - Full audit of focli's portfolio data usage
   - Document all breaking changes
   - Create test portfolio data set

2. **Integration Process**:
   - Create feature branch for integration
   - Implement changes in small, testable chunks
   - Add extensive logging for debugging

3. **Validation**:
   - Create integration test suite
   - Test with production portfolio data
   - Compare output with current implementation

## Timeline

1. **Phase 1: Preparation (1-2 days)**
   - Code audit
   - Test data preparation
   - Document breaking changes

2. **Phase 2: Core Integration (2-3 days)**
   - State management updates
   - Portfolio loading integration
   - Basic command updates

3. **Phase 3: Command Updates (2-3 days)**
   - Update remaining commands
   - Add new functionality
   - Performance optimization

4. **Phase 4: Testing (2-3 days)**
   - Integration testing
   - Performance testing
   - Bug fixes

## Success Criteria

1. **Functionality**:
   - All existing commands work with new implementation
   - No loss of features or capabilities
   - Improved error handling and feedback

2. **Performance**:
   - Loading time within 10% of current implementation
   - Memory usage within acceptable limits
   - Smooth command execution

3. **Code Quality**:
   - Clear separation of concerns
   - Consistent error handling
   - Comprehensive test coverage

4. **User Experience**:
   - No visible changes to command interface
   - Improved error messages
   - Better validation feedback
