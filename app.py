import base64
import html
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from nba_api.stats.endpoints import (
    leaguegamelog,
    leaguedashplayerstats,
    leaguedashteamstats,
)


KNICKS_ID = 1610612752
KNICKS_BLUE = "#006BB6"
KNICKS_ORANGE = "#F58426"
INK = "#10233F"
MUTED = "#667085"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SNAPSHOT_DIR = Path(__file__).resolve().parent / "data"


def current_nba_season() -> str:
    today = date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def image_data_uri(path: Path) -> str:
    encoded_path = path.with_suffix(".b64")
    if encoded_path.exists():
        encoded = encoded_path.read_text(encoding="utf-8").strip()
        return f"data:image/png;base64,{encoded}"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,600;0,700;0,800&family=Inter:wght@400;500;600;700&display=swap');

        :root {{
            --knicks-blue: {KNICKS_BLUE};
            --knicks-orange: {KNICKS_ORANGE};
            --knicks-ink: {INK};
            --surface: rgba(255,255,255,.94);
            --line: rgba(16,35,63,.10);
        }}
        html, body, [class*="css"] {{
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        .stApp {{
            background:
                radial-gradient(circle at 94% 0%, rgba(245,132,38,.15), transparent 27rem),
                radial-gradient(circle at 5% 24%, rgba(0,107,182,.08), transparent 23rem),
                linear-gradient(180deg, #f7faff 0%, #ffffff 34rem);
        }}
        .block-container {{
            max-width: 1220px;
            padding-top: 1.6rem;
            padding-bottom: 3.5rem;
        }}
        .hero {{
            position: relative;
            overflow: hidden;
            isolation: isolate;
            min-height: 315px;
            padding: 2.2rem 2.5rem;
            margin-bottom: 1.45rem;
            border: 1px solid rgba(255,255,255,.16);
            border-radius: 28px;
            color: white;
            background:
                linear-gradient(105deg, rgba(255,255,255,.055), transparent 38%),
                linear-gradient(120deg, #0a1c35 0%, {INK} 26%, {KNICKS_BLUE} 78%, #0f86d2 100%);
            box-shadow: 0 22px 55px rgba(16,35,63,.22), inset 0 1px 0 rgba(255,255,255,.14);
        }}
        .hero::before {{
            content: "NYK";
            position: absolute;
            z-index: -1;
            right: -5rem;
            top: -6rem;
            width: 28rem;
            height: 28rem;
            border: 1px solid rgba(255,255,255,.10);
            border-radius: 50%;
            color: transparent;
            background: radial-gradient(circle, rgba(255,255,255,.10) 0%, rgba(245,132,38,.08) 42%, transparent 70%);
        }}
        .hero::after {{
            display: none;
        }}
        .hero-copy {{
            position: relative;
            z-index: 3;
            max-width: 43%;
        }}
        .hero-brand-lockup {{
            display: flex;
            align-items: center;
            gap: .75rem;
            margin-bottom: .35rem;
        }}
        .hero-logo {{
            position: static;
            width: 58px;
            height: 58px;
            object-fit: contain;
            filter: drop-shadow(0 8px 10px rgba(0,0,0,.22));
        }}
        .hero-starting-five {{
            position: absolute;
            z-index: 2;
            right: -1.5%;
            bottom: 0;
            width: 68%;
            max-height: 96%;
            object-fit: contain;
            object-position: right bottom;
            filter: drop-shadow(0 16px 22px rgba(0,0,0,.30));
            pointer-events: none;
        }}
        .hero-kicker {{
            display: inline-flex;
            align-items: center;
            gap: .5rem;
            white-space: nowrap;
            color: #ffc58b;
            font-size: .75rem;
            font-weight: 800;
            letter-spacing: .19em;
            text-transform: uppercase;
        }}
        .hero-kicker::before {{
            content: "";
            width: 26px;
            height: 3px;
            border-radius: 999px;
            background: {KNICKS_ORANGE};
        }}
        .hero h1 {{
            margin: .22rem 0 .35rem 0;
            color: white;
            font-family: "Barlow Condensed", Impact, sans-serif;
            font-size: clamp(3rem, 6.7vw, 5.7rem);
            font-weight: 800;
            line-height: .91;
            letter-spacing: .015em;
            text-transform: uppercase;
            text-wrap: balance;
            text-shadow: 0 7px 22px rgba(0,0,0,.22);
        }}
        .hero h1 span {{
            color: inherit;
        }}
        .hero h1 span:not([class]) {{
            color: #ff9b43;
        }}
        .hero p {{
            max-width: 640px;
            margin: 0;
            color: rgba(255,255,255,.76);
            font-size: .97rem;
            line-height: 1.65;
        }}
        div[data-testid="stMetric"] {{
            position: relative;
            overflow: hidden;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1.05rem 1.1rem 1.08rem;
            box-shadow: 0 9px 28px rgba(16,35,63,.065);
            transition: transform .18s ease, box-shadow .18s ease;
        }}
        div[data-testid="stMetric"]::before {{
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            background: linear-gradient(180deg, {KNICKS_ORANGE}, #ffad69);
        }}
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 14px 34px rgba(16,35,63,.10);
        }}
        div[data-testid="stMetricLabel"] {{ color: {MUTED}; font-size: .82rem; font-weight: 600; }}
        div[data-testid="stMetricValue"] {{
            color: {INK};
            font-family: "Barlow Condensed", Impact, sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            letter-spacing: .01em;
        }}
        h2, h3 {{
            color: {INK};
            font-family: "Barlow Condensed", Impact, sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: .015em !important;
        }}
        h3 {{ font-size: 1.7rem !important; margin-top: 1.15rem !important; }}
        .section-note {{ color: {MUTED}; margin-top: -.55rem; margin-bottom: .7rem; }}
        .recent-games-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .75rem;
            margin: .2rem 0 1.35rem;
        }}
        .recent-game {{
            position: relative;
            overflow: hidden;
            padding: 1rem;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,.92);
            box-shadow: 0 8px 24px rgba(16,35,63,.06);
        }}
        .recent-game::before {{
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 4px;
            background: {KNICKS_BLUE};
        }}
        .recent-game.loss::before {{ background: {KNICKS_ORANGE}; }}
        .recent-game-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .4rem;
            color: {MUTED};
            font-size: .76rem;
            font-weight: 600;
        }}
        .result-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 1.7rem;
            height: 1.7rem;
            border-radius: 999px;
            color: white;
            background: {KNICKS_BLUE};
            font-size: .72rem;
            font-weight: 800;
        }}
        .loss .result-badge {{ background: {KNICKS_ORANGE}; }}
        .recent-game-opponent {{ margin-top: .7rem; color: {INK}; font-weight: 700; }}
        .recent-game-score {{
            margin-top: .12rem;
            color: {INK};
            font-family: "Barlow Condensed", Impact, sans-serif;
            font-size: 1.65rem;
            font-weight: 700;
            line-height: 1;
        }}
        .recent-game-margin {{ margin-top: .4rem; color: {MUTED}; font-size: .76rem; }}
        .strengths-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
            margin: .25rem 0 1.3rem;
        }}
        .strength-panel {{
            padding: 1.15rem 1.2rem;
            border: 1px solid var(--line);
            border-radius: 18px;
            background: rgba(255,255,255,.92);
            box-shadow: 0 9px 28px rgba(16,35,63,.06);
        }}
        .strength-panel h4 {{
            margin: 0 0 .75rem;
            color: {INK};
            font-family: "Barlow Condensed", Impact, sans-serif;
            font-size: 1.3rem;
            letter-spacing: .015em;
        }}
        .team-readout {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            padding: .7rem 0;
            border-top: 1px solid rgba(16,35,63,.08);
        }}
        .team-readout:first-of-type {{ border-top: 0; padding-top: 0; }}
        .team-readout:last-child {{ padding-bottom: 0; }}
        .metric-name {{ display: block; color: {INK}; font-size: .87rem; font-weight: 700; }}
        .metric-value {{ display: block; margin-top: .14rem; color: {MUTED}; font-size: .77rem; }}
        .rank-pill {{
            flex: 0 0 auto;
            padding: .33rem .58rem;
            border-radius: 999px;
            color: {KNICKS_BLUE};
            background: rgba(0,107,182,.10);
            font-size: .75rem;
            font-weight: 800;
        }}
        .watch .rank-pill {{ color: #a84e0b; background: rgba(245,132,38,.14); }}
        .player-spotlight {{
            display: flex;
            align-items: center;
            gap: 1.4rem;
            min-height: 180px;
            padding: 0 1.5rem 0 0;
            margin: .25rem 0 1rem 0;
            overflow: hidden;
            border: 1px solid var(--line);
            border-left: 7px solid {KNICKS_ORANGE};
            border-radius: 0 20px 20px 0;
            background:
                radial-gradient(circle at 4% 100%, rgba(0,107,182,.18), transparent 44%),
                linear-gradient(105deg, rgba(0,107,182,.11), rgba(255,255,255,.82));
            box-shadow: 0 10px 30px rgba(16,35,63,.065);
        }}
        .player-spotlight img {{
            align-self: flex-end;
            width: 210px;
            max-height: 190px;
            object-fit: contain;
            object-position: bottom center;
            filter: drop-shadow(0 10px 12px rgba(16,35,63,.17));
        }}
        .player-spotlight h3 {{
            color: {INK};
            margin: 0 !important;
            font-family: "Barlow Condensed", Impact, sans-serif;
            font-size: 2.25rem !important;
            font-weight: 700;
            letter-spacing: .01em;
        }}
        .player-spotlight p {{ color: {MUTED}; margin: .3rem 0 0 0; }}
        @media (max-width: 650px) {{
            .recent-games-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .strengths-grid {{ grid-template-columns: 1fr; }}
            .player-spotlight {{ gap: .6rem; padding-right: .75rem; min-height: 140px; }}
            .player-spotlight img {{ width: 145px; max-height: 145px; }}
            .player-spotlight h3 {{ font-size: 1.3rem; }}
        }}
        .source-note {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e5ecf5;
            color: {MUTED};
            font-size: .82rem;
        }}
        div[data-baseweb="tab-list"] {{
            gap: .45rem;
            padding: .3rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: rgba(255,255,255,.66);
            box-shadow: 0 6px 20px rgba(16,35,63,.045);
        }}
        button[data-baseweb="tab"] {{
            border-radius: 10px;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
            font-family: "Inter", sans-serif;
            font-weight: 600;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {KNICKS_BLUE};
            background: rgba(0,107,182,.085);
        }}
        div[data-baseweb="select"] > div,
        div[data-testid="stDataFrame"] {{
            border-radius: 14px;
        }}
        @media (max-width: 650px) {{
            .hero {{ min-height: 340px; padding: 1.45rem 1.4rem; border-radius: 22px; }}
            .hero-copy {{ max-width: 100%; }}
            .hero h1 {{ font-size: clamp(2.65rem, 11vw, 3.55rem); }}
            .hero-logo {{ width: 43px; height: 43px; }}
            .hero-kicker {{ font-size: .61rem; letter-spacing: .12em; }}
            .hero-kicker::before {{ display: none; }}
            .hero-starting-five {{
                right: -6%;
                width: 112%;
                max-height: 52%;
                object-position: center bottom;
            }}
            .hero::before {{ width: 18rem; height: 18rem; right: -7rem; top: -4rem; }}
        }}
        @media (min-width: 651px) and (max-width: 950px) {{
            .hero {{ min-height: 390px; }}
            .hero-copy {{ max-width: 100%; }}
            .hero-starting-five {{
                right: -2%;
                width: 100%;
                max-height: 57%;
                object-position: center bottom;
            }}
            .recent-games-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl="1h", show_spinner="Updating Knicks data...")
def load_data(season: str):
    all_games = leaguegamelog.LeagueGameLog(
        season=season,
        season_type_all_star="Regular Season",
        player_or_team_abbreviation="T",
        timeout=12,
    ).get_data_frames()[0]
    games = all_games.loc[all_games["TEAM_ID"] == KNICKS_ID].copy()

    teams = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
        timeout=12,
    ).get_data_frames()[0]

    players_base = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=KNICKS_ID,
        measure_type_detailed_defense="Base",
        per_mode_detailed="PerGame",
        timeout=12,
    ).get_data_frames()[0]

    players_advanced = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Regular Season",
        team_id_nullable=KNICKS_ID,
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
        timeout=12,
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

    if not games.empty:
        games["GAME_DATE"] = pd.to_datetime(games["GAME_DATE"])
        games = games.sort_values("GAME_DATE")

    return games, teams, players, datetime.now()


@st.cache_data(show_spinner=False)
def load_snapshot():
    games = pd.read_csv(SNAPSHOT_DIR / "games.csv")
    teams = pd.read_csv(SNAPSHOT_DIR / "league.csv")
    players = pd.read_csv(SNAPSHOT_DIR / "players.csv")
    games["GAME_DATE"] = pd.to_datetime(games["GAME_DATE"])
    games = games.sort_values("GAME_DATE")
    refreshed_at = datetime.fromtimestamp((SNAPSHOT_DIR / "snapshot.txt").stat().st_mtime)
    return games, teams, players, refreshed_at


def team_rank(league: pd.DataFrame, column: str, ascending: bool) -> int | None:
    if column not in league.columns or league.empty:
        return None
    ranks = league[column].rank(ascending=ascending, method="min")
    matching = ranks.loc[league["TEAM_ID"] == KNICKS_ID]
    return int(matching.iloc[0]) if not matching.empty else None


def rank_label(value: int | None) -> str:
    return f"NBA rank {value}" if value is not None else "Rank unavailable"


def pct(value) -> str:
    return "—" if pd.isna(value) else f"{value:.1%}"


def number(value, decimals: int = 1, signed: bool = False) -> str:
    if pd.isna(value):
        return "—"
    pattern = f"{{:{'+' if signed else ''}.{decimals}f}}"
    return pattern.format(value)


TEAM_METRIC_SPECS = [
    ("OFF_RATING", "Offensive rating", False, "number"),
    ("DEF_RATING", "Defensive rating", True, "number"),
    ("TS_PCT", "True shooting", False, "pct"),
    ("AST_RATIO", "Assist ratio", False, "number"),
    ("OREB_PCT", "Offensive rebounding", False, "pct"),
    ("DREB_PCT", "Defensive rebounding", False, "pct"),
    ("TM_TOV_PCT", "Turnover rate", True, "rate"),
    ("NET_RATING", "Net rating", False, "signed"),
]


def team_metric_rankings(league: pd.DataFrame):
    knicks_rows = league.loc[league["TEAM_ID"] == KNICKS_ID]
    if knicks_rows.empty:
        return [], [], 0

    knicks = knicks_rows.iloc[0]
    team_count = int(league["TEAM_ID"].nunique())
    ranked_metrics = []
    for column, label, ascending, value_type in TEAM_METRIC_SPECS:
        if column not in league.columns or pd.isna(knicks.get(column)):
            continue
        rank = team_rank(league, column, ascending)
        if rank is not None:
            ranked_metrics.append(
                {
                    "column": column,
                    "label": label,
                    "rank": rank,
                    "value": knicks[column],
                    "value_type": value_type,
                }
            )

    strengths = sorted(ranked_metrics, key=lambda item: item["rank"])[:3]
    strength_columns = {item["column"] for item in strengths}
    weaknesses = sorted(
        [item for item in ranked_metrics if item["column"] not in strength_columns],
        key=lambda item: item["rank"],
        reverse=True,
    )[:3]
    return strengths, weaknesses, team_count


def team_metric_value(metric: dict) -> str:
    value = metric["value"]
    if metric["value_type"] == "pct":
        return pct(value)
    if metric["value_type"] == "signed":
        return number(value, signed=True)
    if metric["value_type"] == "rate":
        return f"{number(value)}%" if abs(value) > 1 else pct(value)
    return number(value)


def team_readout_html(metrics: list[dict], team_count: int, css_class: str) -> str:
    return "".join(
        f'<div class="team-readout {css_class}">'
        f'<div><span class="metric-name">{html.escape(metric["label"])}</span>'
        f'<span class="metric-value">Current value: {team_metric_value(metric)}</span></div>'
        f'<span class="rank-pill">#{metric["rank"]} of {team_count}</span></div>'
        for metric in metrics
    )


def recent_games_html(games: pd.DataFrame) -> str:
    cards = []
    for _, game in games.tail(5).iloc[::-1].iterrows():
        result = str(game["WL"])
        margin = float(game["PLUS_MINUS"])
        knicks_points = int(round(float(game["PTS"])))
        opponent_points = int(round(knicks_points - margin))
        opponent = str(game["MATCHUP"]).split()[-1]
        location = "at" if "@" in str(game["MATCHUP"]) else "vs"
        css_class = "win" if result == "W" else "loss"
        cards.append(
            f'<div class="recent-game {css_class}">'
            f'<div class="recent-game-top"><span>{game["GAME_DATE"].strftime("%b %d")}</span>'
            f'<span class="result-badge">{html.escape(result)}</span></div>'
            f'<div class="recent-game-opponent">{location} {html.escape(opponent)}</div>'
            f'<div class="recent-game-score">NYK {knicks_points} · {html.escape(opponent)} {opponent_points}</div>'
            f'<div class="recent-game-margin">Margin {margin:+.0f}</div></div>'
        )
    return '<div class="recent-games-grid">' + "".join(cards) + "</div>"


def player_headshot_url(player_id, compact: bool = False) -> str:
    size = "260x190" if compact else "1040x760"
    return f"https://cdn.nba.com/headshots/nba/latest/{size}/{int(player_id)}.png"


st.set_page_config(
    page_title="New York Knicks Dashboard",
    page_icon="🏀",
    layout="wide",
)
inject_styles()

season = current_nba_season()
starting_five_image = image_data_uri(ASSETS_DIR / "knicks-starting-five.png")

st.markdown(
    f"""
    <div class="hero">
      <div class="hero-copy">
        <div class="hero-brand-lockup">
          <img class="hero-logo"
               src="https://cdn.nba.com/logos/nba/1610612752/primary/L/logo.svg"
               alt="New York Knicks logo">
          <div class="hero-kicker">Season dashboard · {season}</div>
        </div>
        <h1>New York <span>Knicks</span></h1>
      </div>
      <img class="hero-starting-five"
           src="{starting_five_image}"
           alt="Knicks starting five: Jalen Brunson, Mikal Bridges, Josh Hart, OG Anunoby, and Karl-Anthony Towns">
    </div>
    """,
    unsafe_allow_html=True,
)

data_status = "Live NBA.com data"
try:
    games, league, players, fetched_at = load_data(season)
except Exception:
    try:
        games, league, players, fetched_at = load_snapshot()
        data_status = "NBA.com snapshot fallback"
    except Exception as snapshot_exc:
        st.error(
            "The NBA data service did not respond and the saved dashboard data "
            "could not be loaded."
        )
        with st.expander("Technical details"):
            st.code(str(snapshot_exc))
        st.stop()

if games.empty:
    st.warning(f"No Knicks regular-season games were returned for {season}.")
    st.stop()

overview_tab, players_tab, games_tab = st.tabs(
    ["TEAM OVERVIEW", "PLAYER STATS", "GAME LOG"]
)


with overview_tab:
    period = st.segmented_control(
        "Game window",
        options=["Full season", "Last 10", "Last 5"],
        default="Full season",
    )

    if period == "Last 10":
        selected_games = games.tail(10).copy()
    elif period == "Last 5":
        selected_games = games.tail(5).copy()
    else:
        selected_games = games.copy()

    wins = int(selected_games["WL"].eq("W").sum())
    losses = int(selected_games["WL"].eq("L").sum())
    win_pct = wins / len(selected_games) if len(selected_games) else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Record", f"{wins}–{losses}")
    kpi2.metric("Win percentage", f"{win_pct:.1%}")
    kpi3.metric("Points per game", f"{selected_games['PTS'].mean():.1f}")
    kpi4.metric(
        "Point differential",
        f"{selected_games['PLUS_MINUS'].mean():+.1f}",
    )

    st.subheader("Recent games")
    st.markdown(
        '<p class="section-note">The five latest results, with the most recent game first.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(recent_games_html(games), unsafe_allow_html=True)

    st.subheader("Performance trend")
    st.markdown(
        '<p class="section-note">Five-game rolling point differential; above zero means the Knicks are outscoring opponents.</p>',
        unsafe_allow_html=True,
    )
    selected_games["ROLLING_DIFF"] = (
        selected_games["PLUS_MINUS"].rolling(5, min_periods=1).mean()
    )
    trend = px.line(
        selected_games,
        x="GAME_DATE",
        y="ROLLING_DIFF",
        markers=True,
        custom_data=["MATCHUP", "WL", "PLUS_MINUS"],
        color_discrete_sequence=[KNICKS_BLUE],
    )
    trend.update_traces(
        line={"width": 4},
        marker={"size": 8, "color": KNICKS_ORANGE, "line": {"color": "white", "width": 2}},
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "%{x|%b %d, %Y}<br>"
            "Result: %{customdata[1]} · Game margin: %{customdata[2]:+}<br>"
            "Rolling differential: %{y:+.1f}<extra></extra>"
        ),
    )
    trend.add_hline(y=0, line_dash="dot", line_color="#98A2B3")
    trend.update_layout(
        height=390,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis_title=None,
        yaxis_title="Points",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(trend, width="stretch")

    knicks_rows = league.loc[league["TEAM_ID"] == KNICKS_ID]
    if not knicks_rows.empty:
        knicks = knicks_rows.iloc[0]
        strengths, weaknesses, team_count = team_metric_rankings(league)
        if strengths and weaknesses:
            st.subheader("Team strengths and weaknesses")
            st.markdown(
                '<p class="section-note">Based on current regular-season rank among NBA teams. These rankings describe performance; they do not explain why it happened.</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="strengths-grid">'
                '<div class="strength-panel"><h4>Strengths · Best league ranks</h4>'
                f'{team_readout_html(strengths, team_count, "strength")}</div>'
                '<div class="strength-panel"><h4>Areas to improve</h4>'
                f'{team_readout_html(weaknesses, team_count, "watch")}</div></div>',
                unsafe_allow_html=True,
            )

        st.subheader("League context")
        rating1, rating2, rating3 = st.columns(3)
        rating1.metric(
            "Offensive rating",
            number(knicks.get("OFF_RATING")),
            rank_label(team_rank(league, "OFF_RATING", ascending=False)),
            delta_color="off",
        )
        rating2.metric(
            "Defensive rating",
            number(knicks.get("DEF_RATING")),
            rank_label(team_rank(league, "DEF_RATING", ascending=True)),
            delta_color="off",
        )
        rating3.metric(
            "Net rating",
            number(knicks.get("NET_RATING"), signed=True),
            rank_label(team_rank(league, "NET_RATING", ascending=False)),
            delta_color="off",
        )


with players_tab:
    if players.empty:
        st.info("Player statistics are not available yet.")
    else:
        players = players.sort_values(["PTS", "MIN"], ascending=False).copy()
        player_names = players["PLAYER_NAME"].dropna().tolist()
        selected_name = st.selectbox("Choose a player", player_names)
        selected_player = players.loc[players["PLAYER_NAME"] == selected_name].iloc[0]

        st.markdown(
            f"""
            <div class="player-spotlight">
              <img src="{player_headshot_url(selected_player['PLAYER_ID'])}" alt="{selected_name} headshot"
                   onerror="this.style.display='none'">
              <div>
                <h3>{selected_name}</h3>
                <p>{int(selected_player['GP'])} games · {selected_player['MIN']:.1f} minutes per game</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        stat1, stat2, stat3, stat4 = st.columns(4)
        stat1.metric("Points", number(selected_player.get("PTS")))
        stat2.metric("Rebounds", number(selected_player.get("REB")))
        stat3.metric("Assists", number(selected_player.get("AST")))
        stat4.metric("Minutes", number(selected_player.get("MIN")))

        eff1, eff2, eff3, eff4 = st.columns(4)
        eff1.metric("Field goal", pct(selected_player.get("FG_PCT")))
        eff2.metric("Three-point", pct(selected_player.get("FG3_PCT")))
        eff3.metric("True shooting", pct(selected_player.get("TS_PCT")))
        eff4.metric("Usage", pct(selected_player.get("USG_PCT")))

        st.subheader("Player comparison")
        st.markdown(
            '<p class="section-note">Scoring volume versus shooting efficiency. Bubble size represents minutes per game.</p>',
            unsafe_allow_html=True,
        )
        max_games = max(1, int(players["GP"].max()))
        default_games = min(5, max_games)
        minimum_games = st.slider(
            "Minimum games played",
            min_value=1,
            max_value=max_games,
            value=default_games,
        )
        eligible = players.loc[players["GP"] >= minimum_games].copy()
        eligible["TS_DISPLAY"] = eligible["TS_PCT"] * 100
        eligible["SELECTED"] = eligible["PLAYER_NAME"].eq(selected_name)

        player_chart = px.scatter(
            eligible,
            x="PTS",
            y="TS_DISPLAY",
            size="MIN",
            color="SELECTED",
            color_discrete_map={False: KNICKS_BLUE, True: KNICKS_ORANGE},
            hover_name="PLAYER_NAME",
            hover_data={
                "GP": True,
                "MIN": ":.1f",
                "REB": ":.1f",
                "AST": ":.1f",
                "SELECTED": False,
                "TS_DISPLAY": False,
            },
            labels={"PTS": "Points per game", "TS_DISPLAY": "True shooting %"},
        )
        player_chart.update_traces(
            marker={"line": {"color": "white", "width": 2}},
            hovertemplate=None,
        )
        player_chart.update_layout(
            height=450,
            showlegend=False,
            margin={"l": 10, "r": 10, "t": 10, "b": 10},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis_ticksuffix="%",
        )
        st.plotly_chart(player_chart, width="stretch")

        st.subheader("Roster statistics")
        roster_columns = [
            "PLAYER_ID",
            "PLAYER_NAME",
            "GP",
            "MIN",
            "PTS",
            "REB",
            "AST",
            "STL",
            "BLK",
            "FG_PCT",
            "FG3_PCT",
            "TS_PCT",
            "NET_RATING",
        ]
        roster_columns = [column for column in roster_columns if column in players.columns]
        roster = players[roster_columns].copy()
        if "PLAYER_ID" in roster.columns:
            roster.insert(
                0,
                "PHOTO",
                roster["PLAYER_ID"].map(lambda player_id: player_headshot_url(player_id, compact=True)),
            )
            roster = roster.drop(columns="PLAYER_ID")
        for column in ["FG_PCT", "FG3_PCT", "TS_PCT"]:
            if column in roster.columns:
                roster[column] = roster[column] * 100

        st.dataframe(
            roster,
            width="stretch",
            hide_index=True,
            column_config={
                "PHOTO": st.column_config.ImageColumn("Photo", width="small"),
                "PLAYER_NAME": "Player",
                "GP": st.column_config.NumberColumn("GP", format="%d"),
                "MIN": st.column_config.NumberColumn("MIN", format="%.1f"),
                "PTS": st.column_config.NumberColumn("PTS", format="%.1f"),
                "REB": st.column_config.NumberColumn("REB", format="%.1f"),
                "AST": st.column_config.NumberColumn("AST", format="%.1f"),
                "STL": st.column_config.NumberColumn("STL", format="%.1f"),
                "BLK": st.column_config.NumberColumn("BLK", format="%.1f"),
                "FG_PCT": st.column_config.NumberColumn("FG%", format="%.1f%%"),
                "FG3_PCT": st.column_config.NumberColumn("3P%", format="%.1f%%"),
                "TS_PCT": st.column_config.NumberColumn("TS%", format="%.1f%%"),
                "NET_RATING": st.column_config.NumberColumn("Net rating", format="%+.1f"),
            },
        )


with games_tab:
    st.subheader("Every game")
    st.markdown(
        '<p class="section-note">Use the search and column controls to inspect individual results.</p>',
        unsafe_allow_html=True,
    )
    game_table = games[
        ["GAME_DATE", "MATCHUP", "WL", "PTS", "PLUS_MINUS"]
    ].copy()
    game_table["GAME_DATE"] = game_table["GAME_DATE"].dt.strftime("%b %d, %Y")
    game_table["RESULT"] = game_table.apply(
        lambda row: f"{row['WL']} ({row['PLUS_MINUS']:+.0f})", axis=1
    )
    game_table = game_table[
        ["GAME_DATE", "MATCHUP", "RESULT", "PTS", "PLUS_MINUS"]
    ].iloc[::-1]

    st.dataframe(
        game_table,
        width="stretch",
        hide_index=True,
        column_config={
            "GAME_DATE": "Date",
            "MATCHUP": "Matchup",
            "RESULT": "Result",
            "PTS": st.column_config.NumberColumn("Knicks points", format="%d"),
            "PLUS_MINUS": st.column_config.NumberColumn("Margin", format="%+d"),
        },
    )

st.markdown(
    f"""
    <div class="source-note">
      Data source: NBA.com · {data_status} · Refreshed {fetched_at.strftime('%b %d, %Y at %I:%M %p')} ·
      Regular season only. Ratings are points per 100 possessions.
    </div>
    """,
    unsafe_allow_html=True,
)
