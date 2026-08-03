# A7X Tour Tracker — Automatic Updater

Required GitHub Actions secret: `SETLIST_FM_API_KEY`

## First run
1. Open the repository **Actions** tab.
2. Select **Update A7X Tour Tracker**.
3. Tap **Run workflow**.
4. When it finishes, it will commit a generated `index.html` and `data/tour-data.json` if setlist data changed.
5. Vercel will redeploy the GitHub commit automatically.

The workflow also checks daily at 13:00 UTC.
