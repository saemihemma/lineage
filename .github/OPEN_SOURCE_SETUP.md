# Open Source Setup Guide

This guide contains instructions for the remaining manual steps to complete the open source setup.

## Manual Steps Required

### 1. Make Repository Public

**Via GitHub Web UI:**
1. Go to https://github.com/saemihemma/lineage
2. Click **Settings** (gear icon in repository header)
3. Scroll down to **Danger Zone**
4. Click **Change visibility**
5. Select **Make public**
6. Type repository name to confirm
7. Click **I understand, change repository visibility**

**Via GitHub CLI:**
```bash
gh repo edit saemihemma/lineage --visibility public
```

### 2. Enable GitHub Features

**Settings → General:**
1. Go to repository Settings
2. Scroll to **Features** section
3. Enable:
   - ✅ **Issues** (for bug reports and feature requests)
   - ✅ **Projects** (optional, for project management)
   - ✅ **Wiki** (optional, for documentation)
   - ✅ **Discussions** (optional, for community Q&A)

**Merge Settings:**
1. In Settings → General → Pull Requests
2. Enable all merge options:
   - ✅ Allow merge commits
   - ✅ Allow squash merging
   - ✅ Allow rebase merging

### 3. Set Up Branch Protection Rules

**For `web-version` branch:**
1. Go to **Settings → Branches**
2. Click **Add rule** or edit existing rule for `web-version`
3. Configure:
   - **Branch name pattern:** `web-version`
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: **1**
     - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging
     - Select: **Test Suite** (from GitHub Actions)
   - ✅ **Require conversation resolution before merging**
   - ✅ **Do not allow bypassing the above settings**
   - ✅ **Restrict who can push to matching branches** (optional - only you)
   - ✅ **Do not allow force pushes**
   - ✅ **Do not allow deletions**

**For `main` branch (if exists):**
- Same settings as above
- Consider requiring **2 approvals** for production branch

### 4. Set Up Labels

**Issues → Labels → New label:**

Create these labels:
- `bug` (red, #d73a4a) - Something isn't working
- `enhancement` (green, #a2eeef) - New feature or request
- `documentation` (blue, #0075ca) - Improvements or additions to documentation
- `good first issue` (purple, #7057ff) - Good for newcomers
- `help wanted` (yellow, #008672) - Extra attention is needed
- `question` (orange, #d876e3) - Further information is requested
- `wontfix` (grey, #ffffff) - This will not be worked on
- `duplicate` (grey, #cfd3d7) - This issue or pull request already exists

### 5. Create GitHub Secrets (if needed)

**Settings → Secrets and variables → Actions:**

For CI/CD (if using secrets in GitHub Actions):
- `HMAC_SECRET_KEY_V1` - For anti-cheat signing (test values in CI)
- `CSRF_SECRET_KEY` - For CSRF protection (test values in CI)

**Note:** These are already set in CI workflow with test values, so this may not be needed.

## Quick PR Management Commands

### Using GitHub CLI (`gh`)

**Install GitHub CLI:**
```bash
# macOS
brew install gh

# Then authenticate
gh auth login
```

**Common PR Commands:**
```bash
# List all open PRs
gh pr list

# View a specific PR
gh pr view <number>

# Checkout a PR locally
gh pr checkout <number>

# Merge a PR (squash merge)
gh pr merge <number> --squash

# Add a review comment
gh pr review <number> --comment "Looks good!"

# Approve a PR
gh pr review <number> --approve

# Close a PR
gh pr close <number>
```

### Using GitHub Web UI

1. **Review PRs:** Go to Pull Requests tab
2. **Review:** Click on PR → Review changes → Add comments/approve
3. **Merge:** After approval, click "Merge pull request"
4. **Delete branch:** Option to delete branch after merge

## Post-Launch Checklist

After making the repository public:

- [ ] Announce on social media / dev forums
- [ ] Monitor first PRs/issues closely
- [ ] Set up automated responses (optional)
- [ ] Create roadmap/backlog (GitHub Projects)
- [ ] Engage with community in discussions
- [ ] Review and respond to issues promptly

## Security Reminder

Before going public, ensure:
- ✅ No `.env` files committed
- ✅ No hardcoded API keys
- ✅ No database credentials
- ✅ No personal tokens
- ✅ All secrets use environment variables
- ✅ Railway/production URLs are environment variables only

All checks completed ✅ - Repository is ready to be made public!

