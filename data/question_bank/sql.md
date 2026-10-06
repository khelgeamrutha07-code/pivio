# SQL interview questions

Q: What is the difference between INNER, LEFT, RIGHT and FULL joins?
A: INNER returns only matching rows. LEFT keeps all left rows with NULLs for non-matches, RIGHT does the reverse, and FULL keeps all rows from both sides.

Q: WHERE versus HAVING?
A: WHERE filters rows before grouping; HAVING filters groups after aggregation, so it can use aggregates like COUNT(*) > 5.

Q: What is a window function? Give an example.
A: It computes a value across related rows without collapsing them, using OVER (PARTITION BY ... ORDER BY ...). Example: ROW_NUMBER() to rank salaries within each department.

Q: How do you find duplicate rows?
A: GROUP BY the identifying columns and use HAVING COUNT(*) > 1, or use ROW_NUMBER() partitioned by those columns and keep rn = 1 to deduplicate.

Q: What is a primary key versus a foreign key?
A: A primary key uniquely identifies each row and cannot be NULL. A foreign key references another table's key to enforce referential integrity.

Q: Explain indexes and their trade-offs.
A: Indexes, typically B-trees, speed up lookups, joins and sorts on indexed columns but use storage and slow down writes. Index columns used often in filters and joins, and check the query plan.

Q: What is a CTE and when would you use one?
A: A WITH clause defining a named temporary result for readability, reuse within one query, or recursion such as walking hierarchies.

Q: Difference between UNION and UNION ALL?
A: UNION removes duplicates, which costs a sort or hash; UNION ALL keeps all rows and is faster when duplicates are impossible or acceptable.

Q: How do you get the second highest salary?
A: Use DENSE_RANK() ordered by salary descending and pick rank 2, or SELECT MAX(salary) WHERE salary < (SELECT MAX(salary) ...). DENSE_RANK handles ties cleanly.

Q: What is normalization?
A: Organizing tables to reduce redundancy, usually to third normal form, by splitting data so each fact is stored once. Analytics systems sometimes denormalize on purpose for read speed.

Q: How do you handle NULLs in aggregations and comparisons?
A: NULL is unknown, so comparisons need IS NULL, aggregates ignore NULLs except COUNT(*), and COALESCE supplies defaults.

Q: How would you debug a slow query?
A: Run EXPLAIN or EXPLAIN ANALYZE, look for full scans and bad join order, add or fix indexes, filter early, select only needed columns and check statistics are current.
