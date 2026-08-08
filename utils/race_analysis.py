import fastf1
import pandas as pd

fastf1.Cache.enable_cache('data/')


def load_race_session(year, round_number):
    session = fastf1.get_session(year, round_number, 'R')
    session.load()
    return session


def get_lap_times(session):
    laps = session.laps

    df = laps[['Driver', 'LapTime']].dropna()

    df['LapTime (s)'] = df['LapTime'].dt.total_seconds()

    return df


def get_fastest_laps(session):
    laps = session.laps.pick_quicklaps()

    fastest = laps.groupby('Driver')['LapTime'].min().reset_index()
    fastest['LapTime (s)'] = fastest['LapTime'].dt.total_seconds()

    fastest = fastest.sort_values('LapTime (s)')

    return fastest


def compare_drivers(session, driver1, driver2):
    laps = session.laps

    d1 = laps.pick_drivers(driver1)[['LapNumber', 'LapTime']].dropna()
    d2 = laps.pick_drivers(driver2)[['LapNumber', 'LapTime']].dropna()

    d1['LapTime'] = d1['LapTime'].dt.total_seconds()
    d2['LapTime'] = d2['LapTime'].dt.total_seconds()

    d1['Driver'] = driver1
    d2['Driver'] = driver2

    return pd.concat([d1, d2])