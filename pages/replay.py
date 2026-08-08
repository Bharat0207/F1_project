from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
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
    "BOT": "#52E252", "ZHO": "#52E252",
    "BEA": "#E8002D", "ANT": "#27F4D2", "HAD": "#3671C6"
}

# Pre-defined F1 circuit geometry outlines
CIRCUIT_GEOMETRIES = {
    "melbourne": {
        "x": [0, 200, 400, 650, 800, 750, 600, 450, 300, 200, 100, -50, -180, -220, -180, -80, 0],
        "y": [0, 20, 60, 150, 300, 480, 580, 550, 450, 380, 310, 240, 150, 50, -20, -10, 0]
    },
    "monza": {
        "x": [0, 400, 800, 1200, 1220, 1180, 1100, 1000, 900, 850, 700, 500, 200, 50, 0, 0],
        "y": [0, 10, 20, 30, 150, 250, 260, 200, 220, 350, 380, 280, 270, 180, 100, 0]
    },
    "monaco": {
        "x": [0, 150, 220, 180, 120, 160, 250, 280, 240, 190, 110, 40, -20, -50, 0],
        "y": [0, 30, 120, 180, 160, 220, 210, 130, 80, 70, 90, 60, 30, -10, 0]
    },
    "silverstone": {
        "x": [0, 300, 500, 600, 550, 450, 480, 620, 700, 650, 500, 350, 200, 100, 0],
        "y": [0, 20, 80, 200, 320, 310, 420, 400, 280, 180, 150, 220, 200, 100, 0]
    },
    "spa": {
        "x": [0, 200, 350, 400, 300, 250, 320, 450, 500, 420, 280, 150, 50, -30, 0],
        "y": [0, 50, 180, 350, 420, 500, 580, 520, 380, 250, 220, 260, 180, 80, 0]
    }
}


def get_circuit_outline(location_name):
    """Generates a smooth circuit path geometry matching the event location."""
    key = location_name.lower().replace(" ", "_")
    for track_key, coords in CIRCUIT_GEOMETRIES.items():
        if track_key in key or key in track_key:
            t_orig = np.linspace(0, 1, len(coords["x"]))
            t_smooth = np.linspace(0, 1, 350)
            x_smooth = np.interp(t_smooth, t_orig, coords["x"])
            y_smooth = np.interp(t_smooth, t_orig, coords["y"])
            return pd.DataFrame({"x": x_smooth, "y": y_smooth})

    # Default F1 organic circuit shape fallback
    t = np.linspace(0, 2 * np.pi, 350)
    x = 800 * np.sin(t) + 300 * np.sin(2 * t) + 120 * np.cos(3 * t)
    y = 500 * np.cos(t) + 200 * np.cos(2 * t) - 100 * np.sin(3 * t)
    return pd.DataFrame({"x": x, "y": y})


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
def fetch_circuit_and_replay_data(year, location_name, round_number):
    track_df = pd.DataFrame()
    replay_frames = []

    # 1. Attempt to fetch recorded GPS coordinates from OpenF1
    try:
        sess_url = f"https://api.openf1.org/v1/sessions?year={year}&session_name=Race"
        sess_res = requests.get(sess_url, timeout=4)

        session_key = None
        if sess_res.status_code == 200 and sess_res.json():
            for s in sess_res.json():
                loc = str(s.get("location", "")).lower()
                cntry = str(s.get("country_name", "")).lower()
                target_loc = location_name.lower()
                if target_loc in loc or loc in target_loc or target_loc in cntry:
                    session_key = s.get("session_key")
                    break

        if session_key:
            loc_url = f"https://api.openf1.org/v1/location?session_key={session_key}"
            loc_res = requests.get(loc_url, timeout=5)
            if loc_res.status_code == 200 and loc_res.json():
                df_raw = pd.DataFrame(loc_res.json())
                if not df_raw.empty and "x" in df_raw.columns and "y" in df_raw.columns:
                    track_df = df_raw.dropna(subset=["x", "y"])[::4].copy()
    except Exception:
        pass

    # 2. Fallback to pre-built circuit geometry if API coordinates are unavailable
    if track_df.empty:
        track_df = get_circuit_outline(location_name)

    # 3. Fetch Lap-by-Lap driver standings to animate positions along the circuit
    try:
        laps_url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/laps.json?limit=2000"
        laps_res = requests.get(laps_url, timeout=8)

        if laps_res.status_code == 200:
            races = laps_res.json()["MRData"]["RaceTable"]["Races"]
            if races and "Laps" in races[0]:
                track_points = track_df[["x", "y"]].reset_index(drop=True)
                num_points = len(track_points)

                for lap_obj in races[0]["Laps"]:
                    lap_num = int(lap_obj["number"])
                    total_drivers = len(lap_obj["Timings"])

                    for timing in lap_obj["Timings"]:
                        d_code = timing["driverId"][:3].upper()
                        pos = int(timing["position"])

                        # Calculate relative track distance offset along circuit geometry
                        frac = (total_drivers - pos + 0.5) / total_drivers
                        point_idx = int(frac * (num_points - 1))
                        point_idx = max(0, min(num_points - 1, point_idx))

                        coords = track_points.iloc[point_idx]

                        replay_frames.append({
                            "Lap": lap_num,
                            "Code": d_code,
                            "Position": pos,
                            "x": coords["x"],
                            "y": coords["y"]
                        })
    except Exception:
        pass

    return track_df, pd.DataFrame(replay_frames)


def show_replay():
    st.header("Animated 2D Track Race Replay")
    st.caption("Press Play or scrub through laps to watch driver dots race along the circuit layout.")

    current_year = datetime.now().year

    col_season, col_race = st.columns([1, 2])

    with col_season:
        selected_year = st.selectbox("Select Season:", options=list(range(current_year, 2011, -1)), index=0)

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

    with st.spinner(f"Loading 2D circuit layout and race replay for {selected_year} {location_name}..."):
        track_df, replay_df = fetch_circuit_and_replay_data(selected_year, location_name, selected_round)

    if replay_df.empty:
        st.info("Lap replay telemetry for this round is currently unavailable.")
        return

    total_laps = int(replay_df["Lap"].max())

    st.markdown("### Circuit Spatial Playback")

    fig = go.Figure()

    # Draw Circuit Layout Path
    fig.add_trace(go.Scatter(
        x=track_df["x"],
        y=track_df["y"],
        mode="lines",
        line=dict(color="#555555", width=5),
        hoverinfo="skip",
        name="Circuit Layout"
    ))

    # Construct Animation Frames
    frames = []
    for lap_num in range(1, total_laps + 1):
        lap_data = replay_df[replay_df["Lap"] == lap_num]

        frame_traces = [
            go.Scatter(x=track_df["x"], y=track_df["y"], mode="lines", line=dict(color="#555555", width=5), hoverinfo="skip")
        ]

        for _, d_row in lap_data.iterrows():
            d_code = d_row["Code"]
            d_color = DRIVER_COLORS.get(d_code, "#00CC96")

            frame_traces.append(go.Scatter(
                x=[d_row["x"]],
                y=[d_row["y"]],
                mode="markers+text",
                marker=dict(size=14, color=d_color, line=dict(color="white", width=1.5)),
                text=f"P{d_row['Position']} {d_code}",
                textposition="top center",
                name=d_code,
                hoverinfo="text",
                hovertext=f"<b>{d_code}</b><br>Position: P{d_row['Position']}<br>Lap: {lap_num}"
            ))

        frames.append(go.Frame(data=frame_traces, name=str(lap_num)))

    # Initial frame setup (Lap 1)
    lap1_data = replay_df[replay_df["Lap"] == 1]
    for _, d_row in lap1_data.iterrows():
        d_code = d_row["Code"]
        d_color = DRIVER_COLORS.get(d_code, "#00CC96")

        fig.add_trace(go.Scatter(
            x=[d_row["x"]],
            y=[d_row["y"]],
            mode="markers+text",
            marker=dict(size=14, color=d_color, line=dict(color="white", width=1.5)),
            text=f"P{d_row['Position']} {d_code}",
            textposition="top center",
            name=d_code
        ))

    fig.update_layout(
        height=650,
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title="", scaleanchor="x", scaleratio=1),
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "y": -0.05,
            "x": 0.0,
            "xanchor": "left",
            "yanchor": "top",
            "buttons": [
                {
                    "label": "▶ Play Race",
                    "method": "animate",
                    "args": [None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True}]
                },
                {
                    "label": "❚❚ Pause",
                    "method": "animate",
                    "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]
                }
            ]
        }],
        sliders=[{
            "active": 0,
            "yanchor": "top",
            "xanchor": "left",
            "currentvalue": {"prefix": "Active Lap: ", "visible": True, "xanchor": "right"},
            "pad": {"b": 10, "t": 50},
            "len": 0.85,
            "x": 0.15,
            "y": -0.05,
            "steps": [
                {
                    "args": [[str(lap)], {"frame": {"duration": 250, "redraw": True}, "mode": "immediate"}],
                    "label": str(lap),
                    "method": "animate"
                }
                for lap in range(1, total_laps + 1)
            ]
        }]
    )

    fig.frames = frames

    st.plotly_chart(fig, width="stretch")