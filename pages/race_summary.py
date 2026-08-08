from datetime import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


def parse_time_to_seconds(time_str: str) -> float | None:
    """Parses lap time strings (e.g. '1:18.518') to total seconds."""
    if not time_str or time_str in ["-", "N/A", ""]:
        return None
    try:
        if ":" in time_str:
            m, s = time_str.split(":")
            return float(m) * 60.0 + float(s)
        return float(time_str)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def fetch_season_schedule(year: int):
    """Fetches full race calendar for a selected season."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}.json"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            return res.json()["MRData"]["RaceTable"]["Races"]
    except Exception:
        pass
    return []


@st.cache_data(ttl=1800)
def fetch_race_results(year: int, round_num: int):
    """Fetches race classification details."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_num}/results.json"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            race_table = res.json()["MRData"]["RaceTable"]["Races"]
            if race_table:
                return race_table[0]
    except Exception:
        pass
    return None


@st.cache_data(ttl=1800)
def fetch_qualifying_results(year: int, round_num: int):
    """Fetches qualifying classification."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_num}/qualifying.json"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            race_table = res.json()["MRData"]["RaceTable"]["Races"]
            if race_table and "QualifyingResults" in race_table[0]:
                return race_table[0]["QualifyingResults"]
    except Exception:
        pass
    return []


@st.cache_data(ttl=1800)
def fetch_sprint_results(year: int, round_num: int):
    """Fetches sprint race classification if applicable."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_num}/sprint.json"
    try:
        res = requests.get(url, timeout=6)
        if res.status_code == 200:
            race_table = res.json()["MRData"]["RaceTable"]["Races"]
            if race_table and "SprintResults" in race_table[0]:
                return race_table[0]["SprintResults"]
    except Exception:
        pass
    return []


def show_race_summary():
    st.markdown("<h1 style='text-transform: uppercase;'>RACE SUMMARY & ANALYTICS</h1>", unsafe_allow_html=True)

    col_yr, col_rd = st.columns([1, 2])
    current_year = datetime.now().year

    with col_yr:
        selected_year = st.selectbox("Season:", options=list(range(current_year, 2011, -1)), index=0)

    schedule = fetch_season_schedule(selected_year)
    if not schedule:
        st.warning(f"No schedule data available for {selected_year}.")
        return

    race_options = {f"Round {r['round']}: {r['raceName']}": int(r['round']) for r in schedule}

    with col_rd:
        selected_race_name = st.selectbox("Select Grand Prix:", options=list(race_options.keys()))
        selected_round = race_options[selected_race_name]

    race_data = fetch_race_results(selected_year, selected_round)
    sprint_data = fetch_sprint_results(selected_year, selected_round)
    quali_data = fetch_qualifying_results(selected_year, selected_round)

    # Reordered tabs: Race & Analytics first, Weekend Overview removed
    tab_race_analytics, tab_quali, tab_sprint = st.tabs([
        "Race & Analytics",
        "Qualifying",
        "Sprint"
    ])

    # 1. RACE RESULTS & ANALYTICS
    with tab_race_analytics:
        st.subheader("Race Classification & Performance Analytics")

        if race_data and "Results" in race_data:
            res_list = []
            for item in race_data["Results"]:
                grid_pos = int(item.get("grid", 0)) if str(item.get("grid", "")).isdigit() else 0
                finish_pos = int(item.get("position", 0)) if str(item.get("position", "")).isdigit() else 0
                pos_change = grid_pos - finish_pos if (grid_pos > 0 and finish_pos > 0) else 0

                res_list.append({
                    "Pos": finish_pos if finish_pos > 0 else item.get("position", "-"),
                    "Grid": grid_pos if grid_pos > 0 else item.get("grid", "-"),
                    "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
                    "DriverCode": item['Driver'].get("code") or item['Driver']['familyName'][:3].upper(),
                    "DriverId": item['Driver']['driverId'],
                    "Team": item['Constructor']['name'],
                    "Status": item.get("status"),
                    "Points": float(item.get("points", 0)),
                    "Pos Change": f"+{pos_change}" if pos_change > 0 else (str(pos_change) if pos_change < 0 else "0")
                })

            df_res = pd.DataFrame(res_list)

            st.dataframe(
                df_res[["Pos", "Grid", "Driver", "Team", "Status", "Points", "Pos Change"]],
                use_container_width=True
            )

            # Qualifying Delta to Pole
            st.markdown("### Qualifying Delta to Pole (Ordered by Race Finish)")
            st.caption("Drivers ordered strictly from P1 to last finisher based on their race result.")

            if quali_data:
                quali_times = {}
                all_times = []

                for q_item in quali_data:
                    d_id = q_item['Driver']['driverId']
                    q3 = parse_time_to_seconds(q_item.get("Q3"))
                    q2 = parse_time_to_seconds(q_item.get("Q2"))
                    q1 = parse_time_to_seconds(q_item.get("Q1"))

                    valid_times = [t for t in [q3, q2, q1] if t is not None]
                    if valid_times:
                        best_t = min(valid_times)
                        quali_times[d_id] = best_t
                        all_times.append(best_t)

                pole_time = min(all_times) if all_times else None

                if pole_time is not None:
                    delta_list = []
                    for row in res_list:
                        d_id = row["DriverId"]
                        if d_id in quali_times:
                            delta = round(quali_times[d_id] - pole_time, 3)
                            x_label = f"P{row['Pos']}: {row['DriverCode']}"
                            delta_list.append({
                                "Race Finish & Driver": x_label,
                                "Quali Delta to Pole (seconds)": delta,
                                "Constructor": row["Team"],
                                "Driver": row["Driver"]
                            })

                    if delta_list:
                        df_delta = pd.DataFrame(delta_list)

                        fig_delta = px.bar(
                            df_delta,
                            x="Race Finish & Driver",
                            y="Quali Delta to Pole (seconds)",
                            color="Constructor",
                            text="Quali Delta to Pole (seconds)",
                            hover_data=["Driver", "Constructor"]
                        )

                        fig_delta.update_traces(texttemplate='%{text:.3f}', textposition='outside')
                        fig_delta.update_layout(
                            xaxis_title="Race Finish & Driver",
                            yaxis_title="Quali Delta to Pole (seconds)",
                            yaxis=dict(zeroline=True),
                            height=500
                        )

                        st.plotly_chart(fig_delta, use_container_width=True)
                    else:
                        st.info("Unable to match qualifying times for race finishers.")
                else:
                    st.info("Qualifying timing data unavailable for delta calculation.")
            else:
                st.info("Qualifying data unavailable for this event.")
        else:
            st.info("Race classification and analytics data not available.")

    # 2. QUALIFYING (No / jersey number column removed)
    with tab_quali:
        st.subheader("Qualifying Results")
        if quali_data:
            q_list = []
            for item in quali_data:
                q_list.append({
                    "Pos": item.get("position"),
                    "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
                    "Team": item['Constructor']['name'],
                    "Q1": item.get("Q1", "-"),
                    "Q2": item.get("Q2", "-"),
                    "Q3": item.get("Q3", "-")
                })
            st.dataframe(pd.DataFrame(q_list), use_container_width=True)
        else:
            st.info("Qualifying data not yet available for this event.")

    # 3. SPRINT
    with tab_sprint:
        st.subheader("Sprint Race Results")
        if sprint_data:
            sp_list = []
            for item in sprint_data:
                sp_list.append({
                    "Pos": item.get("position"),
                    "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
                    "Team": item['Constructor']['name'],
                    "Grid": item.get("grid"),
                    "Status": item.get("status"),
                    "Points": item.get("points")
                })
            st.dataframe(pd.DataFrame(sp_list), use_container_width=True)
        else:
            st.info("This event is not a Sprint weekend or Sprint data is unavailable.")