import asyncio
import logging

import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from creds import DISCORD_API_KEY

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
# SERVER IDs:
test = False
test_server = '355860577047937024'
nues_server = '257145891947937808'

test_log = '451514381432389642'
nues_log = '441692695937810432'

set_roles_channel = '451532020695433217'

# VALID GAME ROLES
game_roles = [
    'Rocket League',
    'PUBG',
    'DOTA 2',
    'Overwatch',
    'CounterStrike',
    'Hearthstone',
    'Heroes of the Storm',
    'Fortnite',
]

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('gspread.json', scope)
gc = gspread.authorize(credentials)

# Open a worksheet from spreadsheet with one shot
sheet = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").sheet1
sheet2 = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").get_worksheet(1)

client = discord.Client()


@client.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


def has_role(user, role_name):
    return any([r.name.lower() == role_name.lower() for r in user.roles])


async def add_role(server: discord.Server, user: discord.Member, role_name: str):
    await client.add_roles(user, *[r for r in server.roles if r.name == role_name])


async def remove_role(server: discord.Server, user: discord.Member, role_name: str):
    await client.remove_roles(user, *[r for r in server.roles if r.name == role_name])


async def log_msg(msg):
    await client.send_message(discord.Object(test_log if test else nues_log), msg)


@client.event
async def on_message(message: discord.Message):
    print ('msg', message.content)
    if message.content.startswith('!test') and has_role(message.author, 'Student'):
        counter = 0
        tmp = await client.send_message(message.channel, 'Calculating messages...')
        async for log in client.logs_from(message.channel, limit=100):
            if log.author == message.author:
                counter += 1

        await client.edit_message(tmp, 'You have {} messages.'.format(counter))
    elif message.content.startswith('!sleep'):
        await asyncio.sleep(5)
        await client.send_message(message.channel, 'Done sleeping')
    elif message.content.startswith('!pm'):
        await send_welcome(message.author)
    elif message.content.startswith('!join'):
        await on_member_join(message.author)
    elif message.channel.name == 'set-roles':
        if message.content.startswith('.iam ') and any([r.name == 'Student' for r in message.author.roles]):
            msg = message.content.split(' ')
            game_list = " ".join(msg[1:])
            games = game_list.split(',')
            for game in games:
                game = game.strip()
                if game in game_roles:
                    await add_role(message.server, message.author, game)
                    await log_msg(f'Added role `{game}` to `{message.author}`')
        if message.content.startswith('.iamnot ') and any([r.name == 'Student' for r in message.author.roles]):
            msg = message.content.split(' ')
            game_list = " ".join(msg[1:])
            games = game_list.split(',')
            for game in games:
                game = game.strip()
                if game in game_roles:
                    await remove_role(message.server, message.author, game)
                    await log_msg(f'Removed role `{game}` from `{message.author}`')
        if not message.author.name.startswith("NUESBot"):
            await client.delete_message(message)
        empty = True
        async for log in client.logs_from(message.channel):
            print(log)
            empty = False
            break
        if empty:
            m = "Available roles:\n"
            for game in game_roles:
                m += f"`.iam {game}`\n"
            m += "You can remove roles with `.iamnot <game>`"
            await client.send_message(message.channel, m)


@client.event
async def on_member_join(user: discord.Member):
    welcome_message = sheet2.col_values(2)[1].replace('$user', f'{user.mention}')
    await client.send_message(user, welcome_message)
    await log_msg(welcome_message)


async def poll_sheet():
    await client.wait_until_ready()
    await client.change_presence(game=discord.Game(name='Join OrgSync!'))
    i = 0
    while not client.is_closed:

        # reauthorize once in a while to prevent 401 errors
        gc = gspread.authorize(credentials)
        # Open a worksheet from spreadsheet with one shot
        sheet = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").sheet1
        sheet2 = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").get_worksheet(1)

        server = client.get_server(test_server if test else nues_server)
        ppl = sheet.col_values(3)[1:]
        emails = sheet.col_values(2)[1:]
        for p, e in zip(ppl, emails):
            if not e.endswith('husky.neu.edu'):
                continue
            usr = server.get_member_named(p)
            if usr is None:
                # print(f'User {p} does not exist!')
                continue
            if has_role(usr, 'Student'):
                pass
            else:
                print('User does not have student role, adding...')
                await add_role(server, usr, 'Student')
                await log_msg(f'Added student role to `{p}` with email `{e}`.')
                await send_welcome(usr)
        await asyncio.sleep(10)  # task runs every 10 seconds


async def send_welcome(user: discord.Member):
    welcome_message = sheet2.col_values(1)[1]
    await client.send_message(user, welcome_message)


client.loop.create_task(poll_sheet())

client.run(DISCORD_API_KEY)
