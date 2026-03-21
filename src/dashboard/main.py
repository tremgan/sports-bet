import streamlit as st
import requests
import pandas as pd

DB_SERVICE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Sports Betting Odds", layout="wide")
st.title("Latest Scraped Odds")

@st.cache_data(ttl=30)
def fetch_odds():
    response = requests.get(f"{DB_SERVICE_URL}/sports_betting_odds/")
    return response.json()

odds = fetch_odds()

if not odds:
    st.info("No odds scraped yet.")
else:
    df = pd.DataFrame(odds[-50:])
    df = df[["timestamp", "bookmaker", "team1_odds", "draw_odds", "team2_odds"]]
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(df, use_container_width=True)

if st.button("Refresh"):
    st.cache_data.clear()
    st.rerun()