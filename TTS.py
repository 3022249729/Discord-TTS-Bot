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
from langs import languages

class TTS(commands.Cog):
    def reset(self):
        self.lastAuthor = None
        self.lastAuthorTime = 0
        self.ignoreTTS = False
        self.readSettings()
        self.deleteQueue()
        
    def readSettings(self):
        with open('serverSettings.json', 'r') as f:
            self.settings = json.load(f)

    def deleteQueue(self):
        while self.queue:
            try:
                os.remove(f'./mp3files/{self.queue.pop(0)}')
            except:
                pass
        self.queue = []
            
    def __init__(self, client):
        self.client = client
        self.queue = []
        self.lastAuthor = None
        self.lastAuthorTime = 0
        self.ignoreTTS = False
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
            try:
                while ctx.voice_client.is_playing():
                    await asyncio.sleep(1)
            except AttributeError:
                self.reset()
                return
                
    async def removeFile(self, file):
        try:
            os.remove(f'./mp3files/{file}')
            self.queue.remove(file)
        except:
            pass

    async def joinVC(self, ctx):
        if ctx.author.voice is None:
            await ctx.send("Please join a voice channel first.")        
            return
        elif ctx.voice_client is None:
            voice_channel = ctx.author.voice.channel
            await voice_channel.connect()
            ctx.voice_client.stop()
            self.client.loop.create_task(self.autoLeave(ctx))
        elif ctx.voice_client.channel is not ctx.author.voice.channel:
            await ctx.send("I'm already in a voice channel.")
            return
        
    @commands.command(name='say', aliases=['s'], description="Send a TTS message in your voice channel.")
    async def _say(self, ctx, *, content):
        try:
            serverSetting = self.settings[str(ctx.guild.id)]
        except KeyError:
            await ctx.channel.send("Server not configured, please re-invite the bot to the server while the bot is hosted.")
            return
        
        if serverSetting['language'] is None:
            await ctx.send(f"The language for TTS messages is not set, use `{serverSetting['prefix']}help lang` to get started.")
            return
        
        content = self.replaceInvalidContents(ctx, content)
        if content == "" or content == None:
            return

        if not ctx.voice_client:
            await self.joinVC(ctx)
            if not ctx.voice_client:
                return
        
        self.addTTS(ctx, content, serverSetting)    
        if not ctx.voice_client.is_playing():
            await self.playTTS(ctx)

    @commands.command(name='stop', aliases=['leave', 'dc'], description="Stops playing TTS and leave the voice channel.")
    async def _stop(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()

    @commands.command(name='setChannel', aliases=['sc'], description="Set the channel to monitor for TTS messages. Use this command in the targeted text chanel, all messages sent in this channel will convert to TTS messages.")
    async def _channel(self, ctx):
        channel = ctx.message.channel
        self.settings[str(ctx.guild.id)]['channel'] = channel.id
        with open('serverSettings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        await ctx.send(f"TTS channel set to <#{channel.id}>")
        self.readSettings()

    @commands.command(name='unsetChannel', aliases=['uc'], description="Stop monitoring messages in the configured TTS message channel.")
    async def _unsetChannel(self, ctx):
        self.settings[str(ctx.guild.id)]['channel'] = None
        with open('serverSettings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        await ctx.send(f"TTS channel cleared.")
        self.readSettings()

    @commands.command(name='language', aliases=['lang', 'sl'], description="Set the language for TTS messages.\n\nCommon languages:\n`en` - English\n`zh-CN` - Chinese (Simplified)\n`hi` - Hindi\n`es` - Spanish\n`fr` - French\n`ar` - Arabic\n`bn` - Bengali\n`ru` - Russian\n`pt` - Portuguese\n`ja` - Japanese\n`ur` - Urdu\n`ko` - Korean\n`de` - German\n`id` - Indonesian\n\nFor more supported languages, please refer to [github](https://github.com/3022249729/RenoTTS?tab=readme-ov-file#languages). ")
    async def _language(self, ctx, lang):
        if lang not in languages.keys():
            await ctx.send(f"Invalid language {lang}, use `{self.settings[str(ctx.guild.id)]['prefix']}lang` for a list of supported languages.")
            return
        self.settings[str(ctx.guild.id)]['language'] = lang
        with open('serverSettings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        await ctx.send(f"Language set to {languages[str(lang)]['name']}")
        self.readSettings()

    @commands.command(name='setPrefix', aliases=['sp'], description="Change custom bot prefix.")
    async def _prefix(self, ctx, prefix):
        self.ignoreTTS = True
        self.settings[str(ctx.guild.id)]['prefix'] = prefix
        with open('serverSettings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)
        await ctx.send(f"Prefix changed to {prefix}")
        self.readSettings()

    @commands.command(name='settings', description="Get the TTS settings for the server.")
    async def _settings(self, ctx):
        embed = discord.Embed(title="Settings")
        embed.add_field(name = 'Prefix:', value=f"`{self.settings[str(ctx.guild.id)]['prefix']}`", inline = True)
        embed.add_field(name = 'TTS Language:', value=f"`{self.settings[str(ctx.guild.id)]['language']}`", inline = True)
        embed.add_field(name = 'TTS Channel:', value=self.settingsChannelHelper(ctx.guild.id),inline=True)
        embed.set_footer(text='TTS Bot by ren.xxx', icon_url = ctx.bot.user.avatar.url)
        await ctx.send(embed=embed)

    def settingsChannelHelper(self, guild):
        if self.settings[str(guild)]['channel'] == None:
            return "None"
        else:
            return f"<#{self.settings[str(guild)]['channel']}>"

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)
        settings.pop(str(guild.id))
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        self.readSettings()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open('serverSettings.json', 'r') as f:
            settings = json.load(f)

        s = {"prefix": ".", "language": None, "channel": None}
        
        settings[str(guild.id)] = s
        with open('serverSettings.json', 'w') as f:
            json.dump(settings, f, indent=4)
        self.readSettings()
            
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.author.bot:
            try:
                serverSetting = self.settings[str(message.guild.id)]
            except KeyError:
                await message.channel.send("Server not configured, please re-invite the bot to the server while the bot is hosted.")
                return
            
            if message.channel.id == serverSetting['channel'] and not message.content.startswith(serverSetting['prefix']):
                if serverSetting['language'] is None:
                    await message.channel.send(f"The language for TTS messages is not set, use `{serverSetting['prefix']}help lang` to get started")
                    return
                if self.ignoreTTS:
                    self.ignoreTTS = False
                    return
                
                ctx = await self.client.get_context(message)

                content = self.replaceInvalidContents(ctx, message.content)
                if content == "" or content == None:
                    return

                if not ctx.voice_client:
                    await self.joinVC(ctx)
                    if not ctx.voice_client:
                        return
                
                self.addTTS(ctx, content, serverSetting)    
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
        #replace all server mentions to name of the server

        return content
        
    def addTTS(self, ctx, content, serverSetting):
        if time.time() - self.lastAuthorTime > 60 or not self.lastAuthor == ctx.author.display_name:
            content = ctx.author.display_name + languages[serverSetting['language']]['transitionWord'] + "," + content

        self.lastAuthor = ctx.author.display_name
        try:
            tts = gTTS(text=content, lang=serverSetting['language'])
        except ValueError:
            ctx.send("Language currently not supported.")
            return

        ttsFileName = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=16)) + '.mp3'
        tts.save(f"./mp3files/{ttsFileName}")
        self.queue.append(ttsFileName)

async def setup(client):
    await client.add_cog(TTS(client))
