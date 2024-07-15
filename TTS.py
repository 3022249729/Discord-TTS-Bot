import random
import string
import discord
from discord.ext import commands
from gtts import gTTS
import re
import os
import json
import asyncio
import time

transitionWord = {
    "en": "said",
    "fr": "dit",
    "zh-CN": "说",
    "pt": "disse",
    "es": "dijo"
}

class TTS(commands.Cog):
    def reset(self):
        self.queue = []
        
    def readSettings(self):
        with open('serverSettings.json', 'r') as f:
            self.settings = json.load(f)

    def __init__(self, client):
        self.client = client
        self.queue = []
        self.lastAuthor = None
        self.lastAuthorTime = 0
        self.readSettings()

    async def autoLeave(self, ctx):
        idleTime = 0
        while ctx.voice_client:
            if len(ctx.voice_client.channel.members) < 2:
                await ctx.voice_client.disconnect()
                self.reset()
                break
            
            if not ctx.voice_client.is_playing():
                idleTime += 3
                if idleTime >= 300:
                    await ctx.voice_client.disconnect()
                    self.reset()
                    break
            else:
                idleTime = 0
            
            await asyncio.sleep(3)
        self.reset()

    async def playTTS(self, ctx):
        while self.queue:
            file = self.queue[0]
            ctx.voice_client.play(discord.FFmpegPCMAudio(f'./mp3files/{file}'), after=lambda e: self.client.loop.create_task(self.removeFile(file)))
            self.lastAuthorTime = time.time()
            while ctx.voice_client.is_playing():
                await asyncio.sleep(1)

    async def removeFile(self, file):
        try:
            os.remove(f'./mp3files/{file}')
            self.queue.remove(file)
        except:
            pass

    @commands.command(name='setLanguage', aliases=['lang', 'sl'], description="Sets the language for TTS. \nSupported languages:\n`en`: English\n `fr`: French\n `zh-CN`: Chinese\n `pt`: Portuguese\n `es`: Spanish")
    async def _setLanguage(self, ctx, lang):
        if lang not in transitionWord.keys():
            await ctx.send(f"Invalid language {lang}")
            return
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)
        settings[str(ctx.guild.id)]["language"] = lang
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"Language set to {lang}")
        self.settings = settings

    @commands.command(name='setPrefix', aliases=['prefix', 'sp'], description="Change custom bot prefix.")
    async def _setPrefix(self, ctx, prefix):
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)
        settings[str(ctx.guild.id)]["prefix"] = prefix
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"Prefix changed to {prefix}")
        self.settings = settings

    @commands.command(name='setChannel', aliases=['channel', 'sc'], description="Change the channel to monitor for TTS messages. Use this command in the targeted text chanel.")
    async def _setChannel(self, ctx):
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)
        channel = ctx.message.channel
        settings[str(ctx.guild.id)]["channel"] = channel.id
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        await ctx.send(f"TTS channel set to #{channel.name}")
        self.settings = settings

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)
        settings.pop(str(guild.id))
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)

        s = {"prefix": ",", "language": None, "channel": None}
        
        settings[str(guild.id)] = s
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)
            
    @commands.Cog.listener()
    async def on_message(self, message):
        global botInfo, transitionWord
        try:
            serverSetting = self.settings[str(message.guild.id)]
        except KeyError:
            return
        
        if message.channel.id == serverSetting["channel"] and not message.author.bot and not message.content.startswith(serverSetting["prefix"]):
            ctx = await self.client.get_context(message)
            if ctx.author.voice is None:
                await ctx.send("Please join a voice channel first")        
                return
            elif ctx.voice_client is None:
                voice_channel = ctx.author.voice.channel
                await voice_channel.connect()
                ctx.voice_client.stop()
                self.client.loop.create_task(self.autoLeave(ctx))
            elif ctx.voice_client.channel is not ctx.author.voice.channel:
                await ctx.send("I'm already in a voice channel")
                return

            content = self.replaceInvalidContents(ctx, message.content)
            if content == "":
                return

            if time.time() - self.lastAuthorTime > 60 or not self.lastAuthor == ctx.author.display_name:
                content = ctx.author.display_name + transitionWord[serverSetting["language"]] + "," + content

            self.lastAuthor = ctx.author.display_name
            tts = gTTS(text=content, lang=serverSetting["language"])
            ttsFileName = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16)) + '.mp3'
            tts.save(f"./mp3files/{ttsFileName}")
            self.queue.append(ttsFileName)
            
            if not ctx.voice_client.is_playing():
                await self.playTTS(ctx)

    def replaceInvalidContents(self, ctx, content):
        content = re.sub(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))", '', content)
        #deletes all urls

        content = re.sub(r'<a?:\w+:\d+>', '', content)
        if content == "":
            return
        #deletes all emojies

        guild = ctx.guild
        mentions = re.findall(r'<@!?(\d+)>', content)
        if mentions:
            for mention in mentions:
                content = content.replace(f'<@{mention}>', guild.get_member(int(mention)).display_name + ',')
        #replace all user mentions to name of the user

        channels = re.findall(r'<#!?(\d+)>', content)
        if channels:
            for channel in channels:
                content = content.replace(f'<#{channel}>', guild.get_channel(int(channel)).name + ',')

        return content
        #replace all server mentions to name of the server

async def setup(client):
    await client.add_cog(TTS(client))
