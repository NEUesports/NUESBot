import asyncio

import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials

from creds import DISCORD_API_KEY

# SERVER IDs:

test_server = '355860577047937024'
nues_server = '257145891947937808'

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('gspread.json', scope)
gc = gspread.authorize(credentials)

# Open a worksheet from spreadsheet with one shot
sheet = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").sheet1
sheet2 = gc.open_by_key("1zMeLAnlh8-EyXA20XPVv1nHHWu52dlcjPxojLVYR5DA").get_worksheet(1)

client = discord.Client()


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


corresponding = {
    'PUBG': 'PUBG',
    'Rocket League': 'Rocket League',
    'Super Smash Bros. Melee': 'SSBM',
    'Hearthstone': 'Hearthstone',
    'Destiny 2': 'Destiny',
    'Civilization': 'Civilization'
}


def has_role(user, role_name):
    return any([r.name == role_name for r in user.roles])


async def add_role(server: discord.Server, user: discord.Member, role_name: str):
    await client.add_roles(user, *[r for r in server.roles if r.name == role_name])


async def log_msg(msg):
    await client.send_message(discord.Object('451514381432389642'), msg)


@client.event
async def on_message(message):
    if message.channel.is_private:
        try:
            found = sheet.find(message.content.lstrip('0'))
            print(found)
            row = found.row
            r = sheet.row_values(row)
            print(r, message.author, message.author.name)
            if r[3] == message.content.lstrip('0') and r[4] == str(message.author):
                for s in client.servers:
                    if s.id == "257145891947937808":
                        print(s)
                        member = s.get_member(str(message.author.id))
                        print(member)
                        split = r[2].split(', ')
                        print(split)
                        roles = []
                        removed_roles = []
                        for role in s.roles:
                            if str(role) in corresponding.values():
                                removed_roles.append(role)
                        await client.remove_roles(member, *roles)
                        for role_str in split:

                            if role_str in corresponding:
                                print(role_str)
                                roles.append([role for role in s.roles if str(role) == corresponding[role_str]][0])
                        print(roles)

                        await client.add_roles(member, *roles)
        except Exception as e:
            print(e)

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


async def poll_sheet():
    await client.wait_until_ready()
    await client.change_presence(game=discord.Game(name='Join OrgSync!'))
    while not client.is_closed:
        server = client.get_server(test_server)
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
