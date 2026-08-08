import fastf1

fastf1.Cache.enable_cache('data/')

def get_race_schedule(year):
    schedule = fastf1.get_event_schedule(year)

    # Keep only actual races (not testing)
    schedule = schedule[schedule['EventFormat'] != 'testing']

    return schedule[['EventName', 'RoundNumber']]