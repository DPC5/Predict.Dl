import discord 
from discord import app_commands, colour
from discord.ext import commands
import json
import asyncio
from api import get_deadlock_hero_stats, HEROS, get_hero_stats, get_most_played_heros, resolve_steam_id, steam64_to_steamid3, get_hero_rank, STEAM_API_KEY
import requests

TEST_GUILD = discord.Object(id=1349068689521115197)
STATS_FILE = 'data/stats.json'
CONFIG_FILE = 'data/config.json'

with open(CONFIG_FILE, 'r') as file:
    config = json.load(file)

token = config.get('token')
DL_API = config.get('DL_API')

with open(STATS_FILE, 'r') as f:
    stats = json.load(f)

ver = stats['version']

# Team Colors

AMBER_HAND = 0x493D16
SAPHIRE_FLAME = 0x273462

bot = commands.Bot(command_prefix= '^',intents = discord.Intents.default())
bot.remove_command('help')

# BOT EVENTS

@bot.event
async def on_ready():
    asyncio.create_task(update_activity())
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync(guild=TEST_GUILD)
        print(f"Synced {len(synced)} command(s) to test guild")
    except Exception as e:
        print(e)
    
    try:
        synced_global = await bot.tree.sync()
        print(f"Synced {len(synced_global)} global command(s)")
    except Exception as e:
        print(e)

async def update_activity():
    while True:
        predicts = stats['predict']
        await bot.change_presence(activity=discord.Streaming(name="{} Predictions".format(predicts), url="https://www.twitch.tv/morememes_"))
        await asyncio.sleep(30)

# Emojis

# Rank emoji mapping

RANK_EMOJIS = {
    "obscurus": "<:Obscurus:1420115617767493644>",

    "initiate": [
        "<:Initiate_1:1420115499743842354>",
        "<:Initiate_2:1420115535928098886>",
        "<:Initiate_3:1420115567167410266>",
        "<:Initiate_4:1420115578118607033>",
        "<:Initiate_5:1420115593402515640>",
        "<:Initiate_6:1420115607310827581>",
    ],
    "seeker": [
        "<:Seeker_1:1420115825309909033>",
        "<:Seeker_2:1420115834130534480>",
        "<:Seeker_3:1420115849561506018>",
        "<:Seeker_4:1420115858747035699>",
        "<:Seeker_5:1420115868620423188>",
        "<:Seeker_6:1420115877805817937>",
    ],
    "alchemist": [
        "<:Alchemist_1:1420115132700168202>",
        "<:Alchemist_2:1420115144666513408>",
        "<:Alchemist_3:1420115152811982949>",
        "<:Alchemist_4:1420115161410175107>",
        "<:Alchemist_5:1420115177462042675>",
        "<:Alchemist_6:1420115186001379470>",
    ],
    "arcanist": [
        "<:Arcanist_1:1420115194587119757>",
        "<:Arcanist_2:1420115203504214136>",
        "<:Arcanist_3:1420115212496928860>",
        "<:Arcanist_4:1420115224001904751>",
        "<:Arcanist_5:1420115232533250128>",
        "<:Arcanist_6:1420115241064206356>",
    ],
    "ritualist": [
        "<:Ritualist_1:1420115764832374895>",
        "<:Ritualist_2:1420115776416911451>",
        "<:Ritualist_3:1420115786680504350>",
        "<:Ritualist_4:1420115797405208637>",
        "<:Ritualist_5:1420115806309716040>",
        "<:Ritualist_6:1420115815411486791>",
    ],
    "emissary": [
        "<:Emissary_1:1420115362560606338>",
        "<:Emissary_2:1420115371704189088>",
        "<:Emissary_3:1420115380780793986>",
        "<:Emissary_4:1420115389286715523>",
        "<:Emissary_5:1420115397629313127>",
        "<:Emissary_6:1420115407058243584>",
    ],
    "archon": [
        "<:Archon_1:1420115251004969073>",
        "<:Archon_2:1420115259242446999>",
        "<:Archon_3:1420115268755263640>",
        "<:Archon_4:1420115277743390882>",
        "<:Archon_5:1420115287587426404>",
        "<:Archon_6:1420115296466894979>",
    ],
    "oracle": [
        "<:Oracle_1:1420115627934351481>",
        "<:Oracle_2:1420115637384122430>",
        "<:Oracle_3:1420115648628920400>",
        "<:Oracle_4:1420115659152560189>",
        "<:Oracle_5:1420115671773089873>",
        "<:Oracle_6:1420115682346926121>",
    ],
    "phantom": [
        "<:Phantom_1:1420115697803202570>",
        "<:Phantom_2:1420115708594884658>",
        "<:Phantom_3:1420115721727246438>",
        "<:Phantom_4:1420115733462913094>",
        "<:Phantom_5:1420115743634227250>",
        "<:Phantom_6:1420115754467987456>",
    ],
    "ascendant": [
        "<:Ascendant_1:1420115306436759602>",
        "<:Ascendant_2:1420115314452205568>",
        "<:Ascendant_3:1420115322580766773>",
        "<:Ascendant_4:1420115330902261840>",
        "<:Ascendant_5:1420115341454872636>",
        "<:Ascendant_6:1420115352444211331>",
    ],
    "eternus": [
        "<:Eternus_1:1420115416377720902>",
        "<:Eternus_2:1420115424170741861>",
        "<:Eternus_3:1420115433482092664>",
        "<:Eternus_4:1420115447151595673>",
        "<:Eternus_5:1420115457247019109>",
        "<:Eternus_6:1420115465136509071>",
    ],
}

RANK_NAMES = list(RANK_EMOJIS.keys())

def number_to_rank_emoji(num: int) -> str:
    """
    Convert a number to its corresponding Discord rank emoji.
    - 0 = obscurus
    - 1-6 = initiate 1-6
    - 7-12 = seeker 1-6
    - etc.
    """
    if num == 0:
        return RANK_EMOJIS["obscurus"]

    rank_index = (num - 1) // 6 + 1
    tier = (num - 1) % 6
    if rank_index >= len(RANK_NAMES):
        raise ValueError("Number out of range for available ranks.")
    
    rank_name = RANK_NAMES[rank_index]
    return RANK_EMOJIS[rank_name][tier]

def mmr_to_badge(mmr_score: float) -> int:
    """
    Convert an MMR score into a badge integer.
    """
    mmr_int = int(mmr_score)  # floor/round to int
    return 10 * (mmr_int // 6) + 1 + (mmr_int % 6)

def badge_to_emoji(badge: int) -> str:
    """
    Convert a badge number into the correct Discord emoji.
    """
    return number_to_rank_emoji(badge)

def player_to_emoji(player_data: dict) -> str:
    """
    Convert API player data to the correct rank emoji.
    
    player_data looks like:
    {
      "account_id": 115314746,
      "match_id": 42858596,
      "start_time": 1758468022,
      "player_score": 17.685717899087688,
      "rank": 35,
      "division": 3,
      "division_tier": 5
    }
    """
    mmr_score = player_data["player_score"]
    badge = mmr_to_badge(mmr_score)
    return badge_to_emoji(badge)

# BOT COMMANDS

@bot.tree.command(name="info", description="Get information about Predict.Dl", guild=TEST_GUILD)
async def info(interaction: discord.Interaction):

    embed = discord.Embed(title=" ", description=f"Version {ver} By Morememes")
    embed.set_author(name="Predict.Dl")
    embed.add_field(name="What does it do?", value="This bot was made as a test to see a couple things. First, if I could make a functioning bot. Second, can I make a program that has some connection to a game I play.", inline=False)
    embed.add_field(name="What is PR?", value="PR or Player Rating, is a number that gives an estimate to how much positive impact a player has on their game. ", inline=False)
    embed.add_field(name="How is PR calculated?", value="PR is calculated right now by taking average stats over the past 10 games and comparing them with your rank. These stats include damage, objective damage, kda, and more.", inline=False)
    embed.add_field(name="Why is somone's PR so high?", value="PR has two values, the main one being general PR this is what is displayed using /lookup. This value is the impact that the player would have on an average game with ranging skill levels. The next PR is hidden, this will only be seen when ranks are close together. This PR will no longer apply bonuses based on rank. This is mainly prevelant in higher elo.", inline=False)
    embed.add_field(name="More?", value="If you have any suggestions please message me on discord. Also, keep in mind this is my first discord bot and first semi-public program, there will be bugs please be patient.", inline=False)
    
    await interaction.response.send_message(embed=embed)

#lookup commands, basic stats and rank, no PR yet

#TODO
# add PR
# add caching

@bot.tree.command(name="lookup", description="Look up a Deadlock player by account or name", guild=TEST_GUILD)
async def lookup(interaction: discord.Interaction, account: str):
    
    await interaction.response.defer()
    progress_msg = await interaction.followup.send("Resolving Steam ID... ⏳")

    try:
        steam64 = resolve_steam_id(account)
        steamid3 = steam64_to_steamid3(steam64)
    except ValueError as e:
        return await progress_msg.edit(content=f"Error: {e}")

    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={steam64}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return await progress_msg.edit(content=f"Failed to contact Steam API: {e}")
    except ValueError:
        return await progress_msg.edit(content="Steam API returned invalid data.")

    if not data.get('response', {}).get('players'):
        return await progress_msg.edit(content="Could not find that Steam account.")

    player_info = data['response']['players'][0]
    vanity_name = player_info.get('personaname', steam64)
    avatar_url = player_info.get('avatarfull', None)

    await progress_msg.edit(content="Fetching hero stats... 🔍")

    hero_stats = await get_deadlock_hero_stats(account)
    await progress_msg.edit(content="Calculating stats... 📊")
    
    most_played_hero_id = get_most_played_heros(hero_stats)[0][2]
    player_stats = get_hero_stats(hero_stats, most_played_hero_id)
    hero_rank = await get_hero_rank(most_played_hero_id, steamid3)

    rank_emoji = player_to_emoji(hero_rank)
    rank_display = f"{rank_emoji} " if rank_emoji else ""

    await progress_msg.edit(content="Building player stats embed... 🛠️")

    steam_url = f"https://steamcommunity.com/profiles/{steam64}"
    embed = discord.Embed(
        title=f" ",
        description = f"Most Played Hero: **{HEROS.get(player_stats['hero_id'], 'Unknown')}** {rank_display}",
        color=discord.Color.green()
    )
    embed.set_author(name=f"{vanity_name}", url=steam_url, icon_url="attachment://steam.png")
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.add_field(name="General", value=f"Matches Played: {player_stats['matches_played']}\nWins: {player_stats['wins']}\nEnding Level: {player_stats['ending_level']:.2f}", inline=False)
    embed.add_field(name="Performance", value=f"Kills: {player_stats['kills']}\nDeaths: {player_stats['deaths']}\nAssists: {player_stats['assists']}", inline=False)
    embed.add_field(name="Rates", value=f"Kills/Min: {player_stats['kills_per_min']:.2f}\nDeaths/Min: {player_stats['deaths_per_min']:.2f}\nAssists/Min: {player_stats['assists_per_min']:.2f}\nNetworth/Min: {player_stats['networth_per_min']:.2f}", inline=False)

    await progress_msg.edit(content="Here are the stats! ✅", embed=embed)




bot.run(token)

