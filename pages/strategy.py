from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

TYRE_COLORS = {
    "Soft": "#FF1801",
    "Medium": "#FFF200",
    "Hard": "#FFFFFF",
    "Intermediate": "#39B54A",
    "Wet": "#00AEEF",
    "Unknown": "#717171"
}


def normalize_compound(raw_comp):
    """Standardizes API compound strings into clean Pirelli labels."""
    if not raw_comp or str(raw_comp).upper() in ["NAN", "NONE", "UNKNOWN", "N/A", ""]:
        return "Unknown"
    val = str(raw_comp).upper()
    if "SOFT" in val or "RED" in val:
        return "Soft"
    elif "MEDIUM" in val or "YELLOW" in val:
        return "Medium"
    elif "HARD" in val or "WHITE" in val:
        return "Hard"
    elif "INTER" in val or "GREEN" in val:
        return "Intermediate"
    elif "WET" in val or "BLUE" in val:
        return "Wet"
    return val.title()


@st.cache_data(ttl=3600)
def fetch_schedule_for_year(year):
    """Fetches race calendar dynamically from Jolpica API."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}.json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            races = response.json()["MRData"]["RaceTable"]["Races"]
            parsed = []
            for r in races:
                parsed.append({
                    "RoundNumber": int(r["round"]),
                    "EventName": r["raceName"],
                    "Location": r["Circuit"]["Location"]["locality"]
                })
            return pd.DataFrame(parsed)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_strategy_data(year, round_number):
    """
    Fetches pit stop data from Jolpica API and tyre compound stints from OpenF1 REST API.
    Maps driver race numbers and permanent numbers for 100% accurate tyre compound matching.
    """
    driver_map = {}
    driver_number_map = {}
    driver_order = []

    # 1. Fetch Jolpica Results for Driver Metadata & Race Numbers
    results_url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/results.json"
    try:
        res_resp = requests.get(results_url, timeout=5)
        if res_resp.status_code == 200:
            races = res_resp.json()["MRData"]["RaceTable"]["Races"]
            if races and "Results" in races[0]:
                for item in races[0]["Results"]:
                    d_id = item["Driver"]["driverId"]
                    d_name = f"{item['Driver']['givenName']} {item['Driver']['familyName']}"
                    code = item["Driver"].get("code") or item["Driver"].get("familyName", "")[:3].upper()
                    team = item["Constructor"]["name"] if "Constructor" in item else "N/A"

                    race_num = item.get("number")
                    perm_num = item["Driver"].get("permanentNumber")

                    primary_num = str(race_num or perm_num or "")

                    driver_info = {
                        "name": d_name,
                        "code": code,
                        "team": team,
                        "number": primary_num
                    }
                    driver_map[d_id] = driver_info
                    driver_order.append(code)

                    # Map BOTH race number and permanent number to eliminate N/A lookups
                    if race_num:
                        driver_number_map[str(race_num)] = driver_info
                    if perm_num:
                        driver_number_map[str(perm_num)] = driver_info
    except Exception:
        pass

    # 2. Fetch Jolpica Pit Stops
    jolpica_stops = []
    pit_url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/pitstops.json"
    try:
        pit_resp = requests.get(pit_url, timeout=5)
        if pit_resp.status_code == 200:
            races = pit_resp.json()["MRData"]["RaceTable"]["Races"]
            if races and "PitStops" in races[0]:
                raw_stops = races[0]["PitStops"]
                for stop in raw_stops:
                    d_id = stop["driverId"]
                    info = driver_map.get(d_id, {
                        "name": d_id,
                        "code": d_id[:3].upper(),
                        "team": "N/A",
                        "number": ""
                    })

                    try:
                        duration_sec = float(stop["duration"])
                    except ValueError:
                        duration_sec = None

                    jolpica_stops.append({
                        "Driver": info["name"],
                        "Code": info["code"],
                        "Number": info["number"],
                        "Team": info["team"],
                        "Stop": int(stop["stop"]),
                        "Lap": int(stop["lap"]),
                        "DurationSec": duration_sec,
                        "DurationStr": stop.get("duration", "N/A"),
                        "Compound": "N/A"
                    })
    except Exception:
        pass

    df_stops = pd.DataFrame(jolpica_stops)

    # 3. OpenF1 REST API Stint Fetching
    stint_num_map = {}
    stint_lap_map = {}
    stints_for_viz = []

    try:
        openf1_sess_url = f"https://api.openf1.org/v1/sessions?year={year}&session_name=Race"
        sess_res = requests.get(openf1_sess_url, timeout=5)
        if sess_res.status_code == 200:
            sessions = sess_res.json()
            # Sort sessions chronologically by date_start
            sessions_sorted = sorted(sessions, key=lambda x: x.get("date_start", ""))

            target_session_key = None
            if 0 <= int(round_number) - 1 < len(sessions_sorted):
                target_session_key = sessions_sorted[int(round_number) - 1].get("session_key")

            if target_session_key:
                stints_url = f"https://api.openf1.org/v1/stints?session_key={target_session_key}"
                stints_res = requests.get(stints_url, timeout=5)
                if stints_res.status_code == 200:
                    stints_data = stints_res.json()
                    for st_item in stints_data:
                        d_num = str(st_item.get("driver_number", ""))
                        comp = normalize_compound(st_item.get("compound", ""))
                        st_num = int(st_item.get("stint_number", 1))
                        lap_start = int(st_item.get("lap_start", 1))
                        lap_end = int(st_item.get("lap_end", 100))

                        if comp and comp != "Unknown":
                            # Primary mapping: (driver_number, stint_number) -> compound
                            stint_num_map[(d_num, st_num)] = comp

                            # Secondary mapping: (driver_number, lap_number) -> compound
                            for lap_idx in range(lap_start, lap_end + 1):
                                stint_lap_map[(d_num, lap_idx)] = comp

                            info = driver_number_map.get(d_num, {})
                            d_code = info.get("code", d_num)
                            d_name = info.get("name", d_code)

                            stints_for_viz.append({
                                "Driver": d_code,
                                "DriverName": d_name,
                                "Stint": st_num,
                                "Compound": comp,
                                "StartLap": lap_start,
                                "EndLap": lap_end,
                                "Laps": max(1, lap_end - lap_start + 1)
                            })
    except Exception:
        pass

    # 4. Map compounds fitted during/after pit stops
    if not df_stops.empty:
        compounds_list = []
        for _, row in df_stops.iterrows():
            num = str(row["Number"])
            stop_num = row["Stop"]
            lap = row["Lap"]

            # Priority 1: Match by Stint Number (Stop 1 = Stint 2 compound)
            comp = stint_num_map.get((num, stop_num + 1))

            # Priority 2: Match by Next Lap
            if not comp or comp == "Unknown":
                comp = stint_lap_map.get((num, lap + 1))

            # Priority 3: Match by Current Lap
            if not comp or comp == "Unknown":
                comp = stint_lap_map.get((num, lap))

            compounds_list.append(comp if comp else "N/A")

        df_stops["Compound"] = compounds_list

    return df_stops, pd.DataFrame(stints_for_viz), driver_order


def show_strategy():
    st.header("Tyre Strategy")
    st.caption("Analyze tyre compound choices, stint lengths, and pit stop performance.")

    current_year = datetime.now().year

    # Season and Grand Prix Selectors
    col_season, col_race = st.columns([1, 2])

    with col_season:
        selected_year = st.selectbox(
            "Select Season:",
            options=list(range(current_year, 2011, -1)),
            index=0
        )

    schedule_df = fetch_schedule_for_year(selected_year)

    if schedule_df.empty:
        st.warning(f"No schedule data available for the {selected_year} season.")
        return

    race_options = {
        f"Round {row['RoundNumber']}: {row['EventName']} ({row['Location']})": row["RoundNumber"]
        for _, row in schedule_df.iterrows()
    }

    with col_race:
        selected_label = st.selectbox("Select Grand Prix:", list(race_options.keys()))

    selected_round = race_options[selected_label]

    st.markdown("---")

    # Fetch Data
    with st.spinner(f"Loading tyre strategy data for {selected_year} {selected_label}..."):
        df_stops, df_stints, driver_order = fetch_strategy_data(selected_year, selected_round)

    if df_stops.empty and df_stints.empty:
        st.info("Pit stop and tyre data for this round is unavailable or official timing logs were not published.")
        return

    valid_durations = df_stops.dropna(subset=["DurationSec"]) if not df_stops.empty else pd.DataFrame()

    if not valid_durations.empty:
        fastest_stop_row = valid_durations.loc[valid_durations["DurationSec"].idxmin()]
        fastest_str = f"{fastest_stop_row['Driver']} ({fastest_stop_row['Team']})"
        fastest_val = f"{fastest_stop_row['DurationSec']:.2f} s"
        avg_duration_val = f"{valid_durations['DurationSec'].mean():.2f} s"
    else:
        fastest_str = "N/A"
        fastest_val = "N/A"
        avg_duration_val = "N/A"

    # Key Metrics
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Fastest Pit Stop", fastest_str, fastest_val)

    with col2:
        st.metric("Average Pit Stop Duration", avg_duration_val, "Stationary Time")

    st.markdown("---")

    # Interactive Stint Visualizer
    if not df_stints.empty:
        st.markdown("### Race Tyre Stint Visualizer")
        st.caption("Horizontal stint lengths per driver color-coded by compound.")

        drivers_in_stints = [d for d in driver_order if d in df_stints["Driver"].unique()]
        if not drivers_in_stints:
            drivers_in_stints = list(df_stints["Driver"].unique())

        fig_stints = go.Figure()

        for compound_name, color_hex in TYRE_COLORS.items():
            comp_df = df_stints[df_stints["Compound"] == compound_name]
            if not comp_df.empty:
                fig_stints.add_trace(go.Bar(
                    name=compound_name,
                    y=comp_df["Driver"],
                    x=comp_df["Laps"],
                    base=comp_df["StartLap"] - 1,
                    orientation="h",
                    marker=dict(color=color_hex, line=dict(color="#111111", width=1)),
                    text=comp_df["Laps"],
                    textposition="inside",
                    textfont=dict(color="black" if compound_name in ["Medium", "Hard"] else "white", size=10),
                    hoverinfo="text",
                    hovertext=[
                        f"<b>{row['DriverName']}</b><br>Stint {row['Stint']}: {row['Compound']}<br>Laps: {row['StartLap']} -> {row['EndLap']} ({row['Laps']} Laps)"
                        for _, row in comp_df.iterrows()
                    ]
                ))

        fig_stints.update_layout(
            barmode="overlay",
            height=max(400, len(drivers_in_stints) * 28),
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(title="Race Laps", showgrid=True, gridcolor="#333333"),
            yaxis=dict(title="Driver", categoryorder="array", categoryarray=list(reversed(drivers_in_stints))),
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_stints, width="stretch")

    # Team Pit Stop Efficiency Bar Chart
    if not valid_durations.empty:
        st.markdown("### Team Pit Stop Efficiency")

        team_stats = valid_durations.groupby("Team")["DurationSec"].agg(["mean", "count"]).reset_index()
        team_stats.columns = ["Team", "AvgDuration", "StopsCount"]
        team_stats = team_stats.sort_values(by="AvgDuration", ascending=True)

        fig_team = px.bar(
            team_stats,
            x="Team",
            y="AvgDuration",
            color="Team",
            text_auto=".2f",
            labels={"AvgDuration": "Avg Duration (seconds)", "Team": "Constructor"},
            template="plotly_dark"
        )

        fig_team.update_layout(
            height=360,
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig_team, width="stretch")

    # Official Pit Stop Log Dataframe
    if not df_stops.empty:
        st.markdown("### Official Pit Stop and Tyre Log")

        display_df = df_stops[["Stop", "Driver", "Team", "Lap", "Compound", "DurationStr"]].copy()
        display_df.columns = ["Stop", "Driver", "Team", "Lap", "Tyre Compound", "Duration (s)"]

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True
        )