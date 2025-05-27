# Plan: Display Option Type (CALL/PUT) in CLI Portfolio List Table

## WHY
The goal is to improve the granularity of the CLI output for option positions. Instead of displaying a generic 'option' in the Type column, the CLI should display the specific type: 'CALL' or 'PUT'.

## WHAT
Currently, the CLI's portfolio list command shows all options as 'option' in the Type column. This lacks detail and makes it harder for users to distinguish between calls and puts at a glance. The desired behavior is for the Type column to show 'CALL' or 'PUT' for option positions, and 'stock' for stock positions.

## HOW
- The CLI builds the positions table from a list of position dictionaries, each with a 'Type' field.
- The OptionPosition class and its to_dict() method already include an 'option_type' field ('CALL' or 'PUT').
- Update the CLI code (src/cli/commands/portfolio.py) that builds the table to set the 'Type' field to the value of 'option_type' for option positions, and 'stock' for stocks.
- No changes to business logic or data models are required.

## Scope
- Trivial display change.
- Only affects CLI table-building logic in src/cli/commands/portfolio.py.
- No impact on data models, business logic, or other interfaces.

## Assumptions
- All option positions have a valid 'option_type' field in their dict representation.
- No legacy data without this field is in use.

## Open Questions / Blocking Issues
- None. Requirement is clear and implementation is straightforward.

## Next Steps
1. Update CLI table-building logic to use 'option_type' for option positions in the Type column.
2. Test the CLI to confirm correct display.
