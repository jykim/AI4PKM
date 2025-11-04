# Guidelines for Claude Code Agent

This document provides guidelines for Claude Code when working on this repository.

## Git Commit Policy

**CRITICAL: Never commit to main/master branch without explicit user approval.**

### Workflow for Making Changes

1. **Create a Feature Branch**
   - Always create a new branch for any changes
   - Use descriptive branch names (e.g., `fix/output-validation`, `feature/new-agent`)
   - Never work directly on main/master

2. **Making Changes**
   - Read and understand the code before making changes
   - Make focused, incremental changes
   - Test changes when possible
   - **Always update relevant documentation when making changes**
     - Update README files if behavior changes
     - Update docs/ files for user-facing features
     - Update code comments for internal changes
     - Keep documentation in sync with code

3. **Committing Changes**
   - **WAIT for explicit user approval before committing**
   - User must explicitly say "commit" or "create a commit"
   - Phrases like "let's do 1&2" mean "do the work" not "commit the work"
   - Write clear, descriptive commit messages
   - Use conventional commit format: `type: description`

4. **Pushing Changes**
   - **WAIT for explicit user approval before pushing**
   - User must explicitly say "push" or similar
   - Never assume approval to push based on commit approval

5. **Creating Pull Requests**
   - Only create PRs when explicitly requested
   - Include clear description of changes
   - Link to relevant issues or discussions
   - Wait for user review and approval

## When to Ask for Clarification

Always ask when:
- User's intent about committing/pushing is unclear
- Multiple valid approaches exist for a problem
- Changes affect critical system behavior
- You're unsure about the scope of requested changes

## Example Interaction

❌ **Incorrect:**
```
User: "Let's implement feature X"
Claude: [implements feature, commits, pushes automatically]
```

✅ **Correct:**
```
User: "Let's implement feature X"
Claude: [implements feature]
Claude: "I've implemented feature X. The changes are ready. Would you like me to commit them?"
User: "Yes, commit"
Claude: [commits]
Claude: "Changes committed to branch fix/feature-x. Would you like me to push and create a PR?"
User: "Yes"
Claude: [pushes and creates PR]
```

## Special Cases

### Emergency Fixes
Even for critical bugs, wait for user approval before committing to main.

### Reverts
If you accidentally commit to main:
1. Inform the user immediately
2. Offer to revert the commit
3. Create a proper branch and PR for the changes

### Documentation
Documentation changes still require explicit approval before committing.

## Remember

**User approval must be EXPLICIT, not IMPLIED.**

When in doubt, ask for clarification rather than assuming approval.
