# Publish to GitHub

Local repo is committed on `main`. GitHub CLI is not authenticated on this machine yet.

```bash
# One-time
gh auth login

# Create brand-new public repo and push
cd /Users/koyukinakamori/signora
gh repo create signora --public \
  --description "SignOra — Bittensor subnet for ASL video to English translation" \
  --source=. --remote=origin --push
```

Use a different repo name or org if needed:

```bash
gh repo create YOUR_ORG/signora --public --source=. --remote=origin --push
```

After push, share: `https://github.com/YOUR_USER/signora`
