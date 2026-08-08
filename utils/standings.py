import fastf1
import pandas as pd

# Enable cache (VERY IMPORTANT)
fastf1.Cache.enable_cache('data/')

def get_driver_standings(year):
    ergast = fastf1.ergast.Ergast()
    standings = ergast.get_driver_standings(season=year)

    data = standings.content[0]

    df = pd.DataFrame(data)[[
        'position', 'givenName', 'familyName',
        'constructorNames', 'points', 'wins'
    ]]

    df['Driver'] = df['givenName'] + ' ' + df['familyName']
    df['Team'] = df['constructorNames'].apply(lambda x: x[0])

    df = df[['position', 'Driver', 'Team', 'points', 'wins']]
    df.columns = ['Position', 'Driver', 'Team', 'Points', 'Wins']

    return df


def get_constructor_standings(year):
    ergast = fastf1.ergast.Ergast()
    standings = ergast.get_constructor_standings(season=year)

    data = standings.content[0]

    df = pd.DataFrame(data)[[
        'position', 'constructorName', 'points', 'wins'
    ]]

    df.columns = ['Position', 'Team', 'Points', 'Wins']

    return df