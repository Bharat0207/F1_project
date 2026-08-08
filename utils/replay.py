import pandas as pd


def get_replay_data(session, drivers, lap_number):

    all_data = []

    # -----------------------------------------
    # REFERENCE TRACK
    # -----------------------------------------

    ref_driver = drivers[0]

    ref_lap = (
        session.laps
        .pick_drivers(ref_driver)
        .pick_fastest()
    )

    ref_pos = ref_lap.get_pos_data()

    ref_pos = ref_pos[
        ["X", "Y"]
    ].reset_index(drop=True)

    # Optimization
    ref_pos = ref_pos.iloc[::10]

    track_points = len(ref_pos)

    # -----------------------------------------
    # DRIVER REPLAY DATA
    # -----------------------------------------

    for drv in drivers:

        try:

            lap = (
                session.laps
                .pick_drivers(drv)
                .pick_laps(lap_number)
            )

            if lap.empty:
                continue

            lap = lap.iloc[0]

            lap_time = lap["LapTime"]

            if pd.isna(lap_time):
                continue

            lap_seconds = lap_time.total_seconds()

            for i in range(track_points):

                progress = i / track_points

                x = ref_pos.iloc[i]["X"]
                y = ref_pos.iloc[i]["Y"]

                frame = int(progress * lap_seconds)

                all_data.append({

                    "Driver": drv,
                    "X": x,
                    "Y": y,
                    "Frame": frame
                })

        except:
            continue

    return pd.DataFrame(all_data)