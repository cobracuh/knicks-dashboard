# New York Knicks Dashboard

An interactive Streamlit dashboard for the New York Knicks' current regular season. It includes team performance, recent games, league-relative strengths and weaknesses, player statistics, headshots, and a complete game log.

## Run locally

1. Install Python 3.11 or newer.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the dashboard:

   ```bash
   streamlit run app.py
   ```

The app will open at `http://localhost:8501`.

## Deploy with Streamlit Community Cloud

1. Push this repository to GitHub.
2. Sign in at [share.streamlit.io](https://share.streamlit.io/).
3. Select **Create app** and choose this repository.
4. Set the main file path to `app.py`.
5. Deploy the app.

The dashboard reads current regular-season schedules and statistics from ESPN's public JSON feeds. No API key is required.

## Automatic data updates

GitHub Actions refreshes the saved data every day at 6:00 AM Central Time. When the data changes, the workflow commits the new snapshot and Streamlit Community Cloud automatically redeploys the dashboard. The workflow can also be run manually from the repository's **Actions** tab.

## Project files

- `app.py` — Streamlit application
- `requirements.txt` — Python dependencies
- `scripts/update_snapshot.py` — validates and saves the latest NBA data
- `.github/workflows/refresh-data.yml` — daily refresh automation
- `assets/knicks-starting-five.png` — dashboard header artwork
