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

# async def testing():
#     stats = await get_deadlock_hero_stats("https://steamcommunity.com/id/435345325")
#     ret = await get_hero_rank(get_most_played_heros(stats)[0][2], steam64_to_steamid3(resolve_steam_id("https://steamcommunity.com/id/435345325")))
#     return ret

# def test_manual_async_function():
#     loop = asyncio.get_event_loop()
#     result = loop.run_until_complete(testing())
#     loop.close()
#     print(result)

# test_manual_async_function()

def calcPr(player_stats):
    """
    Calculate a player rating (PR) from a list of hero stats.

    Inputs:
      - player_stats: list of dicts (each dict is a hero stats entry like in data/test-stats.json)
      - Uses fields if present: matches_played, wins, kills_per_min, deaths_per_min,
        assists_per_min, networth_per_min, damage_per_min, obj_damage_per_min,
        accuracy, crit_shot_rate, ending_level, last_played

    Output: dict with:
      - overall_pr: float (aggregated rating)
      - heroes: list of per-hero breakdowns with hero_id, hero_name, score, weight, matches_played

    The implementation is intentionally simple and tweakable: a small set of weights
    are exposed in `params` and the function gives more influence to heroes with
    more matches and more recent play (exponential decay by `recency_half_days`).

    Edge cases handled: missing fields, zero-match heroes ignored for overall aggregation.
    """

    import math
    import time


    params = {
        "recency_half_days": 90.0,  
        "match_confidence_scale": 1.0,  
        "w_win": 2.0,
        "w_kills": 1.0,
        "w_assists": 0.8,
        "w_deaths": 1.0,  
        "w_networth": 1.0,
        "w_damage": 1.2,
        "w_obj": 0.9,
        "w_accuracy": 0.6,
        "w_crit": 0.4,
        "w_level": 0.3,
        # PR scaling
        "pr_per_tier": 100,
        "max_pr_tiers": 66,
    }

    MAX_PR = params["pr_per_tier"] * params["max_pr_tiers"]  # e.g. 100 * 66 = 6600 (cap at Eternus 6)

    now_ts = time.time()
    decay_seconds = params["recency_half_days"] * 24 * 3600

    # Helper to compute recency weight from last_played timestamp
    print('recency')
    def recency_weight(last_played_ts):
        if not last_played_ts:
            return 0.5
        try:
            age = max(0.0, now_ts - float(last_played_ts))
        except Exception:
            return 0.5
        # exponential decay with half-life
        return 0.5 ** (age / decay_seconds)

    # Accept either a list of hero stats or a single hero dict
    single_input = False
    if isinstance(player_stats, dict):
        single_input = True
        heroes_list = [player_stats]
    else:
        heroes_list = list(player_stats or [])

    # Collect maxima for simple normalization across the player's heroes
    max_vals = {
        "kills_per_min": 0.0,
        "assists_per_min": 0.0,
        "deaths_per_min": 0.0,
        "networth_per_min": 0.0,
        "damage_per_min": 0.0,
        "obj_damage_per_min": 0.0,
        "accuracy": 0.0,
        "crit_shot_rate": 0.0,
        "ending_level": 0.0,
    }

    print('hero list')
    for h in heroes_list:
        for k in ("kills_per_min", "assists_per_min", "deaths_per_min", "networth_per_min", "damage_per_min", "obj_damage_per_min", "accuracy", "crit_shot_rate", "ending_level"):
            v = h.get(k)
            if v is None:
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            if fv > max_vals[k]:
                max_vals[k] = fv

    # Avoid divide by zero by setting minima
    for k in list(max_vals.keys()):
        if max_vals[k] <= 0:
            max_vals[k] = 1.0

    # feature total weight (for normalization)
    feature_weight_sum = sum([v for k, v in params.items() if k.startswith("w_")])

    hero_results = []
    total_weight = 0.0
    weighted_norm_score_sum = 0.0

    for h in heroes_list:
        matches = h.get("matches_played", 0) or 0
        if matches <= 0:
            # include breakdown with zeros
            hero_results.append({
                "hero_id": h.get("hero_id"),
                "hero_name": HEROS.get(h.get("hero_id"), "Unknown"),
                "matches_played": matches,
                "raw_score": 0.0,
                "score": 0.0,
                "weight": 0.0,
                "hero_pr": 0.0,
            })
            continue

        wins = h.get("wins", 0) or 0
        win_rate = float(wins) / float(matches) if matches > 0 else 0.0

        # Normalized features (0..1)
        nk = float(h.get("kills_per_min") or 0.0) / max_vals["kills_per_min"]
        na = float(h.get("assists_per_min") or 0.0) / max_vals["assists_per_min"]
        nd = 1.0 - (float(h.get("deaths_per_min") or 0.0) / max_vals["deaths_per_min"]) if max_vals["deaths_per_min"] > 0 else 1.0
        nn = float(h.get("networth_per_min") or 0.0) / max_vals["networth_per_min"]
        ndmg = float(h.get("damage_per_min") or 0.0) / max_vals["damage_per_min"]
        nobj = float(h.get("obj_damage_per_min") or 0.0) / max_vals["obj_damage_per_min"]
        nacc = float(h.get("accuracy") or 0.0) / max_vals["accuracy"]
        ncrit = float(h.get("crit_shot_rate") or 0.0) / max_vals["crit_shot_rate"]
        nlevel = float(h.get("ending_level") or 0.0) / max_vals["ending_level"]

        # Weighted sum (raw)
        raw_score = (
            params["w_win"] * win_rate +
            params["w_kills"] * nk +
            params["w_assists"] * na +
            params["w_deaths"] * nd +
            params["w_networth"] * nn +
            params["w_damage"] * ndmg +
            params["w_obj"] * nobj +
            params["w_accuracy"] * nacc +
            params["w_crit"] * ncrit +
            params["w_level"] * nlevel
        )

        # normalize raw score to 0..1 by dividing by feature weight sum
        norm_score = (raw_score / feature_weight_sum) if feature_weight_sum > 0 else 0.0

        # Confidence / importance weight: based on matches and recency
        rec_w = recency_weight(h.get("last_played"))
        match_conf = (matches ** 0.5) * params["match_confidence_scale"]
        weight = match_conf * rec_w

        weighted_norm_score_sum += norm_score * weight
        total_weight += weight

        # scale per-hero PR to MAX_PR range
        hero_pr = norm_score * MAX_PR

        hero_results.append({
            "hero_id": h.get("hero_id"),
            "hero_name": HEROS.get(h.get("hero_id"), "Unknown"),
            "matches_played": matches,
            "raw_score": round(raw_score, 4),
            "score": round(norm_score, 4),
            "weight": round(weight, 4),
            "win_rate": round(win_rate, 4),
            "hero_pr": round(hero_pr, 2),
        })

    print('hero list pass')
    overall_norm = (weighted_norm_score_sum / total_weight) if total_weight > 0 else 0.0

    # scale to user-requested PR scale: 0..MAX_PR where each 100 PR = new tier
    overall_pr = overall_norm * MAX_PR

    # badge/tier calculation: rank_index (0-based) where 0 = Initiate 1, ... max = max_pr_tiers-1
    rank_index = int(math.floor(overall_pr / params["pr_per_tier"])) if overall_pr > 0 else 0
    rank_index = max(0, min(params["max_pr_tiers"] - 1, rank_index))
    badge_num = rank_index + 1  # 1-based badge numbering matches bot.number_to_rank_emoji

    # When input was a single hero dict, attach general_pr into it for backwards compatibility
    if single_input:
        print('single input')
        out = heroes_list[0]
        out["general_pr"] = round(overall_pr, 2)
        out["pr_badge"] = int(badge_num)
        out["pr_rank_index"] = int(rank_index)
        out["pr_max"] = int(MAX_PR)
        out["pr_params"] = params
        out["hero_pr"] = hero_results[0]["hero_pr"] if hero_results else 0.0
        return out

    # return structure for list input
    return {
        "overall_pr": round(overall_pr, 2),
        "badge": int(badge_num),
        "rank_index": int(rank_index),
        "heroes": sorted(hero_results, key=lambda x: x.get("weight", 0), reverse=True),
        "params": params,
    }