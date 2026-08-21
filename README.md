# Speedadmin API - KunstLab Varde calendar feed

Publishes PLAY bookings for KunstLab Varde (SchoolId 6655) from the SpeedAdmin API as a
subscribable `.ics` feed, refreshed hourly by GitHub Actions and served via GitHub Pages.

## Setup

1. Add a repository secret `SPEEDADMIN_API_KEY` (Settings > Secrets and variables > Actions).
2. Enable GitHub Pages: Settings > Pages > Source = branch `main`, folder `/docs`.
3. Trigger the "Update KunstLab Varde calendar" workflow once manually (Actions tab > Run workflow)
   to generate the initial `docs/kunstlab-varde.ics`.

The feed will then be available at:

```
https://<github-username>.github.io/<repo>/kunstlab-varde.ics
```

## Subscribing (Google Calendar)

1. Open Google Calendar on the web.
2. Next to "Other calendars", click `+` > "From URL".
3. Paste the feed URL above and click "Add calendar".

Google Calendar polls external ICS URLs on its own schedule (historically every 12-24 hours),
so new bookings may take a while to appear even though the feed itself updates hourly.

## Local run

```
pip install -r requirements.txt
$env:SPEEDADMIN_API_KEY = "<your key>"
python scripts/generate_calendar.py
```
