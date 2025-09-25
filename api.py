import requests
import re
import json
import asyncio
import aiohttp

# TODO
# remake each function to be async



CONFIG_FILE = 'data/config.json'
STATS_FILE = 'data/stats.json'
HEROS_FILE = 'data/heros.json'

with open(CONFIG_FILE, 'r') as file:
    config = json.load(file)

with open(HEROS_FILE, 'r', encoding="utf-8") as file:
    heros = json.load(file)

HEROS = {hero["id"]: hero["name"] for hero in heros}

STEAM_API_KEY = config.get('STEAM_API_KEY')

# Steam API Interactions

def resolve_steam_id(input_value: str) -> str:
    """
    Resolve a Steam username, profile URL, or ID into a Steam64 ID.
    """

    # Already a Steam64 ID
    if input_value.isdigit() and len(input_value) == 17:
        return input_value

    # Profile URL case
    if "steamcommunity.com" in input_value:
        vanity_match = re.search(r"/id/([^/]+)/?", input_value)
        numeric_match = re.search(r"/profiles/(\d+)/?", input_value)

        if numeric_match:
            return numeric_match.group(1)

        elif vanity_match:
            vanity_name = vanity_match.group(1)
            url = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={STEAM_API_KEY}&vanityurl={vanity_name}"

            response = requests.get(url, timeout=10)
            data = response.json()

            if data["response"]["success"] == 1:
                return data["response"]["steamid"]
            else:
                raise ValueError(f"Could not resolve vanity URL: {vanity_name}")

    # Plain vanity name
    url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={STEAM_API_KEY}&vanityurl={input_value}"

    response = requests.get(url, timeout=10)
    data = response.json()

    if data["response"]["success"] == 1:
        return data["response"]["steamid"]

    raise ValueError(f"Could not resolve Steam ID: {input_value}")


def steam64_to_steamid3(steam64: str) -> str:
    steam64_int = int(steam64)
    account_id = steam64_int - 76561197960265728
    return f"{account_id}"

# Deadlock API Interaction

async def get_deadlock_hero_stats(input_value: str):

    steam64 = resolve_steam_id(input_value)
    steamid3 = steam64_to_steamid3(steam64)
    async with aiohttp.ClientSession() as session:
        url = f"https://api.deadlock-api.com/v1/players/hero-stats?account_ids={steamid3}"
        async with session.get(url) as response:
            data = await response.json()

    return data

# print (resolve_steam_id("https://steamcommunity.com/id/435345325"))
# print(steam64_to_steamid3(resolve_steam_id("https://steamcommunity.com/id/435345325")))
# print(get_deadlock_hero_stats("https://steamcommunity.com/id/435345325"))
# print(HEROS)

with open('data/test-stats.json', 'r', encoding="utf-8") as file:
    test = json.load(file)

# shouldnt need this to be async

def get_most_played_heros(input_value):

    lst = []

    for hero in input_value:
        hero_name = HEROS.get(hero['hero_id'], "Unknown Hero")
        matches = hero.get('matches_played', 0)
        lst.append((hero_name, matches, hero['hero_id']))
    
    return sorted(lst, key=lambda x: x[1], reverse=True)


# print(get_most_played_heros(test))

# just calcs no need to async 

def get_hero_stats(input_value, hero_id):
    for hero in input_value:
        if hero['hero_id'] == hero_id:
            return hero
    return None

# print(get_hero_stats(test, get_most_played_heros(test)[0][2]))


# def get_hero_rank(hero_id: int, steamid3: str):
#     """
#     Fetch the MMR/rank for a specific hero for a given SteamID3.
#     Returns a dictionary with rank info.
#     """
#     url = f"https://api.deadlock-api.com/v1/players/mmr/{hero_id}?account_ids={steamid3}"
#     print(url)
#     resp = requests.get(url, timeout=10)
#     if resp.status_code != 200:
#         raise ValueError(f"Failed to fetch rank for hero {hero_id}")
#     data = resp.json()

#     if not data:
#         return None

#     return data[0]

async def get_hero_rank(hero_id: int, steamid3: str):
    """
    Fetch the MMR/rank for a specific hero for a given SteamID3.
    Returns a dictionary with rank info.
    """
    async with aiohttp.ClientSession() as session:
        url = f"https://api.deadlock-api.com/v1/players/mmr/{hero_id}?account_ids={steamid3}"
        async with session.get(url) as response:
            data = await response.json()
    if not data:
        return None

    return data[0]


# print(get_hero_rank(get_most_played_heros(test)[0][2], steam64_to_steamid3(resolve_steam_id("https://steamcommunity.com/id/435345325"))))




# Testing

async def testing():
    stats = await get_deadlock_hero_stats("https://steamcommunity.com/id/435345325")
    ret = await get_hero_rank(get_most_played_heros(stats)[0][2], steam64_to_steamid3(resolve_steam_id("https://steamcommunity.com/id/435345325")))
    return ret

def test_manual_async_function():
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(testing())
    loop.close()
    print(result)

test_manual_async_function()
