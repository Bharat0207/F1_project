import pandas as pd

def get_driver_track(session, driver_code):
    laps = session.laps.pick_drivers(driver_code)

    # Get fastest lap (cleaner data)
    lap = laps.pick_fastest()

    pos_data = lap.get_pos_data()

    df = pos_data[['X', 'Y']].copy()
    df['Driver'] = driver_code

    return df


def get_multiple_drivers_track(session, drivers):
    all_data = []

    for drv in drivers:
        try:
            df = get_driver_track(session, drv)
            all_data.append(df)
        except:
            continue

    return pd.concat(all_data)