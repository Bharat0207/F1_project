from datetime import datetime
import pandas as pd
import requests


def get_current_season():
    """Dynamically returns the current calendar year."""
    return datetime.now().year


def fetch_live_schedule(year):
    """Fetches the official schedule for any given year from the Jolpica/Ergast API."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            races = response.json()["MRData"]["RaceTable"]["Races"]

            parsed = []
            for r in races:
                date_str = f"{r['date']} {r.get('time', '13:00:00Z')}"
                parsed.append({
                    "RoundNumber": int(r["round"]),
                    "EventName": r["raceName"],
                    "Country": r["Circuit"]["Location"]["country"],
                    "Location": r["Circuit"]["Location"]["locality"],
                    "Session5Date": pd.to_datetime(date_str, utc=True, errors="coerce")
                })
            return pd.DataFrame(parsed)
    except Exception:
        pass

    return pd.DataFrame()


def fetch_live_standings(year):
    """Fetches official live driver standings for any year."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}/driverStandings.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            lists = response.json()["MRData"]["StandingsTable"]["StandingsLists"]
            if lists:
                driver_standings = lists[0]["DriverStandings"]
                parsed = []
                for item in driver_standings:
                    driver_name = f"{item['Driver']['givenName']} {item['Driver']['familyName']}"
                    team_name = item["Constructors"][0]["name"] if item["Constructors"] else "N/A"
                    points = float(item["points"])

                    parsed.append({
                        "Driver": driver_name,
                        "Team": team_name,
                        "Points": points
                    })
                return pd.DataFrame(parsed)
    except Exception:
        pass

    return pd.DataFrame()


def get_home_data(year=None):
    """Perpetual home data loader."""
    if year is None:
        year = get_current_season()

    schedule = fetch_live_schedule(year)

    # Fallback to previous year if the current year schedule isn't published yet
    if schedule.empty:
        schedule = fetch_live_schedule(year - 1)

    now_utc = pd.Timestamp.now(tz="UTC")
    future = schedule[schedule["Session5Date"] > now_utc] if ("Session5Date" in schedule.columns and not schedule.empty) else pd.DataFrame()

    if not future.empty:
        next_race = future.iloc[0]
    elif not schedule.empty:
        next_race = schedule.iloc[-1]
    else:
        next_race = pd.Series({
            "RoundNumber": 1,
            "EventName": "Season Opener",
            "Country": "TBD",
            "Location": "TBD",
            "Session5Date": pd.Timestamp.now(tz="UTC")
        })

    standings = fetch_live_standings(year)
    # If early season and 0 points are recorded yet, show prior season final standings
    if standings.empty:
        standings = fetch_live_standings(year - 1)

    leader = standings.iloc[0] if not standings.empty else None

    return {
        "race": next_race,
        "leader": leader,
        "standings": standings
    }