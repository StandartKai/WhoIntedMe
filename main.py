import urllib.parse, urllib.request
import json
import pickledb
import datetime


API_PREFIX = 'https://europe.api.riotgames.com'
API_KEY = 'RGAPI-ddf8f7a7-a03c-4fe4-8571-1b87ebfc1e94'
PUUID = '3_CLT0-vX-ldcPn9bcXjBvk6yU15l7izQtMID03SuKxznRlJ1r-xcleRmPlNlY1D48PiTbHw3qJJjg'


def get_puuid_from_name(name, api_key=API_KEY):
    name = name.replace(' ', '%20')

    parameters = dict()
    parameters['api_key'] = api_key

    url_values = urllib.parse.urlencode(parameters)
    url = f'https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}'
    full_url = url + '?' + url_values
    with urllib.request.urlopen(full_url) as response:
        response = response.read().decode('utf-8')

    return json.loads(response)['puuid']


def get_name_from_puuid(puuid, api_key=API_KEY):
    parameters = dict()
    parameters['api_key'] = api_key

    url_values = urllib.parse.urlencode(parameters)

    url = f'{API_PREFIX}/riot/account/v1/accounts/by-puuid/{puuid}'
    full_url = url + '?' + url_values
    with urllib.request.urlopen(full_url) as response:
        response = response.read().decode('utf-8')

    return json.loads(response)['gameName']


def get_recent_matches(api_key=API_KEY, start=0, count=20):
    parameters = dict()
    parameters['api_key'] = api_key
    parameters['start'] = start
    parameters['count'] = count

    url_values = urllib.parse.urlencode(parameters)

    url = f'{API_PREFIX}/lol/match/v5/matches/by-puuid/{PUUID}/ids'
    full_url = url + '?' + url_values
    with urllib.request.urlopen(full_url) as response:
       response = response.read().decode('utf-8')

    return json.loads(response)


def get_match_dict_from_id(match_id, api_key=API_KEY):
    # Get matches from matches id
    url = f'{API_PREFIX}/lol/match/v5/matches/{match_id}'

    parameters = dict()
    parameters['api_key'] = api_key

    url_values = urllib.parse.urlencode(parameters)
    full_url = url + '?' + url_values

    with urllib.request.urlopen(full_url) as response:
        response = response.read().decode('utf-8')
    return json.loads(response)


def update_database(db, start=0, count=20):
    recent_match_ids = get_recent_matches(start=start, count=count)

    # iterate over all recent match ids
    for match_id in recent_match_ids:
        # if a match is already in the database, skip it
        # else, add it to the database as a key only
        if match_id in db.lgetall('matches'):
            continue
        db.ladd('matches', match_id)

        match_dict = get_match_dict_from_id(match_id)

        # found out if I was in the winning or losing team
        i_won = None

        game_mode = match_dict['info']['gameMode']
        date = match_dict['info']['gameStartTimestamp']

        for participant in match_dict['info']['participants']:
            if participant['puuid'] == PUUID:
                i_won = participant['win']

        # iterate over participants of the game
        for participant in match_dict['info']['participants']:

            puuid = participant['puuid']
            # skip if it's me
            if puuid == PUUID:
                continue

            # find out if participant is in my or enemy team
            participant['ally'] = participant['win'] == i_won
            participant['game_mode'] = game_mode
            participant['date'] = date

            # check if the puuid is is in the participants dict keys
            if not db.dexists('participants', puuid):
                db.dadd('participants', (puuid, list()))

            entry_list = db.dget('participants', puuid)
            entry_list.append(participant)
            db.dadd('participants', (puuid, entry_list))

    db.dump()


def print_participant_info(participant):
    pass


def init_database():
    db = pickledb.load('database.db', False)
    db.lcreate('matches')
    db.dcreate('participants')

    db.dump()


# init_database()

# print(get_puuid_from_name('Sick Ranchez'))

db = pickledb.load('database.db', False)
# update_database(db, start=0, count=200)

for puuid in db.dkeys('participants'):
    games_list = db.dget('participants', puuid)
    games_together = len(games_list)
    if games_together > 1:
        print(f'Played {games_together} games with {get_name_from_puuid(puuid)}.')
        for game in games_list:
            team_status = 'Ally' if game['ally'] else 'Enemy'
            date = datetime.datetime.fromtimestamp(game['date']/1000.0)
            victory_status = 'won' if game['win'] else 'lost'
            print(f"- {team_status} {game['championName']}: {game['kills']}/{game['deaths']}/{game['assists']}, {victory_status} the game ({date.date()})")
