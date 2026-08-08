import pandas as pd


def get_tyre_strategy(session):

    laps = session.laps.copy()

    # -----------------------------------------
    # GET FINISHING ORDER
    # -----------------------------------------

    results = session.results

    finishing_order = results["Abbreviation"].tolist()

    # -----------------------------------------
    # FILTER REQUIRED DATA
    # -----------------------------------------

    strategy = laps[[
        "Driver",
        "LapNumber",
        "Compound",
        "Stint"
    ]].dropna()

    # -----------------------------------------
    # GROUP TYRE STINTS
    # -----------------------------------------

    strategy = strategy.groupby(
        ["Driver", "Stint", "Compound"]
    ).agg({

        "LapNumber": ["min", "max"]

    }).reset_index()

    strategy.columns = [
        "Driver",
        "Stint",
        "Compound",
        "LapStart",
        "LapEnd"
    ]

    strategy["StintLength"] = (
        strategy["LapEnd"] -
        strategy["LapStart"] + 1
    )

    

    # -----------------------------------------
    # DRIVER ORDER
    # -----------------------------------------

    strategy["Driver"] = pd.Categorical(
        strategy["Driver"],
        categories=finishing_order[::-1],
        ordered=True
    )

    strategy = strategy.sort_values(
        "Driver"
    )

    return strategy

# ===================================================
# POSITION CHANGES
# ===================================================

def get_position_changes(session):

    laps = session.laps.copy()

    position_df = laps[[
        "Driver",
        "LapNumber",
        "Position"
    ]].dropna()

    return position_df

# ===================================================
# GAP TO LEADER
# ===================================================

def get_gap_to_leader(session):

    laps = session.laps.copy()

    laps = laps[[
        "Driver",
        "LapNumber",
        "Position",
        "Time"
    ]].dropna()

    # Convert time to seconds
    laps["TimeSeconds"] = laps["Time"].dt.total_seconds()

    gap_data = []

    for lap in laps["LapNumber"].unique():

        lap_df = laps[
            laps["LapNumber"] == lap
        ].copy()

        # Leader time
        leader_time = lap_df["TimeSeconds"].min()

        lap_df["GapToLeader"] = (
            lap_df["TimeSeconds"] - leader_time
        )

        gap_data.append(lap_df)

    gap_df = pd.concat(gap_data)

    return gap_df