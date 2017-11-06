import discord
import asyncio
import gspread
import json
from creds import DISCORD_API_KEY
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name('gspread.json', scope)
gc = gspread.authorize(credentials)

# Open a worksheet from spreadsheet with one shot
wks = gc.open_by_key("1sinvxQCx0e0L0NNFauq_xg3YmeU_dSA4wH3CZDwYmJs").sheet1

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

@client.event
async def on_message(message):
    if message.channel.is_private:
        try:
            found = wks.find(message.content.lstrip('0'))
            print (found)
            row = found.row
            r = wks.row_values(row)
            print (r, message.author, message.author.name)
            if r[3] == message.content.lstrip('0') and r[4] == str(message.author):
                for s in client.servers:
                    if s.id == "257145891947937808":
                        print (s)
                        member = s.get_member(str(message.author.id))
                        print (member)
                        split = r[2].split(', ')
                        print (split)
                        roles = []
                        removed_roles = []
                        for role in s.roles:
                            if str(role) in corresponding.values():
                                removed_roles.append(role)
                        await client.remove_roles(member, *roles)
                        for role_str in split:

                            if role_str in corresponding:
                                print (role_str)
                                roles.append([role for role in s.roles if str(role) == corresponding[role_str]][0])
                        print (roles)

                        await client.add_roles(member, *roles)
        except Exception as e:
            print (e)

    if message.content.startswith('!test'):
        counter = 0
        tmp = await client.send_message(message.channel, 'Calculating messages...')
        async for log in client.logs_from(message.channel, limit=100):
            if log.author == message.author:
                counter += 1

        await client.edit_message(tmp, 'You have {} messages.'.format(counter))
    elif message.content.startswith('!sleep'):
        await asyncio.sleep(5)
        await client.send_message(message.channel, 'Done sleeping')

client.run(DISCORD_API_KEY)
