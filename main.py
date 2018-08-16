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
test = True
test_server = '465563181188907008'
nues_server = '257145891947937808'

test_log = '479719966082596865'
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

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('gspread.json', scope)
gc = gspread.authorize(credentials)

# Open a worksheet from spreadsheet with one shot
sheet = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").sheet1
sheet2 = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").get_worksheet(1)

client = discord.Client()

server = discord.Object(test_server if test else nues_server)

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
    logger.info(f'Adding role {role_name} to {user}')
    await client.add_roles(user, *[r for r in server.roles if r.name == role_name])


async def remove_role(server: discord.Server, user: discord.Member, role_name: str):
    logger.info(f'Removing role {role_name} from {user}')
    await client.remove_roles(user, *[r for r in server.roles if r.name == role_name])


async def log_msg(msg):
    logger.info(f'{msg}')
    await client.send_message(discord.Object(test_log if test else nues_log), msg)


@client.event
async def on_message(message: discord.Message):
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
            logger.info(f'User {message.author} requesting role change')
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
            m = buildGRMsg()
            await client.send_message(message.channel, m)

# build the game roles message
def buildGRMsg():
    m = "Available roles:\n"
    for game in game_roles:
        m += f"`.iam {game}`\n"
    m += "You can remove roles with `.iamnot <game>`"
    return m

async def dontcrash():
    channels = client.get_all_channels()
    asyncio.sleep(50)

@client.event
async def on_member_join(user: discord.Member):
    try:
        welcome_message = sheet2.col_values(2)[1].replace('$user', f'{user.mention}')
        await client.send_message(user, welcome_message)
        await log_msg(welcome_message)
    except discord.errors.Forbidden:
        await log_msg(f'Could not send welcome message to {user.mention}! It is forbidden.')
    except Exception as e:
        await log_msg(f'Could not send welcome message to {user.mention}! {e}')

async def poll_sheet():
    await client.wait_until_ready()
    await client.change_presence(game=discord.Game(name='Join OrgSync!'))
    while not client.is_closed:
        try:
            logger.info(f'Checking spreadsheets...')
            if credentials.access_token_expired:
                gc.login()  # refreshes the token
            server = client.get_server(test_server if test else nues_server)
            try:
                ppl = sheet.col_values(3)[1:][::-1]
                emails = sheet.col_values(2)[1:][::-1] # reverse so we use the most recent
                first_names = sheet.col_values(6)[1:][::-1]
                ingame_names = sheet.col_values(7)[1:][::-1]
            except gspread.exceptions.APIError:
                await log_msg('API error checking sheet, sleeping....')
                asyncio.sleep(120)
                continue
            for i, email in enumerate(emails):
                discord_username = ppl[i]
                if i < len(first_names):
                    first_name = first_names[i]
                else:
                    first_name = ""
                if i < len(ingame_names):
                    ingame_name = ingame_names[i]
                else:
                    ingame_name = ""
                if not email.endswith('husky.neu.edu'):
                    continue
                usr = server.get_member_named(discord_username)
                if usr is None:
                    print(f'User {discord_username} does not exist!')
                    if ' #' in discord_username:
                        usr = server.get_member_named(discord_username.replace(' #', '#'))
                    if usr is None:
                        continue
                if has_role(usr, 'Student'):
                    pass
                else:
                    logger.info(f'User {usr} does not have student role, adding...')
                    await add_role(server, usr, 'Student')
                    await log_msg(f'Added student role to `{discord_username}` with email `{email}`.')
                    if len(first_name) != 0 and len(ingame_name) != 0:
                        name = f'{first_name} "{ingame_name}"'
                        await client.change_nickname(usr, name)
                        await log_msg(f'Succesfully set nickname of {usr.mention} to `{name}`')
                    try:
                        await send_welcome(usr)
                    except discord.errors.Forbidden:
                        await log_msg(f'Could not send role set message to {usr.mention}! It is forbidden.')
                    except Exception as exc:
                        await log_msg(f'Could not send role set message to {usr.mention}! {exc}')
            logger.info(f'Done, sleeping...')
            await asyncio.sleep(20)  # task runs every 10 seconds
        except Exception as e:
            await log_msg(f'Error checking spreadsheet: {e}')

#@matt mage, do we need this code block below here? I think it is doing
#what is done above in the on_member_join function?
async def send_welcome(user: discord.Member):
    welcome_message = sheet2.col_values(1)[1]
    await client.send_message(user, welcome_message)
    logger.info(f'Sent welcome message to {user}')

#This below should always check when role "new role" has been updated to see if the name has changed
@client.event
async def on_server_role_update(new_role_prename, new_role_postname):
    if new_role_prename.name == 'new role':
        #if the name of the role is not the same after "new role" is updated, do the following
        if new_role_prename.name != new_role_postname.name:
            exec_board_role = discord.utils.get(server.roles, name = "Executive Board", id = '479707814026149888' if test else "359036894467850262")
            new_gamerole_msg = (exec_board_role.mention + "is" + new_role_postname.name + "a game role?")
            await log_msg(new_gamerole_msg)
            await client.add_reaction(new_gamerole_msg, '✅')
            await client.add_reaction(new_gamerole_msg, '❌')
            res = await client.wait_for_reaction(['✅', '❌'], message= new_gamerole_msg)
            await log_msg("Thank you for your feedback!")
            if(res.reaction.emoji=='✅'):
                #add the game role to the game_roles list
                #build a new GRMsg and edit the old one with the new one
                game_roles.append(new_role_postname.name)
                role_msg.id = '451547972161896448'
                new_GRmsg = await buildGRMsg()
                await client.edit_message(role_msg, new_GRmsg)
            await client.delete_message(new_gamerole_msg)


client.loop.create_task(dontcrash())
client.loop.create_task(poll_sheet())

client.run(DISCORD_API_KEY)
