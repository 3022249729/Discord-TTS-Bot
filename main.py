import discord
import json
from discord.ext import commands
import TTS
import asyncio
import ctypes
import os


token = 'YOUR_TOKEN_HERE'

cogs = [TTS]

def get_prefix(client, message):
    with open('serverSettings.json', 'r') as f:
        settings = json.load(f)
    return settings[str(message.guild.id)]['prefix']


client = commands.Bot(command_prefix=(get_prefix), case_insensitive=True, intents = discord.Intents.all())

async def main():
    for i in range(len(cogs)):  
        await cogs[i].setup(client)


class Help(commands.HelpCommand):
    def get_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=0x47A7FF)
        prefix = self.context.clean_prefix
        embed.description = f"Do `{prefix}help <command>` for more help of the command.\nType `{prefix}help lang` for the list of supported languages.\n\nCapitalization of the commands are ignored.\n`[argument]` are optional, `<argument>` are required.\n "
        for cog, commands in mapping.items():
            command_signatures = []

            for c in commands:
                signature = f'{prefix}`' + self.get_command_signature(c)[1:].replace(" ", '` ', 1)
                command_signatures.append(signature)

            cog_name = getattr(cog, "qualified_name", "No Category")
            embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        embed.set_footer(text='TTS Bot by ren.xxx', icon_url=self.context.bot.user.avatar.url)
        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command) , color=0x47A7FF)
        if command.description:
            embed.description = command.description
        if alias := command.aliases:
            alias = '`' + "`, `".join(alias) + '`'
            embed.add_field(name="Aliases", value=alias, inline=False)

        embed.set_footer(text='TTS Bot by ren.xxx', icon_url=self.context.bot.user.avatar.url)
        channel = self.get_destination()
        await channel.send(embed=embed)

client.help_command = Help()

@client.event
async def on_ready():
    if not os.path.exists("mp3files"):
        os.makedirs("mp3files")
        
    path = ctypes.util.find_library('opus')
    if path is None:
        raise Exception("Opus not detected, please refer to README and install Opus before running the bot.")
    discord.opus.load_opus(path)
    
asyncio.run(main())
client.run(token)
