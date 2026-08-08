import pandas as pd


def get_race_results(session):

    results = session.results.copy()

    results_df = results[[
        "Position",
        "FullName",
        "TeamName",
        "Points",
        "Status"
    ]]

    results_df.columns = [
        "Position",
        "Driver",
        "Team",
        "Points",
        "Status"
    ]

    return results_df