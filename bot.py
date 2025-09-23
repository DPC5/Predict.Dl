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

RANK_NAMES = [
    "unranked",    # Obscurus
    "initiate",
    "seeker",
    "alchemist",
    "arcanist",
    "ritualist",
    "emissary",
    "archon",
    "oracle",
    "phantom",
    "ascendant",
    "eternus"
]


RANK_EMOJIS = {}
rank_id = 1

for rank_name in RANK_NAMES:
    if rank_name == "unranked":
        RANK_EMOJIS[0] = "obscurus"
        continue
    for tier in range(1, 7):
        RANK_EMOJIS[rank_id] = f"{rank_name}_{tier}"
        rank_id += 1

def get_rank_emoji(rank_number: int, bot: commands.Bot):
    emoji_name = RANK_EMOJIS.get(rank_number)
    if emoji_name:
        return discord.utils.get(bot.emojis, name=emoji_name)
    return None

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


@bot.tree.command(name="lookup", description="Look up a Deadlock player by account or name", guild=TEST_GUILD)
async def lookup(interaction: discord.Interaction, account: str):
    
    await interaction.response.defer()
    progress_msg = await interaction.followup.send("Resolving Steam ID... ⏳")

    try:
        steam64 = resolve_steam_id(account)
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

    hero_stats = get_deadlock_hero_stats(account)
    await progress_msg.edit(content="Calculating most played hero... 📊")
    
    most_played_hero_id = get_most_played_heros(hero_stats)[0][2]
    player_stats = get_hero_stats(hero_stats, most_played_hero_id)

    rank_info = get_hero_rank(most_played_hero_id, steam64_to_steamid3(steam64))
    rank_number = rank_info['rank'] if rank_info else 0
    print(rank_number)
    rank_emoji = get_rank_emoji(rank_number, bot)
    print(rank_emoji)
    rank_display = f"{rank_emoji} " if rank_emoji else ""

    await progress_msg.edit(content="Building player stats embed... 🛠️")

    steam_url = f"https://steamcommunity.com/profiles/{steam64}"
    embed = discord.Embed(
        title=f" ",
        description = f"Most Played Hero: {rank_display}**{HEROS.get(player_stats['hero_id'], 'Unknown')}**",
        color=discord.Color.green()
    )
    embed.set_author(name=vanity_name, url=steam_url, icon_url="attachment://steam.png")
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.add_field(name="General", value=f"Matches Played: {player_stats['matches_played']}\nWins: {player_stats['wins']}\nEnding Level: {player_stats['ending_level']:.2f}", inline=False)
    embed.add_field(name="Performance", value=f"Kills: {player_stats['kills']}\nDeaths: {player_stats['deaths']}\nAssists: {player_stats['assists']}", inline=False)
    embed.add_field(name="Rates", value=f"Kills/Min: {player_stats['kills_per_min']:.2f}\nDeaths/Min: {player_stats['deaths_per_min']:.2f}\nAssists/Min: {player_stats['assists_per_min']:.2f}\nNetworth/Min: {player_stats['networth_per_min']:.2f}", inline=False)

    await progress_msg.edit(content="Here are the stats! ✅", embed=embed)




bot.run(token)

