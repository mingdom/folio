# Big Picture on migration
- Create file structure based on [master-plan-concise.md]
- Seed the files with function signatures
- Migrate each file iteratively (details below):
    - Add to docstring each function or class the reference file/function from prior implementation
    - Determine if interfaces are compatible or if changes are needed per function, create a plan
    - Implement based on compatibility, repeat until every function in a file is implemented
    - Fully refactor codebase to use the new function
    - Rinse repeat for every function, every file
- The main idea is to take the smallest slice of refactoring and fully apply it before moving on to the next slice. This lets us test early and find issues early. It also let us iterate on our approach / discover issues early


# Log
- first PR: https://github.com/mingdom/folio/pull/3/files, domain.py and data/stock.py complete.
- no need for pnl specific logic. that should all get wrapped into simulation
- beta is just a feature of stock.py, no need for seperate calculations
