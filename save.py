# TODO
# create a saving system most likely smimilar to the last one
# use json
# update either through time or query rank change

import json
import os
from datetime import datetime, timedelta

DATA_FILE = 'data/data.json'
DATA_EXPIRY_HOURS = 48

with open('data/config.json', 'r') as file:
    config = json.load(file)

def load_data():
    """Load cached data from file"""
    if not os.path.exists(DATA_FILE):
        return {"players": {}, "last_updated": {}}
    
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"players": {}, "last_updated": {}}
    
def save_data(data):
    """Save data to cache file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_player_data(puuid):
    """Get player data from cache if recent enough"""
    data = load_data()
    player_data = data["players"].get(puuid)
    last_updated = data["last_updated"].get(puuid)
    
    if player_data and last_updated:
        last_update_time = datetime.fromisoformat(last_updated)
        if datetime.now() - last_update_time < timedelta(hours=DATA_EXPIRY_HOURS):
            return player_data
    return None

def update_player_data(puuid, player_data):
    """Update cache with new player data"""
    data = load_data()
    data["players"][puuid] = player_data
    data["last_updated"][puuid] = datetime.now().isoformat()
    save_data(data)