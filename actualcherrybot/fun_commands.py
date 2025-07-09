"""minimal fun and utility commands: uptime, weather, remind, define, 8ball, coinflip, roll, choose, meme, avatar, cat."""
import random
import datetime
import asyncio
from typing import Optional

import discord

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
from discord.ext import commands
from discord import app_commands
import aiohttp


EIGHT_BALL_RESPONSES = [
    "yes", "no", "maybe", "ask again later", "absolutely", "unlikely", "definitely", "could be", "not sure", "for sure"
]

CAT_ENDPOINT = "https://cataas.com/cat"
WEATHER_ENDPOINT = "https://wttr.in/{city}?format=j1"


class FunCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time: datetime.datetime = datetime.datetime.utcnow()

    async def cog_load(self):
        # create a single aiohttp session for reuse
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # uptime command
    @commands.hybrid_command(name="uptime")
    async def uptime(self, ctx: commands.Context):
        """show how long the bot has been online."""
        delta: datetime.timedelta = datetime.datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        embed = discord.Embed(title="uptime", description=uptime_str, color=INVIS_COLOR)
        await ctx.send(embed=embed)


    # 8ball command
    @commands.hybrid_command(name="8ball")
    async def eight_ball(self, ctx: commands.Context, *, question: str | None = None):
        """magic 8-ball response."""
        if question is None:
            embed = discord.Embed(title="8ball", description="ask me a yes/no question like '/8ball will it rain today?'", color=INVIS_COLOR)
            await ctx.send(embed=embed)
            return
        response = random.choice(EIGHT_BALL_RESPONSES)
        embed = discord.Embed(title="8ball", description=response, color=INVIS_COLOR)
        await ctx.send(embed=embed)

    # weather command
    @commands.hybrid_command(name="weather")
    async def weather(self, ctx: commands.Context, *, city: str):
        """show current weather for a city (uses wttr.in)."""
        url = WEATHER_ENDPOINT.format(city=city)
        async with self.session.get(url) as resp:
            if resp.status != 200:
                embed = discord.Embed(title="weather", description="could not fetch weather right now.", color=discord.Color.red())
                await ctx.send(embed=embed)
                return
            data = await resp.json()
        try:
            current = data["current_condition"][0]
            temp_c = current["temp_C"]
            feels_c = current["FeelsLikeC"]
            temp_f = current.get("temp_F")
            feels_f = current.get("FeelsLikeF")
            condition = current["weatherDesc"][0]["value"].lower()
            desc = (
                f"{city.lower()}: {temp_c}°c/{temp_f}°f, feels like {feels_c}°c/{feels_f}°f, {condition}"
            )
        except (KeyError, IndexError):
            desc = "unexpected response received."
        embed = discord.Embed(title="weather", description=desc, color=INVIS_COLOR)
        await ctx.send(embed=embed)

    # remind command
    @commands.hybrid_command(name="remind")
    async def remind(self, ctx: commands.Context, minutes: int, *, text: str):
        """dm you after <minutes> with <text>."""
        if minutes <= 0 or minutes > 60*24:
            await ctx.send(embed=discord.Embed(title="remind", description="minutes must be between 1 and 1440.", color=INVIS_COLOR))
            return
        confirm = discord.Embed(title="remind", description=f"i'll remind you in {minutes} minutes.", color=INVIS_COLOR)
        await ctx.send(embed=confirm)
        async def _wait_and_dm():
            await asyncio.sleep(minutes*60)
            try:
                await ctx.author.send(f"reminder: {text.lower()}")
            except discord.Forbidden:
                pass
        asyncio.create_task(_wait_and_dm())

    # define command
    @commands.hybrid_command(name="define")
    async def define(self, ctx: commands.Context, word: str):
        """fetch a dictionary definition."""
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                await ctx.send(embed=discord.Embed(title="define", description="could not find that word.", color=INVIS_COLOR))
                return
            data = await resp.json()
        try:
            meaning = data[0]["meanings"][0]["definitions"][0]["definition"].lower()
            description = f"{word.lower()}: {meaning}"
        except (KeyError, IndexError):
            description = "unexpected response."
        await ctx.send(embed=discord.Embed(title="define", description=description, color=INVIS_COLOR))


        # coinflip command
    @commands.hybrid_command(name="coinflip", description="flip a coin")
    async def coinflip(self, ctx: commands.Context):
        """flip a coin and return heads or tails."""
        result = random.choice(["heads", "tails"])
        embed = discord.Embed(title="coinflip", description=result, color=INVIS_COLOR)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="roll")
    async def roll(self, ctx: commands.Context, sides: int = 6):
        """roll a dice with <sides> faces (2-100)."""
        if not 2 <= sides <= 100:
            await ctx.send(embed=discord.Embed(title="roll", description="sides must be 2-100.", color=INVIS_COLOR))
            return
        result = random.randint(1, sides)
        embed = discord.Embed(title="roll", description=f"you rolled {result} on a d{sides}.", color=INVIS_COLOR)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="choose")
    async def choose(self, ctx: commands.Context, *, options: str):
        """pick a random option from a | separated list."""
        items = [o.strip() for o in options.split("|") if o.strip()]
        if len(items) < 2:
            await ctx.send(embed=discord.Embed(title="choose", description="provide at least two options separated by |", color=INVIS_COLOR))
            return
        choice = random.choice(items)
        embed = discord.Embed(title="choose", description=f"i pick {choice.lower()}.", color=INVIS_COLOR)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="meme")
    async def meme(self, ctx: commands.Context):
        """send a random meme."""
        async with self.session.get("https://meme-api.com/gimme") as resp:
            if resp.status != 200:
                await ctx.send(embed=discord.Embed(title="meme", description="could not fetch a meme.", color=INVIS_COLOR))
                return
            data = await resp.json()
        title = str(data.get("title", "meme")).lower()
        image_url = data.get("url")
        embed = discord.Embed(title="meme", description=title, color=INVIS_COLOR)
        if image_url:
            embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    # avatar command
    @commands.hybrid_command(name="avatar", description="show a user avatar")
    async def avatar(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """show user's avatar."""
        target = member or ctx.author
        embed = discord.Embed(title="avatar", description=str(target), color=INVIS_COLOR)
        embed.set_image(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    # cat command
    @commands.hybrid_command(name="cat")
    async def cat(self, ctx: commands.Context):
        """send a random cat picture."""
        # we can simply point embed image to cataas endpoint which returns random cat image
        embed = discord.Embed(title="cat", color=INVIS_COLOR)
        embed.set_image(url=f"{CAT_ENDPOINT}?{random.randint(1,999999)}")  # random query to avoid cache
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))
