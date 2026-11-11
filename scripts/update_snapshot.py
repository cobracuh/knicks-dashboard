from __future__ import annotations

import time
from datetime import date, datetime, timezone
from pathlib import Path

from nba_api.stats.endpoints import (
    leaguegamelog,
    leaguedashplayerstats,
    leaguedashteamstats,
)


KNICKS_ID = 1610612752
ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "data"
MAX_ATTEMPTS = 3


def current_nba_season() -> str:
    today = date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def fetch_snapshot(season: str):
    all_games = leaguegamelog.LeagueGameLog(
        season=season,
        season_type_all_star="Regular Season",
        player_or_team_abbreviation="T",
        timeout=60,
    ).get_data_frames()[0]
    games = all_games.loc[all_games["TEAM_ID"] == KNICKS_ID].copy()

    teams = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
        timeout=60,
    ).get_data_frames()[0]

    players_base = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=KNICKS_ID,
        measure_type_detailed_defense="Base",
        per_mode_detailed="PerGame",
        timeout=60,
    ).get_data_frames()[0]

    players_advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=KNICKS_ID,
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
        timeout=60,
    ).get_data_frames()[0]

    advanced_columns = [
        "PLAYER_ID",
        "TS_PCT",
        "USG_PCT",
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "AST_PCT",
        "REB_PCT",
        "PIE",
    ]
    available_advanced = [
        column for column in advanced_columns if column in players_advanced.columns
    ]
    players = players_base.merge(
        players_advanced[available_advanced],
        on="PLAYER_ID",
        how="left",
    )

    return games, teams, players


def validate_snapshot(games, teams, players) -> None:
    required_games = {"TEAM_ID", "GAME_DATE", "MATCHUP", "WL", "PTS"}
    required_teams = {"TEAM_ID", "TEAM_NAME", "OFF_RATING", "DEF_RATING"}
    required_players = {"PLAYER_ID", "PLAYER_NAME", "GP", "PTS"}

    for name, frame, required in (
        ("games", games, required_games),
        ("teams", teams, required_teams),
        ("players", players, required_players),
    ):
        missing = required.difference(frame.columns)
        if frame.empty:
            raise ValueError(f"NBA.com returned no {name} data")
        if missing:
            raise ValueError(f"{name} data is missing columns: {sorted(missing)}")

    if len(teams) < 30:
        raise ValueError(f"Expected 30 NBA teams, received {len(teams)}")
    if not teams["TEAM_ID"].eq(KNICKS_ID).any():
        raise ValueError("The Knicks are missing from the league snapshot")


def csv_text(frame, sort_columns: list[str]) -> str:
    available = [column for column in sort_columns if column in frame.columns]
    if available:
        frame = frame.sort_values(available).reset_index(drop=True)
    return frame.to_csv(index=False, lineterminator="\n")


def save_if_changed(season: str, games, teams, players) -> bool:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "games.csv": csv_text(games, ["GAME_DATE", "GAME_ID"]),
        "league.csv": csv_text(teams, ["TEAM_ID"]),
        "players.csv": csv_text(players, ["PLAYER_ID"]),
    }

    changed = any(
        not (OUTPUT_DIR / name).exists()
        or (OUTPUT_DIR / name).read_text(encoding="utf-8") != content
        for name, content in files.items()
    )
    if not changed:
        print("NBA data is unchanged; no files were updated.")
        return False

    for name, content in files.items():
        (OUTPUT_DIR / name).write_text(content, encoding="utf-8")

    refreshed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    (OUTPUT_DIR / "snapshot.txt").write_text(
        f"season={season}\nrefreshed_at_utc={refreshed_at}\n",
        encoding="utf-8",
    )
    print(
        f"Saved {len(games)} Knicks games, {len(teams)} teams, "
        f"and {len(players)} Knicks players."
    )
    return True


def main() -> None:
    season = current_nba_season()
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            games, teams, players = fetch_snapshot(season)
            validate_snapshot(games, teams, players)
            save_if_changed(season, games, teams, players)
            return
        except Exception as error:
            last_error = error
            if attempt == MAX_ATTEMPTS:
                break
            delay = attempt * 10
            print(f"Refresh attempt {attempt} failed: {error}. Retrying in {delay}s.")
            time.sleep(delay)

    raise RuntimeError(
        f"Could not refresh the Knicks snapshot after {MAX_ATTEMPTS} attempts"
    ) from last_error


if __name__ == "__main__":
    main()
