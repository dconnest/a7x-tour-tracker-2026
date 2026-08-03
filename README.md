# A7X Tour Tracker 2026

Automatic static-site updater for the 2026 North American tour.

## Required GitHub secret

`SETLIST_FM_API_KEY`

## First run

1. Open the repository's **Actions** tab.
2. Select **Update A7X Tour Tracker**.
3. Click **Run workflow**.
4. Wait for a green check mark.
5. The workflow will update `index.html` and `data/tour-data.json`.
6. Vercel will redeploy the new GitHub commit automatically.

## Daily schedule

The updater runs daily at 13:00 UTC, approximately 9:00 AM Eastern during daylight-saving time.
