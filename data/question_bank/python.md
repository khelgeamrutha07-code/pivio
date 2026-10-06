# Python interview questions

Q: What is the difference between a list and a tuple?
A: Lists are mutable and tuples are immutable. Tuples are hashable when their items are, so they can be dict keys, and they signal fixed-size records.

Q: How do Python decorators work?
A: A decorator is a callable that takes a function and returns a wrapped function, applied with @name syntax. Use functools.wraps to preserve metadata. Common uses are logging, caching and auth checks.

Q: Explain generators and when to use them.
A: Generators use yield to produce values lazily, one at a time, keeping memory flat. Use them for large files or streams instead of building full lists.

Q: What is the GIL?
A: The Global Interpreter Lock lets only one thread run Python bytecode at a time in CPython. CPU-bound work needs multiprocessing; I/O-bound work still benefits from threads or asyncio.

Q: Difference between shallow copy and deep copy?
A: A shallow copy duplicates the outer container but shares nested objects; deepcopy recursively copies nested objects so changes do not leak between copies.

Q: What are *args and **kwargs?
A: *args collects extra positional arguments into a tuple and **kwargs collects extra keyword arguments into a dict. They allow flexible signatures and argument forwarding.

Q: How does Python manage memory?
A: Reference counting frees objects when counts reach zero, and a cyclic garbage collector handles reference cycles. Objects live on a private heap.

Q: What is a list comprehension and why prefer it?
A: A concise expression like [x*x for x in xs if x > 0] that builds a list. It is usually faster and more readable than an equivalent loop with append.

Q: Explain the difference between "is" and "==".
A: "==" compares values via __eq__; "is" compares object identity. Use "is" for None checks.

Q: How do you handle exceptions properly?
A: Catch specific exceptions in try/except, use else for success-only code and finally for cleanup, never use a bare except, and raise custom exceptions with clear messages.

Q: What are context managers?
A: Objects implementing __enter__ and __exit__ (or built with contextlib.contextmanager) so the "with" statement guarantees setup and cleanup, such as closing files or releasing locks.

Q: How would you speed up slow pandas code?
A: Vectorize instead of looping or apply, use appropriate dtypes such as category, avoid chained copies, read only needed columns, and profile first. For very large data consider chunking or a columnar engine.
