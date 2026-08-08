import streamlit as st
import pandas as pd
from components.hero import hero
from components.standings import driver_standings
from utils.home_data import get_home_data
from utils.asset_manager import (
    get_circuit_image,
    get_team_car
)

def show_home(year=None):
    data = get_home_data(year)
    race = data["race"]
    leader = data["leader"]
    standings = data["standings"]

    # Safe timezone conversion for countdown
    session_date = race.get("Session5Date") if hasattr(race, "get") else getattr(race, "Session5Date", None)
    if pd.notna(session_date):
        race_time = pd.to_datetime(session_date, utc=True)
        now_utc = pd.Timestamp.now(tz="UTC")
        countdown = race_time - now_utc
    else:
        countdown = pd.Timedelta(0)

    leader_team = leader["Team"] if leader is not None and "Team" in leader else None

    hero(
        race,
        get_circuit_image(race.get("Country", "")),
        get_team_car(leader_team) if leader_team else None,
        countdown
    )

    driver_standings(standings)