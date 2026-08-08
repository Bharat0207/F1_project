from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests

DRIVER_COLORS = {
    "VER": "#3671C6", "PER": "#3671C6",
    "HAM": "#27F4D2", "RUS": "#27F4D2",
    "LEC": "#E8002D", "SAI": "#E8002D",
    "NOR": "#FF8000", "PIA": "#FF8000",
    "ALO": "#229971", "STR": "#229971",
    "GAS": "#0093CC", "OCO": "#0093CC",
    "TSU": "#6692FF", "LAW": "#6692FF",
    "ALB": "#64C4FF", "COL": "#64C4FF",
    "MAG": "#B6BABD", "HUL": "#B6BABD",
    "BOT": "#52E252", "ZHO": "#52E252"
}


@st.cache_data(ttl=3600)
def fetch_schedule_for_year(year):
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
def fetch_round_drivers(year, round_number):
    drivers_map = {}
    url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/results.json"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            races = resp.json()["MRData"]["RaceTable"]["Races"]
            if races and "Results" in races[0]:
                for res in races[0]["Results"]:
                    d_num = res.get("number") or res["Driver"].get("permanentNumber")
                    d_code = res["Driver"].get("code") or res["Driver"].get("familyName", "")[:3].upper()
                    d_name = f"{res['Driver']['givenName']} {res['Driver']['familyName']}"
                    if d_num:
                        drivers_map[f"{d_code} ({d_name})"] = str(d_num)
    except Exception:
        pass

    if not drivers_map:
        drivers_map = {
            "NOR (Lando Norris)": "4", "VER (Max Verstappen)": "1",
            "HAM (Lewis Hamilton)": "44", "LEC (Charles Leclerc)": "16",
            "PIA (Oscar Piastri)": "81", "RUS (George Russell)": "63"
        }
    return drivers_map


def compute_distance_and_telemetry(df):
    """Calculates cumulative track distance (meters) from speed and time."""
    df = df.sort_values(by="date_dt").copy()
    df["dt"] = df["date_dt"].diff().dt.total_seconds().fillna(0.0)
    df["speed_ms"] = df["speed"] / 3.6
    df["distance_delta"] = df["speed_ms"] * df["dt"]
    df["Distance"] = df["distance_delta"].cumsum()
    df["LapTimeSec"] = (df["date_dt"] - df["date_dt"].min()).dt.total_seconds()
    return df


@st.cache_data(ttl=3600)
def fetch_telemetry_comparison(year, location_name, d1_number, d2_number):
    telemetry_data = {}

    try:
        sess_url = f"https://api.openf1.org/v1/sessions?year={year}&session_name=Qualifying"
        sess_res = requests.get(sess_url, timeout=6)

        session_key = None
        if sess_res.status_code == 200 and sess_res.json():
            for s in sess_res.json():
                loc = str(s.get("location", "")).lower()
                cntry = str(s.get("country_name", "")).lower()
                target_loc = location_name.lower()
                if target_loc in loc or loc in target_loc or target_loc in cntry:
                    session_key = s.get("session_key")
                    break

        if not session_key:
            race_sess_url = f"https://api.openf1.org/v1/sessions?year={year}&session_name=Race"
            race_res = requests.get(race_sess_url, timeout=6)
            if race_res.status_code == 200 and race_res.json():
                for s in race_res.json():
                    loc = str(s.get("location", "")).lower()
                    cntry = str(s.get("country_name", "")).lower()
                    target_loc = location_name.lower()
                    if target_loc in loc or loc in target_loc or target_loc in cntry:
                        session_key = s.get("session_key")
                        break

        if session_key:
            for d_num in [d1_number, d2_number]:
                laps_url = f"https://api.openf1.org/v1/laps?session_key={session_key}&driver_number={d_num}"
                laps_res = requests.get(laps_url, timeout=6)

                if laps_res.status_code == 200 and laps_res.json():
                    df_laps = pd.DataFrame(laps_res.json())
                    valid_laps = df_laps[
                        (df_laps["lap_duration"].notna()) &
                        (df_laps["is_pit_out_lap"] == False) &
                        (df_laps["lap_duration"] > 50)
                    ]

                    if not valid_laps.empty:
                        best_lap = valid_laps.loc[valid_laps["lap_duration"].idxmin()]
                        lap_num = best_lap["lap_number"]
                        lap_time_sec = float(best_lap["lap_duration"])
                        dt_start = pd.to_datetime(best_lap["date_start"])
                        dt_end = dt_start + timedelta(seconds=lap_time_sec)

                        iso_start = dt_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                        iso_end = dt_end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

                        # 1. Fetch Car Telemetry (Speed, Throttle, Brake, Gear)
                        car_url = f"https://api.openf1.org/v1/car_data?session_key={session_key}&driver_number={d_num}&date>={iso_start}&date<={iso_end}"
                        car_res = requests.get(car_url, timeout=8)

                        # 2. Fetch Spatial Location Telemetry (X, Y Coordinates)
                        loc_url = f"https://api.openf1.org/v1/location?session_key={session_key}&driver_number={d_num}&date>={iso_start}&date<={iso_end}"
                        loc_res = requests.get(loc_url, timeout=8)

                        if car_res.status_code == 200 and car_res.json():
                            df_car = pd.DataFrame(car_res.json())
                            df_car["date_dt"] = pd.to_datetime(df_car["date"])
                            df_car = compute_distance_and_telemetry(df_car)

                            # Merge Spatial (X, Y) telemetry onto timestamp grid
                            if loc_res.status_code == 200 and loc_res.json():
                                df_loc = pd.DataFrame(loc_res.json())
                                if not df_loc.empty and "x" in df_loc.columns and "y" in df_loc.columns:
                                    df_loc["date_dt"] = pd.to_datetime(df_loc["date"])
                                    df_car = pd.merge_asof(
                                        df_car.sort_values("date_dt"),
                                        df_loc[["date_dt", "x", "y"]].sort_values("date_dt"),
                                        on="date_dt",
                                        direction="nearest"
                                    )

                            telemetry_data[str(d_num)] = {
                                "LapNumber": lap_num,
                                "LapTimeSec": lap_time_sec,
                                "Telemetry": df_car
                            }
    except Exception:
        pass

    return telemetry_data


def render_2d_track_map(df, driver_code):
    """Generates an interactive 2D spatial track map colored by speed."""
    if "x" not in df.columns or "y" not in df.columns or df["x"].isna().all():
        st.info(f"Spatial GPS telemetry unavailable for {driver_code}.")
        return

    valid_geo = df.dropna(subset=["x", "y", "speed"]).copy()

    fig_map = px.scatter(
        valid_geo,
        x="x",
        y="y",
        color="speed",
        color_continuous_scale="Turbo",
        labels={"x": "X (Meters)", "y": "Y (Meters)", "speed": "Speed (km/h)"},
        title=f"2D Track Speed Profile: {driver_code}",
        template="plotly_dark",
        hover_data={"x": False, "y": False, "speed": ":.0f km/h", "Distance": ":.0f m"}
    )

    fig_map.update_traces(marker=dict(size=5, opacity=0.9))
    fig_map.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="", scaleanchor="x", scaleratio=1),
        coloraxis_colorbar=dict(title="km/h", len=0.8)
    )

    st.plotly_chart(fig_map, width="stretch")


def show_telemetry():
    st.header("Intuitive Lap Telemetry & Track Spatial Map")
    st.caption("Track-aligned distance channels, continuous time delta, and interactive 2D track speed profiles.")

    current_year = datetime.now().year

    col_season, col_race = st.columns([1, 2])

    with col_season:
        selected_year = st.selectbox("Select Season:", options=list(range(current_year, 2022, -1)), index=0)

    schedule_df = fetch_schedule_for_year(selected_year)
    if schedule_df.empty:
        st.warning(f"No schedule data available for the {selected_year} season.")
        return

    race_options = {
        f"Round {row['RoundNumber']}: {row['EventName']} ({row['Location']})": (row["RoundNumber"], row["Location"])
        for _, row in schedule_df.iterrows()
    }

    with col_race:
        selected_label = st.selectbox("Select Grand Prix:", list(race_options.keys()))

    selected_round, location_name = race_options[selected_label]
    st.markdown("---")

    driver_catalog = fetch_round_drivers(selected_year, selected_round)
    driver_labels = list(driver_catalog.keys())

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        d1_label = st.selectbox("Driver 1 (Baseline):", driver_labels, index=0)
        d1_num = driver_catalog[d1_label]
        d1_code = d1_label[:3]

    with col_d2:
        default_idx = 1 if len(driver_labels) > 1 else 0
        d2_label = st.selectbox("Driver 2 (Comparison):", driver_labels, index=default_idx)
        d2_num = driver_catalog[d2_label]
        d2_code = d2_label[:3]

    if d1_num == d2_num:
        st.warning("Please select two distinct drivers.")
        return

    st.markdown("---")

    with st.spinner(f"Processing telemetry & 2D track maps for {d1_code} vs {d2_code}..."):
        tele_map = fetch_telemetry_comparison(selected_year, location_name, d1_num, d2_num)

    if not tele_map or str(d1_num) not in tele_map or str(d2_num) not in tele_map:
        st.info(f"Telemetry for {selected_year} {location_name} is unavailable. Select a completed round from 2023–2025.")
        return

    d1_data = tele_map[str(d1_num)]
    d2_data = tele_map[str(d2_num)]

    df1 = d1_data["Telemetry"]
    df2 = d2_data["Telemetry"]

    # Key Performance Metrics Banner
    top_speed_d1, top_speed_d2 = df1["speed"].max(), df2["speed"].max()
    min_speed_d1, min_speed_d2 = df1["speed"].min(), df2["speed"].min()

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(f"{d1_code} Best Lap", f"{d1_data['LapTimeSec']:.3f} s")
    with col_m2:
        st.metric(f"{d2_code} Best Lap", f"{d2_data['LapTimeSec']:.3f} s")
    with col_m3:
        st.metric(f"{d1_code} Speed Range", f"{min_speed_d1:.0f} - {top_speed_d1:.0f} km/h")
    with col_m4:
        st.metric(f"{d2_code} Speed Range", f"{min_speed_d2:.0f} - {top_speed_d2:.0f} km/h")

    st.markdown("---")

    # Interactive 2D Track Speed Maps Side-by-Side
    st.markdown("### Interactive 2D Circuit Speed Profiles")
    st.caption("Visualizes speed distribution across track cornering apexes and straights.")

    map_col1, map_col2 = st.columns(2)
    with map_col1:
        render_2d_track_map(df1, d1_code)

    with map_col2:
        render_2d_track_map(df2, d2_code)

    st.markdown("---")

    # Standardize Distance Grid for Time Delta Calculation
    max_dist = min(df1["Distance"].max(), df2["Distance"].max())
    dist_grid = np.linspace(0, max_dist, 500)

    t1_interp = np.interp(dist_grid, df1["Distance"], df1["LapTimeSec"])
    t2_interp = np.interp(dist_grid, df2["Distance"], df2["LapTimeSec"])
    time_delta = t1_interp - t2_interp

    # Multi-Trace Telemetry Channels
    fig_tele = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=(
            "Speed Trace (km/h)",
            f"Time Delta: {d1_code} relative to {d2_code} (seconds)",
            "Throttle (%) & Brake Application",
            "Gear Selection"
        )
    )

    c1 = DRIVER_COLORS.get(d1_code, "#00CC96")
    c2 = DRIVER_COLORS.get(d2_code, "#EF553B")

    # 1. Distance-Aligned Speed Trace
    fig_tele.add_trace(go.Scatter(x=df1["Distance"], y=df1["speed"], mode="lines", name=d1_code, line=dict(color=c1, width=2)), row=1, col=1)
    fig_tele.add_trace(go.Scatter(x=df2["Distance"], y=df2["speed"], mode="lines", name=d2_code, line=dict(color=c2, width=2)), row=1, col=1)

    # 2. Continuous Time Delta Curve
    fig_tele.add_trace(go.Scatter(
        x=dist_grid, y=time_delta, mode="lines",
        name=f"Delta ({d1_code} - {d2_code})",
        line=dict(color="#FFD700", width=2),
        hovertemplate="Distance: %{x:.0f}m<br>Delta: %{y:+.3f}s"
    ), row=2, col=1)

    # 3. Throttle & Brake
    fig_tele.add_trace(go.Scatter(x=df1["Distance"], y=df1["throttle"], mode="lines", name=f"{d1_code} Throttle", line=dict(color=c1, width=1.5), showlegend=False), row=3, col=1)
    fig_tele.add_trace(go.Scatter(x=df2["Distance"], y=df2["throttle"], mode="lines", name=f"{d2_code} Throttle", line=dict(color=c2, width=1.5), showlegend=False), row=3, col=1)
    fig_tele.add_trace(go.Scatter(x=df1["Distance"], y=df1["brake"] * 100, mode="lines", name=f"{d1_code} Brake", line=dict(color=c1, width=1, dash="dash"), showlegend=False), row=3, col=1)
    fig_tele.add_trace(go.Scatter(x=df2["Distance"], y=df2["brake"] * 100, mode="lines", name=f"{d2_code} Brake", line=dict(color=c2, width=1, dash="dash"), showlegend=False), row=3, col=1)

    # 4. Gear Usage
    fig_tele.add_trace(go.Scatter(x=df1["Distance"], y=df1["n_gear"], mode="lines", name=d1_code, line=dict(color=c1, width=1.5), showlegend=False), row=4, col=1)
    fig_tele.add_trace(go.Scatter(x=df2["Distance"], y=df2["n_gear"], mode="lines", name=d2_code, line=dict(color=c2, width=1.5), showlegend=False), row=4, col=1)

    fig_tele.update_layout(
        height=800,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig_tele.update_xaxes(title_text="Track Distance (meters)", row=4, col=1, showgrid=True, gridcolor="#222222")
    fig_tele.update_yaxes(showgrid=True, gridcolor="#222222")

    st.plotly_chart(fig_tele, width="stretch")