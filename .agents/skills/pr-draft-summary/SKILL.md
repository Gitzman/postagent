---
name: pr-draft-summary
description: Generate a structured PR description when code work is finished or ready for review. Auto-collects branch, tree status, changed files, diffs, and commits.
trigger: When task is finished and ready for review or PR creation
output: Branch name suggestion, PR title, structured draft description
---

# PR Draft Summary

## Steps
1. Collect context via scripts:
   - `git branch --show-current`
   - `git status --short`
   - `git diff --stat main...HEAD`
   - `git log --oneline main...HEAD`
2. Analyze the diff to produce:
   - **PR Title**: Under 70 chars, describes the "what"
   - **Summary**: 1-3 bullet points of what changed and why
   - **Test Plan**: Checklist of verification steps
   - **Breaking Changes**: Any API or schema changes that affect consumers

## Output Format
```
## Summary
- bullet points

## Test plan
- [ ] verification steps

## Breaking changes
- none / list
```
