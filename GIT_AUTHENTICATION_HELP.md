# Git Authentication Help

## Current Status
- Branch: `web-version`
- Remote: `https://github.com/saemihemma/lineage.git`
- Using HTTPS (requires Personal Access Token)

## If Git Push Fails

### Option 1: Test Current Token (Recommended First Step)
```bash
git push origin web-version
```

If it fails with authentication error, continue to Option 2.

### Option 2: Update Personal Access Token
1. Go to GitHub: https://github.com/settings/tokens
2. Generate new token with these scopes:
   - ✅ `repo` (full repository access)
   - ✅ `workflow` (if you want to update GitHub Actions)
3. Copy the new token
4. Update git credentials:

```bash
# Option A: Use credential helper (recommended)
git config --global credential.helper osxkeychain  # macOS
# Then on next push, enter your username and paste the new token as password

# Option B: Use token in URL (temporary, less secure)
git remote set-url origin https://YOUR_TOKEN@github.com/saemihemma/lineage.git
# Replace YOUR_TOKEN with your actual token
```

### Option 3: Use SSH Instead (More Secure)
```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add SSH key to GitHub
# Copy public key: cat ~/.ssh/id_ed25519.pub
# Add to: https://github.com/settings/keys

# Change remote to SSH
git remote set-url origin git@github.com:saemihemma/lineage.git
```

## Quick Test
```bash
# Test connection
git ls-remote origin

# If that works, you're good to push
git add .
git commit -m "feat: PostgreSQL transaction fix + womb expansion"
git push origin web-version
```

## Current Changes Ready to Commit
- PostgreSQL transaction abort fix (autocommit mode)
- Womb expansion system (multiple wombs, durability, attention)
- Regression tests for bugs
- All bug fixes from production

