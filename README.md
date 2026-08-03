# A7X Tour Tracker — Automation v2

This version fixes the duplicate/specialty-set issue by:

1. grouping returned entries by event date,
2. preferring the exact tour name `North American Tour 2026`,
3. preferring the longest/full set,
4. rejecting short non-tour specialty entries.

It also uses Node 24-compatible GitHub Actions:

- `actions/checkout@v5`
- `actions/setup-python@v6`

## Files to upload

```text
.github/workflows/daily-update.yml
data/tour-data.json
tracker/__init__.py
tracker/config.py
tracker/fetch.py
tracker/stats.py
tracker/render.py
index.html
update_tracker.py
README.md
```

## First verification

1. Upload all files and folders.
2. Open **Actions → Update A7X Tour Tracker**.
3. Choose **Run workflow**.
4. Open the completed run and expand **Fetch setlists and regenerate site**.
5. Confirm the log reports selected full-tour shows and no four-song Statica entry.
6. Vercel will redeploy after the automated commit.
