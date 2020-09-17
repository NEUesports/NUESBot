import asyncio
import json
import logging
import traceback

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

test_server = 465563181188907008
nues_server = 257145891947937808

test_log = 479719966082596865
nues_log = 441692695937810432

test_execboard = 479707814026149888
nues_execboard = 359036894467850262

set_roles_channel = 451532020695433217

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

credentials = ServiceAccountCredentials.from_json_keyfile_name('gspread.json', scope)
gc = gspread.authorize(credentials)

# Open a worksheet from spreadsheet with one shot
sheet = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").sheet1
sheet2 = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").get_worksheet(1)

client = discord.Client()

with open('game_roles.json') as f:
    game_roles = json.load(f)

server = client.get_guild(test_server if test else nues_server)


@client.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('Current Game Roles:')
    print(game_roles)


def has_role(user, role_name):
    return any([r.name.lower() == role_name.lower() for r in user.roles])


async def add_role(server: discord.Guild, user: discord.Member, role_name: str):
    logger.info(f'Adding role {role_name} to {user}')
    await user.add_roles(*[r for r in server.roles if r.name == role_name])


async def remove_role(server: discord.Guild, user: discord.Member, role_name: str):
    logger.info(f'Removing role {role_name} from {user}')
    await user.remove_roles(*[r for r in server.roles if r.name == role_name])

def get_server():
    return client.get_guild(nues_server)

def get_log_channel():
    return get_server().get_channel(test_log if test else nues_log)

async def log_msg(msg):
    logger.info(f'{msg}')
    return await get_log_channel().send(msg)


@client.event
async def on_message(message: discord.Message):

    if isinstance(message.channel, discord.DMChannel):
        return
    
    if message.content.startswith('!test') and has_role(message.author, 'Student'):
        counter = 0
        tmp = await message.channel.send('Calculating messages...')
        async for log in message.channel.history(limit=100):
            if log.author == message.author:
                counter += 1

        await tmp.edit('You have {} messages.'.format(counter))
    elif message.content.startswith('!sleep'):
        await asyncio.sleep(5)
        await message.channel.send('Done sleeping')
    elif message.content.startswith('!pm'):
        await send_welcome(message.author)
    elif message.content.startswith('!join'):
        await on_member_join(message.author)
    elif message.content.startswith('!add') and any([r.name == 'Bot Master' for r in message.author.roles]):
        await add_game_role(message.content.replace('!add ', ''))
    elif message.content.startswith('!remove') and any([r.name == 'Bot Master' for r in message.author.roles]):
        await remove_game_role(message.content.replace('!remove ', ''))
    elif message.channel.name == 'set-roles':
        if message.content.startswith('.iam ') and any([r.name == 'Student' for r in message.author.roles]):
            logger.info(f'User {message.author} requesting role change')
            msg = message.content.split(' ')
            game_list = " ".join(msg[1:])
            games = game_list.split(',')
            for game in games:
                game = game.strip()
                if game in game_roles:
                    await add_role(message.guild, message.author, game)
                    await log_msg(f'Added role `{game}` to `{message.author}`')
        if message.content.startswith('.iamnot ') and any([r.name == 'Student' for r in message.author.roles]):
            msg = message.content.split(' ')
            game_list = " ".join(msg[1:])
            games = game_list.split(',')
            for game in games:
                game = game.strip()
                if game in game_roles:
                    await remove_role(message.guild, message.author, game)
                    await log_msg(f'Removed role `{game}` from `{message.author}`')
        if message.author.name != client.user.name:
            await message.delete()
        empty = True
        async for log in message.channel.history():
            print(log)
            empty = False
            break
        if empty:
            m = buildGRMsg()
            await message.channel.send(m)


# build the game roles message
def buildGRMsg():
    m = "Available roles:\n"
    print(game_roles)
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
        await user.send(welcome_message)
        await log_msg(welcome_message)
    except discord.errors.Forbidden:
        await log_msg(f'Could not send welcome message to {user.mention}! It is forbidden.')
    except Exception as e:
        await log_msg(f'Could not send welcome message to {user.mention}! {e}')


async def poll_sheet():
    await client.wait_until_ready()
    await client.change_presence(activity=discord.Game(name='Join OrgSync!'))
    while True:
        try:
            logger.info(f'Checking spreadsheets...')
            if credentials.access_token_expired:
                gc.login()  # refreshes the token
            server = client.get_guild(test_server if test else nues_server)
            try:
                ppl = sheet.col_values(3)[1:][::-1]
                emails = sheet.col_values(2)[1:][::-1]  # reverse so we use the most recent
                first_names = sheet.col_values(6)[1:][::-1]
                ingame_names = sheet.col_values(7)[1:][::-1]
            except gspread.exceptions.APIError:
                await log_msg('API error checking sheet, sleeping....')
                asyncio.sleep(120)
                continue
            skip = []
            for i, email in enumerate(emails):
                if email in skip:
                    continue
                discord_username = ppl[i]
                if i < len(first_names):
                    first_name = first_names[i]
                else:
                    first_name = ""
                if i < len(ingame_names):
                    ingame_name = ingame_names[i]
                else:
                    ingame_name = ""
                if not (email.endswith('husky.neu.edu') or email.endswith('northeastern.edu')):
                    continue
                usr = server.get_member_named(discord_username)
                if usr is None:
                    if ' #' in discord_username:
                        usr = server.get_member_named(discord_username.replace(' #', '#'))
                    if usr is None:
                        print(f'User {discord_username} does not exist!')
                        continue
                if has_role(usr, 'Student'):
                    if len(first_name) != 0 and len(ingame_name) != 0:
                        name = f'{first_name} "{ingame_name}"'
                        if name != usr.display_name:
                            await log_msg(f'changing nickname of {usr.display_name} to `{name}`')
                            await usr.edit(nick=name) 
                            await log_msg(f'Succesfully set nickname of {usr.mention} to `{name}`')
                            await log_msg(f"cleaning sheet of previous inputs")
                            occurences = [i for i, x in enumerate(emails) if x == email]
                            last_occurence = emails.index(email)
                            print("last: ", last_occurence)
                            occurences.remove(last_occurence)
                            if len(occurences) > 0:
                                print(f"need to clean occurences of: {email}")
                                skip.append(email)
                            for occurence in occurences:
                                actual = len(emails) - occurence + 1
                                await log_msg(f"removing row: {sheet.row_values(actual)}")
                                sheet.delete_row(actual)
                            
                else:
                    logger.info(f'User {usr} does not have student role, adding...')
                    await add_role(server, usr, 'Student')
                    await log_msg(f'Added student role to `{discord_username}` with email `{email}`.')
                    if len(first_name) != 0 and len(ingame_name) != 0:
                        name = f'{first_name} "{ingame_name}"'
                        if len(name) > 32:
                            sheet.delete_row(len(emails) - emails.index(email) + 1)
                        await usr.edit(nick=name)
                        await log_msg(f'Succesfully set nickname of {usr.mention} to `{name}`')
                    try:
                        await send_welcome(usr)
                    except discord.errors.Forbidden:
                        await log_msg(f'Could not send role set message to {usr.mention}! It is forbidden.')
                    except Exception as exc:
                        await log_msg(f'Could not send role set message to {usr.mention}! {exc}')
            logger.info(f'Done, sleeping...')
            await asyncio.sleep(20)  # task runs every 20 seconds
        except Exception as e:
            traceback.print_exc()
            await log_msg(f'Error checking spreadsheet: {e}')


async def send_welcome(user: discord.Member):
    welcome_message = sheet2.col_values(1)[1]
    await user.send(welcome_message)
    logger.info(f'Sent welcome message to {user}')


# Ask if newly creted role is game role.
@client.event
async def on_server_role_create(new_role: str):
    if new_role.name != 'new role':
        server = client.get_guild(test_server if test else nues_server)
        exec_board_role = discord.utils.get(server.roles, name="Executive Board",
                                            id=test_execboard if test else nues_execboard)
        new_gamerole_msg = (exec_board_role.mention + " is " + new_role.name + " a game role?")
        new_gamerole_msg = await log_msg(new_gamerole_msg)
        await new_gamerole_msg.add_reaction('✅')
        await new_gamerole_msg.add_reaction('❌')
        await asyncio.sleep(1)
        def pred(reaction, user):
            return str(reaction.emoji) == '✅'  or str(reaction.emoji) == '❌'
        res = await client.wait_for("reaction_add", check=pred)
        await log_msg("Thank you for your feedback!")
        if res.reaction.emoji == '✅':
            # add the game role to the game_roles list
            game_roles.append(new_role.name)
            # build a new GRMsg and edit the old one with the new one
            await update_gm_message()
            await log_msg("Updated Set Roles message with " + new_role.name)
            write_game_roles_to_disk()
        await new_gamerole_msg.delete()


# ask if role is a game role if the name is updated from "new role"
@client.event
async def on_server_role_update(new_role_prename, new_role_postname):
    if new_role_prename.name == 'new role':
        if new_role_prename.name != new_role_postname.name:
            server = client.get_guild(test_server if test else nues_server)
            exec_board_role = discord.utils.get(server.roles, name="Executive Board",
                                                id=test_execboard if test else nues_execboard)
            new_gamerole_msg = (exec_board_role.mention + " is " + new_role_postname.name + " a game role?")
            new_gamerole_msg = await log_msg(new_gamerole_msg)
            await new_gamerole_msg.add_reaction('✅')
            await new_gamerole_msg.add_reaction('❌')
            await asyncio.sleep(1)
            def pred(reaction, user):
                return str(reaction.emoji) == '✅'  or str(reaction.emoji) == '❌'
            res = await client.wait_for("reaction_add", check=pred)
            await log_msg("Thank you for your feedback!")
            if res.reaction.emoji == '✅':
                # add the game role to the game_roles list
                game_roles.append(new_role_postname.name)
                await update_gm_message()
                await log_msg("Updated Set Roles message with " + new_role_postname.name)
                write_game_roles_to_disk()
            await new_gamerole_msg.delete()


async def update_gm_message():
    set_roles_channel = client.get_channel(465609299285245955 if test else 451532020695433217)
    role_msg = await set_roles_channel.fetch_message(482608179104972820 if test else 451547972161896448)
    new_GRmsg = buildGRMsg()
    await role_msg.edit(new_GRmsg)


async def add_game_role(role_name: str):
    game_roles.append(role_name)
    write_game_roles_to_disk()
    await update_gm_message()
    await log_msg('Added game role ' + role_name)


async def remove_game_role(role_name: str):
    try:
        if role_name in game_roles:
            game_roles.remove(role_name)
            write_game_roles_to_disk()
        await update_gm_message()
        await log_msg('Removed game role ' + role_name)
    except Exception as e:
        await log_msg('Error removing game role: ' + str(e))


def write_game_roles_to_disk():
    with open("game_roles.json", mode="w") as f:
        json.dump(game_roles, f)


async def protected_game_channels():
    await client.wait_until_ready()
    members = client.get_all_members()
    server = client.get_guild(test_server if test else nues_server)
    with open('game_roles.json') as f:
        game_roles = json.load(f)
    for member in members:
        for game_role in game_roles:
            if has_role(member, game_role) and (not has_role(member, 'Student') and not has_role(member, 'Guest')):
                role = discord.utils.get(server.roles, name=f'{game_role}')
                await member.remove_roles(role)
                rem_role_msg = (
                    f'{member} your role, {game_role}, on the Northeastern University Esports Discord has been removed since you are not registered as a student. Please register as a student using the Google Form at https://goo.gl/forms/AwC3tuYLg0GQMPYs1 to regain access to game roles.')
                member.send(rem_role_msg)
                await log_msg(f'Removed `{game_role}` role from `{member}`')
    await asyncio.sleep(86400)  # task runs once a day


client.loop.create_task(protected_game_channels())
client.loop.create_task(dontcrash())
client.loop.create_task(poll_sheet())

client.run(DISCORD_API_KEY)
