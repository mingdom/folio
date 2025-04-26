# A Concise, Opinionated Guide to Writing Good Code (with Python examples)

This guide summarizes core principles for writing clean, maintainable, and effective code. It's opinionated and rule-based, designed to provide clear direction for junior developers. Adhering to these rules will help you build better software and become a more valuable team member. Python examples are provided for clarity.

## 1. Naming Matters Immensely

* **Rule:** Use intention-revealing names.
    * **Don't:** `d = (datetime.now() - start_date).days`
    * **Do:** `elapsed_time_in_days = (datetime.now() - start_date).days`
* **Rule:** Avoid disinformation.
    * **Don't:** `account_list = {"id": 1, "name": "Alice"}` (It's a dictionary, not a list)
    * **Do:** `account_data = {"id": 1, "name": "Alice"}` or `account_dict = ...`
* **Rule:** Use pronounceable and searchable names.
    * **Don't:** `genymdhms = datetime.now().strftime('%Y%m%d%H%M%S')`
    * **Do:** `generation_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')`
* **Rule:** Be consistent.
    * **Don't:** Using `fetch_user_data`, `getUserInfo`, `retrieve_client_details` in the same project.
    * **Do:** Consistently use one style, e.g., `get_user_data`, `get_order_info`, `get_product_details`.

## 2. Functions Should Be Small and Focused

* **Rule:** Functions must do **one thing**.
    * **Don't:**
        ```python
        def process_user_data(user_id):
            # Fetches data
            response = requests.get(f"/api/users/{user_id}")
            user_data = response.json()
            # Validates data
            if not user_data.get("email"):
                raise ValueError("Email missing")
            # Saves data
            db.save(user_data)
            # Sends notification
            send_email(user_data["email"], "Welcome!")
            return user_data
        ```
    * **Do:** Break it down:
        ```python
        def fetch_user_data(user_id):
            response = requests.get(f"/api/users/{user_id}")
            response.raise_for_status() # Raise HTTP errors
            return response.json()

        def validate_user_data(user_data):
            if not user_data.get("email"):
                raise ValueError("Email missing")
            # ... other validations

        def save_user_data(user_data):
            db.save(user_data)

        def send_welcome_email(email_address):
            send_email(email_address, "Welcome!")

        def register_user(user_id):
            user_data = fetch_user_data(user_id)
            validate_user_data(user_data)
            save_user_data(user_data)
            send_welcome_email(user_data["email"])
            return user_data
        ```
* **Rule:** Functions must be **small**. (The "Do" example above also illustrates this).
* **Rule:** Minimize function arguments.
    * **Don't:** `def create_user(name, email, password, dob, address, phone, role, is_active): ...`
    * **Do:**
        ```python
        class UserProfile:
            def __init__(self, name, email, dob, address, phone):
                # ... initialization ...

        def create_user(profile: UserProfile, password: str, role: str, is_active: bool = True):
             # ... use profile attributes ...
        ```
        Or pass a dictionary:
        ```python
        def create_user(user_details: dict):
            # Access details via user_details['name'], user_details['email'] etc.
            # Consider using TypedDict for better structure if using Python 3.8+
            ...
        ```
* **Rule:** Avoid side effects where possible.
    * **Don't (Hidden Side Effect):**
        ```python
        user_list = []
        def add_user_if_valid(name, email):
            if "@" in email:
                user_list.append({"name": name, "email": email}) # Modifies global state
                return True
            return False
        ```
    * **Do (Explicit):**
        ```python
        def create_user_record(name, email):
            if "@" not in email:
                raise ValueError("Invalid email")
            return {"name": name, "email": email}

        # Usage
        try:
            new_user = create_user_record("Bob", "bob@example.com")
            user_list.append(new_user) # State change happens outside the function
        except ValueError as e:
            print(f"Error: {e}")
        ```

## 3. Comments Are for "Why," Not "What"

* **Rule:** Comment the "Why," not the "What."
    * **Don't:**
        ```python
        # Check if user is eligible
        if age >= 18 and country == "US": # This just repeats the code
            is_eligible = True
        ```
    * **Do:**
        ```python
        # User must be a legal adult in the US to qualify for this specific offer.
        if age >= 18 and country == "US":
            is_eligible = True
        ```
* **Rule:** Do **not** leave commented-out code.
    * **Don't:**
        ```python
        def calculate_total(items):
            total = 0
            for item in items:
                total += item['price']
            # tax = total * 0.10 # Old tax calculation
            # total += tax
            total *= 1.10 # Apply 10% tax
            return total
        ```
    * **Do:** Remove the commented lines. Use Git history if you need to see the old calculation.
        ```python
        def calculate_total(items):
            total = sum(item['price'] for item in items)
            total *= 1.10 # Apply 10% tax
            return total
        ```
* **Rule:** Keep comments up-to-date. (Self-explanatory - if the logic changes, update or remove the comment).
* **Rule:** Avoid redundant comments.
    * **Don't:**
        ```python
        count = 0 # Initialize count
        count += 1 # Increment count
        ```
    * **Do:** Just the code is enough.
        ```python
        count = 0
        count += 1
        ```

## 4. Formatting and Structure Enhance Readability

* **Rule:** Use a consistent style guide (e.g., PEP 8 for Python). Use tools like `Black`, `Flake8`, `isort`.
    * **Don't:** Inconsistent spacing, line lengths, import orders.
    * **Do:** Code automatically formatted by tools like `Black`.
* **Rule:** Top-down narrative.
    * **Don't:** Define helper functions *before* the main function that uses them, forcing the reader to jump around.
    * **Do:**
        ```python
        def main_process():
            data = _fetch_data()
            result = _process_data(data)
            _save_result(result)

        # --- Helper functions defined below ---
        def _fetch_data(): ...
        def _process_data(data): ...
        def _save_result(result): ...
        ```
        *(Note: Leading underscore `_` often indicates internal/helper functions)*
* **Rule:** Keep related concepts vertically close. (The example above also shows this).
* **Rule:** Use whitespace.
    * **Don't:**
        ```python
        def process(a,b,c):
            x=a+b
            y=x*c
            if y>10:
                print("Large")
            else:
                print("Small")
            z=y-a
            return z
        ```
    * **Do:**
        ```python
        def process(a, b, c):
            intermediate_value = a + b
            final_value = intermediate_value * c

            if final_value > 10:
                print("Large")
            else:
                print("Small")

            adjusted_value = final_value - a
            return adjusted_value
        ```

## 5. Keep It Simple (KISS & YAGNI)

* **Rule:** KISS (Keep It Simple, Stupid).
    * **Don't:** Using complex metaprogramming or obscure language features when a simple loop or conditional would suffice.
    * **Do:** Prefer straightforward, readable solutions.
* **Rule:** YAGNI (You Ain't Gonna Need It).
    * **Don't:** Adding configuration options, database fields, or API endpoints for features that *might* be needed in the future but aren't required now.
    * **Do:** Implement only what's necessary for the current requirements.
* **Rule:** Avoid premature optimization.
    * **Don't:** Spending hours micro-optimizing a function with string concatenations before profiling to see if it's even a bottleneck.
    * **Do:** Write clean code first. If performance is an issue (measure it!), profile and optimize the specific hotspots. Often, a better algorithm beats micro-optimization.

## 6. Don't Repeat Yourself (DRY)

* **Rule:** Avoid duplication.
    * **Don't:**
        ```python
        def process_file_a(path):
            # 10 lines of validation logic
            if not valid: return None
            # Process file A specific logic
            ...

        def process_file_b(path):
            # Same 10 lines of validation logic copied here
            if not valid: return None
            # Process file B specific logic
            ...
        ```
    * **Do:**
        ```python
        def _validate_input(path):
            # 10 lines of validation logic
            return is_valid

        def process_file_a(path):
            if not _validate_input(path): return None
            # Process file A specific logic
            ...

        def process_file_b(path):
            if not _validate_input(path): return None
            # Process file B specific logic
            ...
        ```

## 7. Handle Errors Gracefully

* **Rule:** Use exceptions over error codes.
    * **Don't:**
        ```python
        def divide(a, b):
            if b == 0:
                return -1 # Error code
            return a / b

        result = divide(10, 0)
        if result == -1:
            print("Error: Division by zero")
        ```
    * **Do:**
        ```python
        def divide(a, b):
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b

        try:
            result = divide(10, 0)
        except ValueError as e:
            print(f"Error: {e}")
        ```
* **Rule:** Provide context with errors.
    * **Don't:** `raise Exception("Error!")`
    * **Do:** `raise ValueError(f"Invalid user ID format: '{user_id_str}'")`

## 8. Test Your Code

* **Rule:** Write unit tests (using frameworks like `pytest` or `unittest`).
    * **Don't:** Skipping tests because the code "looks simple."
    * **Do:**
        ```python
        # Example using pytest
        from my_module import add

        def test_add_positive_numbers():
            assert add(2, 3) == 5

        def test_add_negative_numbers():
            assert add(-1, -1) == -2

        def test_add_mixed_numbers():
            assert add(5, -3) == 2
        ```
* **Rule:** Test behavior, not implementation.
    * **Don't:** Writing a test that checks if a specific private helper method (`_helper`) was called.
    * **Do:** Writing a test that checks if the public method produces the correct output or state change, regardless of which internal helpers were used.
* **Rule:** Keep tests clean, readable, and fast. (Apply the same principles from this guide to your test code).

## 9. Practice Continuous Refactoring

* **Rule:** Follow the Boy Scout Rule.
    * **Don't:** Seeing a poorly named variable or a slightly complex block of code and leaving it because "it works."
    * **Do:** Taking a few moments to rename the variable or extract a small function to improve clarity before committing your primary change.
* **Rule:** Refactoring is part of development. (This is a mindset, less about specific code examples).

## 10. Optimize for Readability

* **Rule:** Code is read more than written.
    * **Don't:** Using overly clever one-liners or complex list comprehensions that are hard to decipher.
        ```python
        # Clever but potentially hard to read
        result = [x**2 for x in range(10) if x % 2 == 0 and x > 3]
        ```
    * **Do:** Prioritize clarity, even if it means slightly more verbose code.
        ```python
        result = []
        for x in range(10):
            is_even = x % 2 == 0
            is_greater_than_3 = x > 3
            if is_even and is_greater_than_3:
                result.append(x**2)
        # Or a more readable comprehension if appropriate
        result = [x**2 for x in range(4, 10, 2)] # Clearer range
        ```

## 11. Python-Specific Best Practices

* **Rule:** Embrace Pythonic idioms.
    * **Use List Comprehensions (when clear):** Prefer `squares = [x*x for x in numbers]` over manual `for` loop appends for simple transformations.
    * **Use Context Managers (`with` statement):** Ensure resources like files or network connections are properly closed.
        ```python
        # Don't
        f = open("myfile.txt", "w")
        try:
            f.write("Hello")
        finally:
            f.close()

        # Do
        with open("myfile.txt", "w") as f:
            f.write("Hello")
        # File is automatically closed here, even if errors occur
        ```
    * **Iterate Directly:** Iterate over sequences directly instead of using index manipulation.
        ```python
        # Don't
        for i in range(len(my_list)):
            print(my_list[i])

        # Do
        for item in my_list:
            print(item)

        # Do (if index is needed)
        for i, item in enumerate(my_list):
            print(f"Index {i}: {item}")
        ```
* **Rule:** Use Type Hinting (Python 3.5+). Improves readability, enables static analysis tools (`mypy`), and clarifies intent.
    ```python
    # Don't
    def greet(name):
        print("Hello " + name)

    # Do
    def greet(name: str) -> None:
        print("Hello " + name)

    def add(a: int, b: int) -> int:
        return a + b
    ```
* **Rule:** Use Virtual Environments (`venv`). Isolate project dependencies to avoid conflicts between projects. Always create and activate a virtual environment before installing packages (`pip install ...`).
* **Rule:** Prefer f-strings (Python 3.6+) for string formatting. They are generally more readable and often faster than `.format()` or `%` formatting.
    ```python
    name = "Alice"
    age = 30

    # Don't (older styles)
    print("Name: %s, Age: %d" % (name, age))
    print("Name: {}, Age: {}".format(name, age))

    # Do
    print(f"Name: {name}, Age: {age}")
    ```
* **Rule:** Understand Mutable Default Arguments. Be wary of using mutable types (like lists or dicts) as default function arguments, as they are shared across calls.
    ```python
    # Don't (potential bug)
    def add_item(item, my_list=[]):
        my_list.append(item)
        return my_list

    list1 = add_item(1) # [1]
    list2 = add_item(2) # [1, 2] - Unexpected!

    # Do
    def add_item(item, my_list=None):
        if my_list is None:
            my_list = []
        my_list.append(item)
        return my_list

    list1 = add_item(1) # [1]
    list2 = add_item(2) # [2] - Correct
