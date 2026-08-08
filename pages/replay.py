from datetime import datetime, date
import os
import fastf1
import fastf1.events
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# Direct FastF1 to Jolpica backend endpoint
try:
    import fastf1.ergast
    fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
except Exception:
    pass

# Initialize local FastF1 cache directory
os.makedirs('cache', exist_ok=True)
try:
    fastf1.Cache.enable_cache('cache')
except Exception:
    pass


@st.cache_data(ttl=3600)
def fetch_season_schedule(year: int):
    """Fetches full race calendar directly from Jolpica API."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}.json"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            return res.json()["MRData"]["RaceTable"]["Races"]
    except Exception:
        pass
    return []


def patch_fastf1_schedule():
    """Patches FastF1's get_event_schedule to fall back to Jolpica API if FastF1 backends fail."""
    original_get_event_schedule = fastf1.events.get_event_schedule

    def fallback_get_event_schedule(year, include_testing=False, backend=None, force_ergast=False):
        try:
            return original_get_event_schedule(year, include_testing=include_testing, backend=backend, force_ergast=force_ergast)
        except Exception:
            races = fetch_season_schedule(year)
            schedule_data = []
            for r in races:
                rd = int(r.get('round', 1))
                r_name = r.get('raceName', f'Round {rd}')
                country = r.get('Circuit', {}).get('Location', {}).get('country', '')
                location = r.get('Circuit', {}).get('Location', {}).get('locality', '')
                date_str = r.get('date', '2024-01-01')
                event_dt = pd.to_datetime(date_str)

                schedule_data.append({
                    'RoundNumber': rd,
                    'Country': country,
                    'Location': location,
                    'OfficialEventName': r_name,
                    'EventName': r_name,
                    'EventDate': event_dt,
                    'EventFormat': 'conventional',
                    'Session1': 'Practice 1',
                    'Session1Date': event_dt,
                    'Session1DateUtc': event_dt,
                    'Session2': 'Practice 2',
                    'Session2Date': event_dt,
                    'Session2DateUtc': event_dt,
                    'Session3': 'Practice 3',
                    'Session3Date': event_dt,
                    'Session3DateUtc': event_dt,
                    'Session4': 'Qualifying',
                    'Session4Date': event_dt,
                    'Session4DateUtc': event_dt,
                    'Session5': 'Race',
                    'Session5Date': event_dt,
                    'Session5DateUtc': event_dt,
                    'F1ApiSupport': True
                })
            df = pd.DataFrame(schedule_data)
            return fastf1.events.EventSchedule(df, year=year)

    fastf1.events.get_event_schedule = fallback_get_event_schedule
    fastf1.get_event_schedule = fallback_get_event_schedule


# Apply schedule fallback patch
patch_fastf1_schedule()

TEAM_COLORS = {
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E8002D",
    "McLaren": "#FF8000",
    "Mercedes": "#27F4D2",
    "Aston Martin": "#229971",
    "Alpine": "#0093CC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "Racing Bulls": "#6692FF",
    "AlphaTauri": "#5E8FAA",
    "Haas F1 Team": "#B6BABD",
    "Kick Sauber": "#52E252",
    "Alfa Romeo": "#C92D4B",
    "Cadillac": "#FFD700",
    "Audi": "#00E5FF"
}


def get_team_color(team_name: str) -> str:
    """Returns matching HEX team color or fallback."""
    for k, v in TEAM_COLORS.items():
        if k.lower() in str(team_name).lower():
            return v
    return "#FFFFFF"


@st.cache_data(ttl=3600, show_spinner=False)
def load_full_replay_data(year: int, round_num: int, race_name: str, race_date_str: str, sample_rate_sec: int = 2):
    """Loads session telemetry with automated schedule fallback handling."""
    if race_date_str:
        try:
            r_date = datetime.strptime(race_date_str, "%Y-%m-%d").date()
            if r_date > date.today():
                raise ValueError(f"The {year} {race_name} is scheduled for {race_date_str} and has not taken place yet.")
        except ValueError as ve:
            if "has not taken place yet" in str(ve):
                raise ve
            pass

    session = None

    # Load session using round number or clean race name
    try:
        session = fastf1.get_session(int(year), int(round_num), 'R')
        session.load(laps=True, telemetry=True, weather=False, messages=False)
    except Exception:
        try:
            clean_name = race_name.replace("Grand Prix", "").strip()
            session = fastf1.get_session(int(year), clean_name, 'R')
            session.load(laps=True, telemetry=True, weather=False, messages=False)
        except Exception as e:
            raise ValueError(f"Telemetry unavailable for {year} {race_name}: {str(e)}")

    if session is None or session.laps.empty:
        raise ValueError("No lap timing or position telemetry recorded for this session.")

    # Extract circuit outline
    fastest_lap = session.laps.pick_fastest()
    circuit_tel = fastest_lap.get_telemetry()
    if circuit_tel.empty:
        raise ValueError("No circuit telemetry coordinates available.")

    track_x = circuit_tel['X'].tolist()
    track_y = circuit_tel['Y'].tolist()

    # Safety Car detection (Status code 4)
    sc_active_times = set()
    try:
        if hasattr(session, 'track_status') and not session.track_status.empty:
            sc_statuses = session.track_status[session.track_status['Status'].astype(str).str.contains('4')]
            for _, sc_row in sc_statuses.iterrows():
                start_sec = int(sc_row['Time'].total_seconds())
                for t in range(start_sec, start_sec + 120):
                    sc_active_times.add(t)
    except Exception:
        pass

    driver_frames = []

    for drv in session.drivers:
        try:
            drv_laps = session.laps.pick_driver(drv)
            if drv_laps.empty:
                continue

            drv_code = drv_laps['Driver'].iloc[0]
            team_name = drv_laps['Team'].iloc[0]
            color = get_team_color(team_name)

            tel = drv_laps.get_telemetry()
            if tel.empty:
                continue

            max_driver_time = int(tel['Time'].dt.total_seconds().max())

            tel['TimeSec'] = tel['Time'].dt.total_seconds().astype(int)
            grouped = tel.groupby(tel['TimeSec'] // sample_rate_sec).first().reset_index()

            for _, row in grouped.iterrows():
                t_sec = int(row['TimeSec'])
                drs_raw = str(row.get('DRS', '0'))
                drs_str = "ON" if drs_raw in ['10', '12', '14', '1'] else "OFF"
                compound_str = str(row.get('Compound', 'N/A'))
                lap_num = int(row.get('LapNumber', 1))

                status_str = "OK"
                if t_sec > (max_driver_time - 30) and max_driver_time < 5000:
                    status_str = "OUT"

                driver_frames.append({
                    'TimeSec': t_sec,
                    'Driver': drv_code,
                    'Team': team_name,
                    'Color': color,
                    'X': float(row['X']),
                    'Y': float(row['Y']),
                    'Speed': int(row.get('Speed', 0)),
                    'Gear': int(row.get('nGear', 0)),
                    'DRS': drs_str,
                    'Compound': compound_str,
                    'Distance': float(row.get('Distance', 0)),
                    'LapNumber': lap_num,
                    'Status': status_str
                })
        except Exception:
            continue

    df_all = pd.DataFrame(driver_frames)

    # Compute Safety Car positions (~500m ahead of leader)
    sc_frames = []
    if not df_all.empty:
        unique_times = sorted(df_all['TimeSec'].unique())
        for t in unique_times:
            if t in sc_active_times:
                t_df = df_all[df_all['TimeSec'] == t].sort_values(by="Distance", ascending=False)
                if not t_df.empty:
                    leader = t_df.iloc[0]
                    sc_frames.append({
                        'TimeSec': t,
                        'Driver': 'SC',
                        'Team': 'Safety Car',
                        'Color': '#FF9900',
                        'X': leader['X'] + 500.0,
                        'Y': leader['Y'] + 500.0,
                        'Speed': min(140, leader['Speed']),
                        'Gear': 3,
                        'DRS': 'OFF',
                        'Compound': 'N/A',
                        'Distance': leader['Distance'] + 500.0,
                        'LapNumber': leader['LapNumber'],
                        'Status': 'SC ACTIVE'
                    })

    if sc_frames:
        df_sc = pd.DataFrame(sc_frames)
        df_all = pd.concat([df_all, df_sc], ignore_index=True)

    return track_x, track_y, df_all


def show_replay():
    st.markdown("<h1 style='text-transform: uppercase;'>RACE REPLAY & INSIGHTS MENU</h1>", unsafe_allow_html=True)

    col_yr, col_rd, col_step = st.columns([1, 2, 1])
    current_year = datetime.now().year
    available_years = list(range(current_year, 2017, -1))

    with col_yr:
        default_idx = available_years.index(2024) if 2024 in available_years else 0
        selected_year = st.selectbox("Season:", options=available_years, index=default_idx)

    schedule = fetch_season_schedule(selected_year)
    if not schedule:
        st.warning(f"No schedule data available for {selected_year}.")
        return

    race_options = {
        f"Round {r['round']}: {r['raceName']}": (int(r['round']), r['raceName'], r.get('date', ''))
        for r in schedule
    }

    with col_rd:
        selected_race_label = st.selectbox("Select Grand Prix:", options=list(race_options.keys()))
        selected_round, selected_race_name, selected_race_date = race_options[selected_race_label]

    with col_step:
        sample_interval = st.selectbox("Playback Quality (Step Sec):", options=[1, 2, 5], index=1)

    if st.button("Load Race Replay Data", use_container_width=True):
        st.session_state.load_replay_trigger = True

    if st.session_state.get("load_replay_trigger", False):
        with st.spinner("Processing telemetry coordinates, Safety Car simulation, and leaderboards..."):
            try:
                track_x, track_y, df_replay = load_full_replay_data(
                    selected_year, selected_round, selected_race_name, selected_race_date, sample_interval
                )

                if df_replay.empty:
                    st.warning("No telemetry data recorded for this race.")
                    return

                col_map, col_leaderboard = st.columns([3, 1])
                unique_times = sorted(df_replay['TimeSec'].unique())

                with col_map:
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=track_x,
                        y=track_y,
                        mode='lines',
                        line=dict(color='#2A2D3A', width=8),
                        hoverinfo='none',
                        name='Circuit'
                    ))

                    frames = []
                    for t in unique_times:
                        t_df = df_replay[df_replay['TimeSec'] == t].sort_values(by="Distance", ascending=False)
                        custom_data = t_df[['Team', 'Speed', 'Gear', 'DRS', 'Compound', 'Status', 'LapNumber']].values
                        marker_sizes = [18 if drv == 'SC' else 13 for drv in t_df['Driver']]

                        frame_traces = [
                            go.Scatter(
                                x=track_x,
                                y=track_y,
                                mode='lines',
                                line=dict(color='#2A2D3A', width=8),
                                hoverinfo='none',
                                showlegend=False
                            ),
                            go.Scatter(
                                x=t_df['X'],
                                y=t_df['Y'],
                                mode='markers+text',
                                marker=dict(
                                    size=marker_sizes,
                                    color=t_df['Color'].tolist(),
                                    line=dict(width=1.5, color='#FFFFFF')
                                ),
                                text=t_df['Driver'],
                                textposition='top center',
                                textfont=dict(size=11, color='#FFFFFF'),
                                customdata=custom_data,
                                hovertemplate=(
                                    "<b>%{text}</b> (%{customdata[0]})<br>"
                                    "Status: %{customdata[5]} | Lap: %{customdata[6]}<br>"
                                    "Speed: %{customdata[1]} km/h<br>"
                                    "Gear: %{customdata[2]} | DRS: %{customdata[3]}<br>"
                                    "Tyre: %{customdata[4]}"
                                    "<extra></extra>"
                                ),
                                name='Drivers'
                            )
                        ]

                        time_str = str(pd.Timedelta(seconds=t)).split('.')[0]
                        frames.append(go.Frame(data=frame_traces, name=str(t), layout=dict(title=f"Race Time: {time_str}")))

                    first_df = df_replay[df_replay['TimeSec'] == unique_times[0]]
                    first_custom = first_df[['Team', 'Speed', 'Gear', 'DRS', 'Compound', 'Status', 'LapNumber']].values
                    first_sizes = [18 if drv == 'SC' else 13 for drv in first_df['Driver']]

                    fig.add_trace(go.Scatter(
                        x=first_df['X'],
                        y=first_df['Y'],
                        mode='markers+text',
                        marker=dict(
                            size=first_sizes,
                            color=first_df['Color'].tolist(),
                            line=dict(width=1.5, color='#FFFFFF')
                        ),
                        text=first_df['Driver'],
                        textposition='top center',
                        textfont=dict(size=11, color='#FFFFFF'),
                        customdata=first_custom,
                        hovertemplate=(
                            "<b>%{text}</b> (%{customdata[0]})<br>"
                            "Status: %{customdata[5]} | Lap: %{customdata[6]}<br>"
                            "Speed: %{customdata[1]} km/h<br>"
                            "Gear: %{customdata[2]} | DRS: %{customdata[3]}<br>"
                            "Tyre: %{customdata[4]}"
                            "<extra></extra>"
                        ),
                        name='Drivers'
                    ))

                    fig.update_layout(
                        xaxis=dict(visible=False),
                        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
                        paper_bgcolor='#0f1015',
                        plot_bgcolor='#0f1015',
                        height=620,
                        margin=dict(l=10, r=10, t=40, b=10),
                        updatemenus=[{
                            "type": "buttons",
                            "buttons": [
                                {
                                    "label": "Play",
                                    "method": "animate",
                                    "args": [None, {"frame": {"duration": 120, "redraw": True}, "fromcurrent": True}]
                                },
                                {
                                    "label": "Pause",
                                    "method": "animate",
                                    "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]
                                }
                            ],
                            "direction": "left",
                            "pad": {"r": 10, "t": 10},
                            "showactive": False,
                            "x": 0.1,
                            "xanchor": "right",
                            "y": 0,
                            "yanchor": "top"
                        }],
                        sliders=[{
                            "active": 0,
                            "yanchor": "top",
                            "xanchor": "left",
                            "currentvalue": {
                                "font": {"size": 15, "color": "#ffffff"},
                                "prefix": "Session Time: ",
                                "visible": True,
                                "xanchor": "right"
                            },
                            "transition": {"duration": 0},
                            "pad": {"b": 10, "t": 40},
                            "len": 0.9,
                            "x": 0.1,
                            "y": 0,
                            "steps": [
                                {
                                    "args": [[str(t)], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
                                    "label": str(pd.Timedelta(seconds=t)).split('.')[0],
                                    "method": "animate"
                                } for t in unique_times
                            ]
                        }]
                    )

                    fig.frames = frames
                    st.plotly_chart(fig, use_container_width=True)

                with col_leaderboard:
                    st.subheader("Live Leaderboard")
                    latest_t = unique_times[-1]
                    latest_df = df_replay[(df_replay['TimeSec'] == latest_t) & (df_replay['Driver'] != 'SC')].sort_values(
                        by="Distance", ascending=False
                    ).reset_index(drop=True)

                    latest_df['Pos'] = range(1, len(latest_df) + 1)

                    st.dataframe(
                        latest_df[['Pos', 'Driver', 'Team', 'Compound', 'Status']],
                        use_container_width=True,
                        hide_index=True
                    )

                    st.markdown("---")
                    st.subheader("Driver Insights")

                    driver_list = sorted(latest_df['Driver'].unique().tolist())
                    selected_focus = st.selectbox("Focus Driver:", options=driver_list)

                    drv_sample = latest_df[latest_df['Driver'] == selected_focus].iloc[0]

                    st.metric("Top Speed Recorded", f"{drv_sample['Speed']} km/h")
                    st.metric("Current Gear / DRS", f"G{drv_sample['Gear']} | DRS {drv_sample['DRS']}")
                    st.metric("Tyre Compound", f"{drv_sample['Compound']}")
                    st.metric("Status", f"{drv_sample['Status']}")

            except Exception as e:
                st.info(f"{str(e)}")