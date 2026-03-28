import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime, timezone
import pytz

DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://localhost:8000")
LOCAL_TZ = pytz.timezone("Europe/Zurich")


def fetch_matches_with_odds() -> list[dict]:
    response = requests.get(f"{DB_SERVICE_URL}/matches/with_odds/")
    response.raise_for_status()
    return response.json()


def compute_margin(bookmaker_odds: dict) -> float:
    best_team1 = max(v["team1_odds"] for v in bookmaker_odds.values())
    best_draw = max(v["draw_odds"] for v in bookmaker_odds.values() if v["draw_odds"])
    best_team2 = max(v["team2_odds"] for v in bookmaker_odds.values())
    return 1/best_team1 + 1/best_draw + 1/best_team2


def fmt_datetime(dt_str: str, include_time: bool = True) -> str:
    dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
    return dt.strftime("%a %d %b %Y, %H:%M") if include_time else dt.strftime("%a %d %b %Y")


def fmt_timestamp(dt_str: str) -> str:
    dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
    return dt.strftime("%H:%M %d/%m/%y")


def render_matches():
    st.title("🇨🇭 Swiss Sports Bet Dashboard")
    st.markdown("---")
    st.markdown("Made by [Remi Tregan](https://github.com/tremgan) · [GitHub](https://github.com/tremgan/sports-bet)")

    data = fetch_matches_with_odds()

    if not data:
        st.info("No matches with odds from multiple bookmakers found.")
        return

    data.sort(key=lambda item: compute_margin(item["bookmaker_odds"]))

    for item in data:
        match = item["match"]
        bookmaker_odds = item["bookmaker_odds"]

        margin = compute_margin(bookmaker_odds)
        has_arb = margin < 1.0
        margin_pct = (margin - 1) * 100

        label = f"{'🟢' if has_arb else '🔴'} {match['match_label']} (margin: {margin_pct:.2f}%)"

        with st.expander(label):
            st.markdown(f"**{fmt_datetime(match['match_datetime'])}**")

            odds_df = pd.DataFrame(bookmaker_odds).T
            odds_df.index.name = "Bookmaker"
            odds_df["timestamp"] = odds_df["timestamp"].apply(fmt_timestamp)
            st.markdown("#### All bookmaker odds")
            st.dataframe(odds_df, use_container_width=True)

            best_odds = {
                "team1": max(bookmaker_odds.values(), key=lambda v: v["team1_odds"]),
                "draw": max((v for v in bookmaker_odds.values() if v["draw_odds"]), key=lambda v: v["draw_odds"]),
                "team2": max(bookmaker_odds.values(), key=lambda v: v["team2_odds"]),
            }
            st.markdown("#### Best odds")
            best_df = pd.DataFrame({
                "Outcome": ["Team 1", "Draw", "Team 2"],
                "Best Odds": [best_odds["team1"]["team1_odds"], best_odds["draw"]["draw_odds"], best_odds["team2"]["team2_odds"]],
            })
            st.dataframe(best_df, use_container_width=True)

            if has_arb:
                profit = (1 / margin - 1) * 100
                st.success(f"Arbitrage opportunity! Profit: {profit:.2f}%")


render_matches()