from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import requests


def parse_time_to_seconds(time_str):
    """Converts time string ('M:SS.sss' or 'SS.sss') into seconds."""
    if not time_str or str(time_str).upper() in ["N/A", "NONE", "", "NAN"]:
        return None
    try:
        if ":" in str(time_str):
            parts = str(time_str).split(":")
            return float(parts[0]) * 60.0 + float(parts[1])
        return float(time_str)
    except Exception:
        return None


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
                    "Location": r["Circuit"]["Location"]["locality"],
                    "CircuitName": r["Circuit"]["circuitName"]
                })
            return pd.DataFrame(parsed)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_session_data(year, round_number, endpoint_type):
    """Generic fetcher for Qualifying, Sprint, or Race results."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/{endpoint_type}.json"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            races = resp.json()["MRData"]["RaceTable"]["Races"]
            if races:
                return races[0]
    except Exception:
        pass
    return {}


def show_analytics():
    st.header("Weekend Analytics")
    st.caption("Detailed breakdown of session results, lap deltas, position changes, and teammate battles.")

    current_year = datetime.now().year

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

    # Multi-Session Navigation Tabs
    tab_quali, tab_sprint, tab_race, tab_h2h = st.tabs([
        "Qualifying Breakdown",
        "Sprint Session",
        "Race Pace & Overtakes",
        "Teammate H2H Matrix"
    ])

    # TAB 1: QUALIFYING BREAKDOWN
    with tab_quali:
        q_data = fetch_session_data(selected_year, selected_round, "qualifying")

        if q_data and "QualifyingResults" in q_data:
            q_results = q_data["QualifyingResults"]
            parsed_q = []

            for item in q_results:
                d_code = item["Driver"].get("code") or item["Driver"].get("familyName", "")[:3].upper()
                d_name = f"{item['Driver']['givenName']} {item['Driver']['familyName']}"
                team = item["Constructor"]["name"] if "Constructor" in item else "N/A"
                best_q = item.get("Q3") or item.get("Q2") or item.get("Q1") or "N/A"
                sec_val = parse_time_to_seconds(best_q)

                parsed_q.append({
                    "Pos": int(item.get("position", 99)),
                    "Code": d_code,
                    "Driver": d_name,
                    "Team": team,
                    "Q1": item.get("Q1", "N/A"),
                    "Q2": item.get("Q2", "N/A"),
                    "Q3": item.get("Q3", "N/A"),
                    "BestTime": best_q,
                    "Sec": sec_val
                })

            df_q = pd.DataFrame(parsed_q).sort_values(by="Pos")

            if not df_q.empty and df_q["Sec"].notna().any():
                pole_sec = df_q["Sec"].min()
                df_q["DeltaToPole"] = df_q["Sec"].apply(lambda x: round(x - pole_sec, 3) if pd.notna(x) else None)
                df_q["QualiLabel"] = "P" + df_q["Pos"].astype(str) + ": " + df_q["Code"]

                st.markdown("### Qualifying Session Deltas")
                
                valid_q_df = df_q.dropna(subset=["DeltaToPole"]).copy()
                quali_order = valid_q_df["QualiLabel"].tolist()

                fig_q = px.bar(
                    valid_q_df,
                    x="QualiLabel",
                    y="DeltaToPole",
                    color="Team",
                    text_auto="+.3f",
                    labels={"QualiLabel": "Quali Position & Driver", "DeltaToPole": "Gap to Pole (s)", "Team": "Constructor"},
                    template="plotly_dark",
                    category_orders={"QualiLabel": quali_order}
                )
                fig_q.update_layout(
                    height=380,
                    margin=dict(l=20, r=20, t=30, b=20),
                    xaxis=dict(tickangle=-45, categoryorder="array", categoryarray=quali_order),
                    yaxis=dict(title="Gap to Pole (seconds)", showgrid=True, gridcolor="#333333")
                )
                st.plotly_chart(fig_q, width="stretch")

            st.dataframe(df_q[["Pos", "Code", "Driver", "Team", "Q1", "Q2", "Q3", "BestTime"]], width="stretch", hide_index=True)
        else:
            st.info("Qualifying data for this round is unavailable or not yet published.")

    # TAB 2: SPRINT SESSION
    with tab_sprint:
        s_data = fetch_session_data(selected_year, selected_round, "sprint")

        if s_data and "SprintResults" in s_data:
            s_results = s_data["SprintResults"]
            parsed_s = []

            for item in s_results:
                d_code = item["Driver"].get("code") or item["Driver"].get("familyName", "")[:3].upper()
                d_name = f"{item['Driver']['givenName']} {item['Driver']['familyName']}"
                team = item["Constructor"]["name"] if "Constructor" in item else "N/A"
                grid = int(item.get("grid", 0))
                finish = int(item.get("position", 0))

                parsed_s.append({
                    "Finish": finish,
                    "Grid": grid,
                    "Change": grid - finish if grid > 0 else 0,
                    "Code": d_code,
                    "Driver": d_name,
                    "Team": team,
                    "Points": float(item.get("points", 0)),
                    "Status": item.get("status", "Finished")
                })

            df_s = pd.DataFrame(parsed_s).sort_values(by="Finish")

            st.markdown("### Sprint Race Classification")
            st.dataframe(df_s[["Finish", "Grid", "Code", "Driver", "Team", "Points", "Status"]], width="stretch", hide_index=True)
        else:
            st.info("This Grand Prix round did not include a Sprint format.")

    # TAB 3: RACE PACE & OVERTAKES
    with tab_race:
        r_data = fetch_session_data(selected_year, selected_round, "results")

        if r_data and "Results" in r_data:
            r_results = r_data["Results"]
            parsed_r = []

            for item in r_results:
                d_code = item["Driver"].get("code") or item["Driver"].get("familyName", "")[:3].upper()
                d_name = f"{item['Driver']['givenName']} {item['Driver']['familyName']}"
                team = item["Constructor"]["name"] if "Constructor" in item else "N/A"
                grid = int(item.get("grid", 0))
                finish = int(item.get("position", 0))

                parsed_r.append({
                    "Finish": finish,
                    "Grid": grid,
                    "PositionsGained": (grid - finish) if (grid > 0 and finish > 0) else 0,
                    "Code": d_code,
                    "Driver": d_name,
                    "Team": team,
                    "Points": float(item.get("points", 0)),
                    "Status": item.get("status", "Finished")
                })

            df_r = pd.DataFrame(parsed_r).sort_values(by="Finish")

            st.markdown("### Race Grid Positions Gained / Lost")
            df_r["Color"] = df_r["PositionsGained"].apply(lambda x: "Gained" if x > 0 else ("Lost" if x < 0 else "Same"))

            fig_r = px.bar(
                df_r,
                x="Code",
                y="PositionsGained",
                color="Color",
                color_discrete_map={"Gained": "#39B54A", "Lost": "#FF1801", "Same": "#717171"},
                text_auto=True,
                labels={"Code": "Driver", "PositionsGained": "Net Change"},
                template="plotly_dark"
            )
            fig_r.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_r, width="stretch")
        else:
            st.info("Race results data unavailable.")

    # TAB 4: TEAMMATE HEAD-TO-HEAD MATRIX
    with tab_h2h:
        q_data_h2h = fetch_session_data(selected_year, selected_round, "qualifying")

        if q_data_h2h and "QualifyingResults" in q_data_h2h:
            q_res = q_data_h2h["QualifyingResults"]
            df_h2h_q = pd.DataFrame([
                {
                    "Code": item["Driver"].get("code") or item["Driver"].get("familyName", "")[:3].upper(),
                    "Driver": f"{item['Driver']['givenName']} {item['Driver']['familyName']}",
                    "Team": item["Constructor"]["name"],
                    "QPos": int(item.get("position", 99)),
                    "BestTime": item.get("Q3") or item.get("Q2") or item.get("Q1") or "N/A",
                    "Sec": parse_time_to_seconds(item.get("Q3") or item.get("Q2") or item.get("Q1"))
                }
                for item in q_res
            ])

            teams_list = sorted(list(df_h2h_q["Team"].unique()))
            selected_h2h_team = st.selectbox("Select Constructor to Inspect Teammate Duel:", teams_list, index=0)

            team_drivers = df_h2h_q[df_h2h_q["Team"] == selected_h2h_team].sort_values(by="QPos")

            if len(team_drivers) >= 2:
                d1 = team_drivers.iloc[0]
                d2 = team_drivers.iloc[1]

                delta_sec = abs(d1["Sec"] - d2["Sec"]) if (pd.notna(d1["Sec"]) and pd.notna(d2["Sec"])) else None
                delta_str = f"{delta_sec:.3f} s" if delta_sec is not None else "N/A"

                st.markdown(f"### {selected_h2h_team} Teammate Battle")
                col_d1, col_d2 = st.columns(2)

                with col_d1:
                    st.metric("Qualifying Winner", d1["Driver"], f"P{d1['QPos']} ({d1['BestTime']})")

                with col_d2:
                    st.metric("Qualifying Gap", delta_str, f"P{d2['QPos']} ({d2['BestTime']})")