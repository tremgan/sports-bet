import streamlit as st
import requests
import pandas as pd

from config import DB_SERVICE_URL

st.set_page_config(page_title="Sports Betting Odds", layout="wide")
st.title("Latest Scraped Odds")


@st.cache_data(ttl=30)
def fetch_matches_with_odds():
    response = requests.get(f"{DB_SERVICE_URL}/matches/with_odds/")
    return response.json()


data = fetch_matches_with_odds()

if not data:
    st.info("No paired matches yet.")
else:
    rows = []
    for item in data:
        match = item["match"]
        for bookmaker, odds in item["bookmaker_odds"].items():
            rows.append(
                {
                    "match": match["match_label"],
                    "datetime": match["match_datetime"],
                    "bookmaker": bookmaker,
                    "team1_odds": odds["team1_odds"],
                    "draw_odds": odds.get("draw_odds"),
                    "team2_odds": odds["team2_odds"],
                    "scraped_at": odds["timestamp"],
                }
            )

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d %H:%M")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"]).dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(df, use_container_width=True)

if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()
