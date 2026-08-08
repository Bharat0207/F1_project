import pandas as pd


def get_race_summary(session):

    results = session.results

    winner = results.iloc[0]
    p2 = results.iloc[1]
    p3 = results.iloc[2]

    laps = session.laps

    total_drivers = len(results)

    classified = len(
        results[
            results["Status"].str.contains(
                "Finished",
                na=False
            )
        ]
    )

    dnfs = total_drivers - classified

    total_laps = int(
        laps["LapNumber"].max()
    )

    return {

        "winner": winner,

        "p2": p2,

        "p3": p3,

        "total_drivers": total_drivers,

        "classified": classified,

        "dnfs": dnfs,

        "total_laps": total_laps
    }