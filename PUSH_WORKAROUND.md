# Workflow File Push Issue - Quick Fix

## Problem
GitHub blocks pushing commits that modify `.github/workflows/` files without a Personal Access Token that has the `workflow` scope.

## Solutions

### Option 1: Update Your Personal Access Token (Recommended)
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Find your token (or create a new one)
3. Edit it and check the `workflow` scope
4. Save and update your git credential helper with the new token
5. Try pushing again: `git push origin web-version`

### Option 2: Push Without Workflow Commit
If you can't update the token right now, push everything except the workflow commit:

```bash
# Push only commits after the workflow one
# Find the workflow commit hash first:
git log --oneline | grep workflow

# Then push from the commit BEFORE the workflow one
# (Replace <commit-before-workflow> with actual hash)
git push origin <commit-before-workflow>:web-version --force-with-lease
```

**Note**: Option 2 is more complex. Option 1 is easier.

### Option 3: Temporarily Remove Workflow File (Quick Fix)
Remove the workflow file from the recent commits so you can push:

```bash
# Remove workflow file from git tracking (keeps file locally)
git rm --cached .github/workflows/tests.yml

# Commit the removal
git commit -m "Remove workflow file to allow push without workflow scope"

# Now push
git push origin web-version
```

**Note**: This removes the workflow file from the repo. You can add it back later when you have the workflow scope.

### Option 4: Use SSH Instead
If you have SSH keys set up with GitHub:
```bash
# Change remote URL to SSH
git remote set-url origin git@github.com:saemihemma/lineage.git

# Push via SSH (no token needed)
git push origin web-version
```

---

## Recommended Action
**Use Option 1** - it's the cleanest solution and allows you to manage workflow files going forward.

If you need the workflow file removed temporarily, **Option 3** is the quickest workaround.

