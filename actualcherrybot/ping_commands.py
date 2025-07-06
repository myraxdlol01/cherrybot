import discord

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
from discord.ext import commands
from discord import app_commands
import time


class PingCommands(commands.Cog):
    """Simple latency check commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx: commands.Context):
        """respond with bot latency."""
        start_time = time.perf_counter()
        temp_msg = await ctx.reply("checking...", mention_author=False)
        end_time = time.perf_counter()
        rtt_ms = (end_time - start_time) * 1000

        embed = discord.Embed(
            title="pong!",
            color=INVIS_COLOR
        )
        embed.add_field(name="round-trip", value=f"{round(rtt_ms)}ms", inline=True)
        embed.add_field(name="websocket", value=f"{round(self.bot.latency*1000)}ms", inline=True)
        await temp_msg.edit(content=None, embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PingCommands(bot))
