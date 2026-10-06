# Data analysis interview questions

Q: Walk me through your process for a new dataset.
A: Clarify the business question, inspect shape, types and missing values, clean, explore distributions and relationships, form hypotheses, test them, and communicate findings with clear visuals and recommendations.

Q: How do you detect and treat outliers?
A: Use box plots, z-scores or the IQR rule, then investigate whether they are errors or real events. Remove, cap or keep them depending on cause and business impact, and document the decision.

Q: What is the difference between correlation and causation?
A: Correlation is co-movement; causation means one variable produces change in another. Establishing causation needs experiments or careful causal methods that control confounders.

Q: Explain a p-value in plain language.
A: It is the probability of seeing results at least as extreme as observed if the null hypothesis were true. A small p-value is evidence against the null, not the probability the null is true.

Q: How would you design an A/B test?
A: Define one primary metric and hypothesis, compute sample size for desired power, randomize users, run for full business cycles without peeking, then test significance and check practical effect size.

Q: Mean versus median: when to use which?
A: The mean is sensitive to outliers; the median is robust. For skewed data such as salaries or order values, report the median, often alongside the mean.

Q: How do you handle missing data in analysis?
A: Quantify it, understand the mechanism, then drop, impute or flag it. Be transparent about how it could bias results.

Q: A key metric dropped 15% this week. What do you do?
A: Verify data quality and tracking first, then segment by time, region, device, channel and product to localize the drop, check releases or external events, and report findings with next steps.

Q: How do you choose the right chart?
A: Match the chart to the question: lines for trends, bars for comparisons, scatter for relationships, histograms for distributions. Avoid clutter and misleading axes.

Q: What is a pivot table or group-by used for?
A: Summarizing data by categories, such as revenue by region and month, quickly exposing patterns and totals.

Q: Explain cohort analysis.
A: Grouping users by a shared start event, such as signup month, and tracking behavior like retention over time to see whether newer cohorts do better.

Q: How do you make sure stakeholders trust your analysis?
A: Define metrics clearly, validate numbers against source systems, document assumptions, show uncertainty, and explain results in business terms.
