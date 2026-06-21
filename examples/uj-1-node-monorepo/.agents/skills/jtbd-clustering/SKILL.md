---
name: jtbd-clustering
description: Cluster forces from multiple JTBD interviews to identify patterns. Use after extracting from multiple interviews.
---

# JTBD Forces Clustering

Cluster and categorize forces from multiple interviews for pattern analysis.

## When to Use

When you have JTBD extractions from multiple interviews and need to identify patterns across them.

## The Process

1. **Create a matrix:**
   - Rows = interview stories
   - Columns = distinct forces

2. **Code each interview:**
   - Start with first story's forces as initial columns
   - For each new story:
     - If force matches existing column: mark "1"
     - If force is novel: add new column

3. **Abstraction pass:**
   - Review columns for grouping opportunities
   - Rename with overarching descriptors
   - Merge similar forces

4. **Analysis questions:**
   - Which forces appear most frequently?
   - Which stories introduced unique forces?
   - What patterns emerge across segments?

## Output

1. **Spreadsheet summary:** Number of stories and forces identified
2. **Force categories:** Abstract labels for each column
3. **Unique contributors:** Stories that introduced novel forces
4. **Patterns and insights:** Notable observations

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
