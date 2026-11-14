from __future__ import annotations

import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests


KNICKS_ID = 1610612752
ESPN_KNICKS_ID = "18"
ROOT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT_DIR / "data"
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT = 30
HEADERS = {"User-Agent": "knicks-dashboard/1.0"}


def current_nba_season() -> tuple[str, int]:
    today = date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}", start_year + 1


def get_json(url: str, params: dict | None = None) -> dict:
    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def category_values(item: dict, display_name: str) -> list[float]:
    for category in item.get("categories", []):
        if category.get("displayName") == display_name:
            return category.get("values", [])
    raise ValueError(f"ESPN response is missing {display_name}")


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else float("nan")


def fetch_games(season_year: int) -> pd.DataFrame:
    payload = get_json(
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/ny/schedule",
        {"season": season_year},
    )
    rows = []
    for event in payload.get("events", []):
        competition = event["competitions"][0]
        if not competition.get("status", {}).get("type", {}).get("completed"):
            continue

        competitors = competition.get("competitors", [])
        knicks = next(
            (team for team in competitors if team.get("team", {}).get("id") == ESPN_KNICKS_ID),
            None,
        )
        opponent = next((team for team in competitors if team is not knicks), None)
        if not knicks or not opponent:
            continue

        knicks_points = float(knicks["score"]["value"])
        opponent_points = float(opponent["score"]["value"])
        location = "vs." if knicks.get("homeAway") == "home" else "@"
        opponent_abbr = opponent["team"]["abbreviation"]
        rows.append(
            {
                "TEAM_ID": KNICKS_ID,
                "GAME_ID": event["id"],
                "GAME_DATE": event["date"][:10],
                "MATCHUP": f"NYK {location} {opponent_abbr}",
                "WL": "W" if knicks.get("winner") else "L",
                "PTS": int(knicks_points),
                "PLUS_MINUS": int(knicks_points - opponent_points),
            }
        )
    return pd.DataFrame(rows)


def fetch_teams(season_year: int) -> pd.DataFrame:
    payload = get_json(
        "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byteam",
        {
            "region": "us",
            "lang": "en",
            "contentorigin": "espn",
            "season": season_year,
            "seasontype": 2,
            "limit": 100,
        },
    )
    rows = []
    for item in payload.get("teams", []):
        team = item["team"]
        general = category_values(item, "Own General")
        opponent_general = category_values(item, "Opponent General")
        defensive = category_values(item, "Own Defensive")
        opponent_defensive = category_values(item, "Opponent Defensive")
        offensive = category_values(item, "Own Offensive")
        opponent_offensive = category_values(item, "Opponent Offensive")

        points, turnovers, fga, fta, oreb, assists = (
            offensive[0],
            offensive[4],
            offensive[7],
            offensive[11],
            offensive[12],
            offensive[13],
        )
        opp_points, opp_turnovers, opp_fga, opp_fta, opp_oreb = (
            opponent_offensive[0],
            opponent_offensive[4],
            opponent_offensive[7],
            opponent_offensive[11],
            opponent_offensive[12],
        )
        dreb = defensive[1]
        opp_dreb = opponent_defensive[1]
        possessions = fga - oreb + turnovers + 0.44 * fta
        opponent_possessions = opp_fga - opp_oreb + opp_turnovers + 0.44 * opp_fta
        offensive_rating = 100 * safe_divide(points, possessions)
        defensive_rating = 100 * safe_divide(opp_points, opponent_possessions)

        espn_id = team["id"]
        rows.append(
            {
                "TEAM_ID": KNICKS_ID if espn_id == ESPN_KNICKS_ID else int(espn_id),
                "TEAM_NAME": team["displayName"],
                "GP": int(general[7]),
                "OFF_RATING": offensive_rating,
                "DEF_RATING": defensive_rating,
                "NET_RATING": offensive_rating - defensive_rating,
                "TS_PCT": safe_divide(points, 2 * (fga + 0.44 * fta)),
                "AST_RATIO": 100 * safe_divide(assists, possessions),
                "OREB_PCT": safe_divide(oreb, oreb + opp_dreb),
                "DREB_PCT": safe_divide(dreb, dreb + opp_oreb),
                "TM_TOV_PCT": 100 * safe_divide(turnovers, possessions),
                "REB": general[1],
                "OPP_REB": opponent_general[1],
            }
        )
    return pd.DataFrame(rows)


def fetch_players(season_year: int) -> pd.DataFrame:
    payload = get_json(
        "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/statistics/byathlete",
        {
            "region": "us",
            "lang": "en",
            "contentorigin": "espn",
            "isqualified": "false",
            "sort": "offensive.avgPoints:desc",
            "season": season_year,
            "seasontype": 2,
            "limit": 500,
        },
    )
    rows = []
    for item in payload.get("athletes", []):
        athlete = item["athlete"]
        if athlete.get("teamId") != ESPN_KNICKS_ID:
            continue

        general = category_values(item, "Own General")
        offensive = category_values(item, "Own Offensive")
        defensive = category_values(item, "Own Defensive")
        points, fga, fta = offensive[0], offensive[2], offensive[8]
        rows.append(
            {
                "PLAYER_ID": int(athlete["id"]),
                "PLAYER_NAME": athlete["displayName"],
                "GP": int(general[0]),
                "MIN": general[1],
                "PTS": points,
                "REB": general[11],
                "AST": offensive[10],
                "STL": defensive[0],
                "BLK": defensive[1],
                "FG_PCT": offensive[3] / 100,
                "FG3_PCT": offensive[6] / 100,
                "FT_PCT": offensive[9] / 100,
                "TS_PCT": safe_divide(points, 2 * (fga + 0.44 * fta)),
                "USG_PCT": float("nan"),
                "NET_RATING": float("nan"),
            }
        )
    return pd.DataFrame(rows)


def fetch_snapshot(season_year: int):
    return fetch_games(season_year), fetch_teams(season_year), fetch_players(season_year)


def validate_snapshot(games, teams, players) -> None:
    required_games = {"TEAM_ID", "GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS"}
    required_teams = {"TEAM_ID", "TEAM_NAME", "OFF_RATING", "DEF_RATING"}
    required_players = {"PLAYER_ID", "PLAYER_NAME", "GP", "PTS"}
    for name, frame, required in (
        ("games", games, required_games),
        ("teams", teams, required_teams),
        ("players", players, required_players),
    ):
        missing = required.difference(frame.columns)
        if frame.empty:
            raise ValueError(f"ESPN returned no {name} data")
        if missing:
            raise ValueError(f"{name} data is missing columns: {sorted(missing)}")

    if len(teams) != 30:
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
        print("ESPN data is unchanged; no files were updated.")
        return False

    for name, content in files.items():
        (OUTPUT_DIR / name).write_text(content, encoding="utf-8")
    refreshed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    (OUTPUT_DIR / "snapshot.txt").write_text(
        f"season={season}\nsource=ESPN\nrefreshed_at_utc={refreshed_at}\n",
        encoding="utf-8",
    )
    print(
        f"Saved {len(games)} Knicks games, {len(teams)} teams, "
        f"and {len(players)} Knicks players."
    )
    return True


def main() -> None:
    season, season_year = current_nba_season()
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            games, teams, players = fetch_snapshot(season_year)
            validate_snapshot(games, teams, players)
            save_if_changed(season, games, teams, players)
            return
        except Exception as error:
            last_error = error
            if attempt == MAX_ATTEMPTS:
                break
            delay = attempt * 5
            print(f"Refresh attempt {attempt} failed: {error}. Retrying in {delay}s.")
            time.sleep(delay)
    raise RuntimeError(
        f"Could not refresh the Knicks snapshot after {MAX_ATTEMPTS} attempts"
    ) from last_error


if __name__ == "__main__":
    main()
