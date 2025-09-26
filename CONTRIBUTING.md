# Docuparse Contribution Guidelines

## ⚠️ CRITICAL: Main Branch Protection Rules

**Since GitHub's technical branch protection isn't available on our free plan, we rely on TEAM DISCIPLINE and these strict guidelines.**

- **NEVER** push directly to main (`git push origin main`)
- **NEVER** force push to shared branches
- **ALWAYS** use Pull Requests for main branch changes
- **ALWAYS** get team approval before merging

## Branch Structure

- **`main`** - Production code only. Requires PR + approval
- **`develop`** - Integration/testing branch
- **Individual branches**: `HemanthRayudu`,`Omraut`,`PeiYing`

## Daily Workflow

### 1. Start Work
```bash
git checkout YourName
git pull origin develop
git pull origin YourName
```

### 2. Completed a task/issue or a feature
```bash
# Work and commit
git add .
git commit -m "Clear description of changes"
git push origin YourName

# When ready to integrate:
git checkout develop
git pull origin develop
git merge YourName
git push origin develop
```

### 3. Team Testing (MANDATORY)
After ANY push to develop:
- Pusher notifies team: "🧪 Pushed [feature] to develop - please test!"
- **ALL 3 teammates** must test locally and approve
- Only merge to main after all approvals

## Pull Requests

### When to Create:
- `YourName → develop`: Feature integration
- `develop → main`: Production release (requires all 3 approvals)

### PR Format:
```
[Type] Brief description

## What Changed?
- Key changes

## How to Test?  
- Testing steps

## Checklist:
- [ ] Tested locally
- [ ] Requirements updated
- [ ] No sensitive data
```

## Team Testing Protocol

### After develop push:
1. All teammates pull and test develop branch
2. Each gives explicit approval: "✅ Tested - looks good!"
3. Only create develop → main PR after ALL approve
4. If issues found: "🚨 Found issue: [description]"

## Commit Standards

**Good**: `Add pdfplumber for text extraction`  
**Bad**: `fix`, `update`, `working`

Format: `[Action] What changed` (under 50 chars)

## Emergency Fixes

### Accidental main push:
```bash
git checkout main
git revert <commit-hash>
git push origin main
```

### Broken develop:
1. Stop all merges
2. Create hotfix from working commit
3. Fix and test
4. PR to develop

## Communication

- **Before major changes**: Discuss with team
- **When stuck**: Ask for help immediately  
- **After breaking something**: Notify team right away
- **Daily**: Brief progress updates

## Success Metrics

✅ **Good**: No main pushes, PRs reviewed quickly, main always works  
🚩 **Bad**: Direct main pushes, unreviewed PRs, broken main

**Remember**: We're a team. When in doubt, ask! Better to over-communicate than break main.
