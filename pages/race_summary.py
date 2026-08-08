from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import requests


def parse_time_to_seconds(time_str):
    """Converts time string ('M:SS.sss' or 'SS.sss') into seconds."""
    if not time_str or time_str in ["N/A", "None", "", None]:
        return None
    try:
        if ":" in time_str:
            parts = time_str.split(":")
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
                    "Location": r["Circuit"]["Location"]["locality"]
                })
            return pd.DataFrame(parsed)
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def fetch_full_race_summary_data(year, round_number):
    """
    Fetches Race Results and Qualifying Data combined from Jolpica API.
    """
    quali_map = {}
    q_url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/qualifying.json"
    try:
        q_resp = requests.get(q_url, timeout=5)
        if q_resp.status_code == 200:
            races = q_resp.json()["MRData"]["RaceTable"]["Races"]
            if races and "QualifyingResults" in races[0]:
                for q_item in races[0]["QualifyingResults"]:
                    d_code = q_item["Driver"].get("code") or q_item["Driver"].get("familyName", "")[:3].upper()
                    best_q = q_item.get("Q3") or q_item.get("Q2") or q_item.get("Q1") or "N/A"
                    best_sec = parse_time_to_seconds(best_q)
                    q_pos = int(q_item.get("position", 99))

                    quali_map[d_code] = {
                        "QualiPos": q_pos,
                        "BestQualiTime": best_q,
                        "QualiSec": best_sec
                    }
    except Exception:
        pass

    results_records = []
    r_url = f"https://api.jolpi.ca/ergast/f1/{year}/{round_number}/results.json"
    try:
        r_resp = requests.get(r_url, timeout=5)
        if r_resp.status_code == 200:
            races = r_resp.json()["MRData"]["RaceTable"]["Races"]
            if races and "Results" in races[0]:
                for res in races[0]["Results"]:
                    d_code = res["Driver"].get("code") or res["Driver"].get("familyName", "")[:3].upper()
                    d_name = f"{res['Driver']['givenName']} {res['Driver']['familyName']}"
                    team = res["Constructor"]["name"] if "Constructor" in res else "N/A"

                    finish_pos = int(res.get("position", 99))
                    grid_pos = int(res.get("grid", 0))
                    points = float(res.get("points", 0))
                    status = res.get("status", "Finished")

                    time_info = res.get("Time", {}).get("time", status)

                    q_info = quali_map.get(d_code, {
                        "QualiPos": grid_pos,
                        "BestQualiTime": "N/A",
                        "QualiSec": None
                    })

                    results_records.append({
                        "Finish": finish_pos,
                        "Grid": grid_pos,
                        "Code": d_code,
                        "Driver": d_name,
                        "Team": team,
                        "Status": status,
                        "Points": points,
                        "RaceTime": time_info,
                        "QualiPos": q_info["QualiPos"],
                        "BestQualiTime": q_info["BestQualiTime"],
                        "QualiSec": q_info["QualiSec"]
                    })
    except Exception:
        pass

    df = pd.DataFrame(results_records)

    if not df.empty and "QualiSec" in df.columns:
        valid_q = df.dropna(subset=["QualiSec"])
        if not valid_q.empty:
            pole_sec = valid_q["QualiSec"].min()
            df["QualiDelta"] = df["QualiSec"].apply(lambda x: round(x - pole_sec, 3) if pd.notna(x) else None)
        else:
            df["QualiDelta"] = None
    else:
        df["QualiDelta"] = None

    return df


def show_race_summary():
    st.header("Grand Prix Race Summary")
    st.caption("Podium winners, complete session results, and qualifying delta ordered by race finish.")

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

    with st.spinner(f"Loading race summary for {selected_year} {selected_label}..."):
        df = fetch_full_race_summary_data(selected_year, selected_round)

    if df.empty:
        st.info("Race results for this round are currently unavailable.")
        return

    # 1. Podium Top 3 Metrics
    podium_df = df[df["Finish"] <= 3].sort_values("Finish")
    if not podium_df.empty:
        col_p1, col_p2, col_p3 = st.columns(3)

        p1 = podium_df[podium_df["Finish"] == 1]
        p2 = podium_df[podium_df["Finish"] == 2]
        p3 = podium_df[podium_df["Finish"] == 3]

        with col_p1:
            if not p1.empty:
                st.metric("Winner (P1)", f"{p1.iloc[0]['Driver']}", p1.iloc[0]['Team'])
        with col_p2:
            if not p2.empty:
                st.metric("Runner Up (P2)", f"{p2.iloc[0]['Driver']}", p2.iloc[0]['Team'])
        with col_p3:
            if not p3.empty:
                st.metric("Third Place (P3)", f"{p3.iloc[0]['Driver']}", p3.iloc[0]['Team'])

    st.markdown("---")

    # Sort strictly by numerical Finish Position (P1 to P22)
    df_race_order = df.sort_values(by="Finish", ascending=True).copy()
    df_race_order["FinishLabel"] = "P" + df_race_order["Finish"].astype(str) + ": " + df_race_order["Code"]

    # 2. Complete Session Results & Delta Log
    st.markdown("### Complete Session Results & Delta Log")

    display_df = df_race_order[[
        "Finish", "Grid", "Code", "Driver", "Team", "Status", "Points", "RaceTime", "BestQualiTime", "QualiDelta"
    ]].copy()

    display_df.columns = [
        "Finish Pos", "Grid Pos", "Code", "Driver", "Team", "Status", "Points", "Race Time / Margin", "Best Quali Time", "Quali Delta (s)"
    ]

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True
    )

    st.markdown("---")

    # 3. Qualifying Delta to Pole (Ordered strictly P1, P2, P3...)
    st.markdown("### Qualifying Delta to Pole (Ordered by Race Finish)")
    st.caption("Drivers ordered strictly from P1 to last finisher based on their race result.")

    valid_delta_df = df_race_order.dropna(subset=["QualiDelta"]).copy()

    if not valid_delta_df.empty:
        # Extract explicit list of labels in P1, P2, P3... order
        finish_order = valid_delta_df["FinishLabel"].tolist()

        fig_delta = px.bar(
            valid_delta_df,
            x="FinishLabel",
            y="QualiDelta",
            color="Team",
            text_auto="+.3f",
            labels={"FinishLabel": "Race Finish & Driver", "QualiDelta": "Delta to Pole (s)", "Team": "Constructor"},
            template="plotly_dark",
            category_orders={"FinishLabel": finish_order}
        )

        fig_delta.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(
                tickangle=-45,
                categoryorder="array",
                categoryarray=finish_order
            ),
            yaxis=dict(title="Quali Delta to Pole (seconds)", showgrid=True, gridcolor="#333333")
        )

        st.plotly_chart(fig_delta, width="stretch")