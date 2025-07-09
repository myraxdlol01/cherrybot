"""timezone utilities for setting and viewing your timezone."""
import json
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Dict

import discord

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
from discord.ext import commands
from discord import app_commands


STORAGE_FILE = Path(__file__).with_name("timezones.json")

# common shorthand aliases -> iana timezone
ALIASES = {
    # north america
    "est": "America/New_York",
    "edt": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "utc": "UTC",
    "gmt": "Etc/GMT",
    # western europe
    "bst": "Europe/London",
    "cet": "Europe/Paris",
    "cest": "Europe/Paris",
    "eet": "Europe/Athens",
    "eest": "Europe/Athens",
    # africa
    "sast": "Africa/Johannesburg",
    "wat": "Africa/Lagos",
    "cat": "Africa/Harare",
    "eat": "Africa/Nairobi",
    # asia
    "ist": "Asia/Kolkata",
    "jst": "Asia/Tokyo",
    "kst": "Asia/Seoul",
    "gst": "Asia/Dubai",
    # australia / oceania
    "aest": "Australia/Sydney",
    "acst": "Australia/Adelaide",
    "awst": "Australia/Perth",
}


def load_timezones() -> Dict[str, str]:
    if STORAGE_FILE.exists():
        try:
            return json.loads(STORAGE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_timezones(data: Dict[str, str]):
    STORAGE_FILE.write_text(json.dumps(data))


class TimezoneCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_zones: Dict[str, str] = load_timezones()

    # root tz command
    @commands.hybrid_group(name="tz", invoke_without_command=True)
    async def tz(self, ctx: commands.Context):
        """show your saved timezone and current time."""
        user_id = str(ctx.author.id)
        zone_name = self.user_zones.get(user_id)
        if not zone_name:
            embed = discord.Embed(title="timezone", description="no timezone saved. use '/tz set <zone>' to save yours.", color=INVIS_COLOR)
            await ctx.send(embed=embed)
            return
        try:
            tzinfo = ZoneInfo(zone_name)
            now = datetime.datetime.now(tzinfo).strftime("%Y-%m-%d %I:%M:%S %p")
            desc = f"your timezone is set to {zone_name.lower()}. current time there is {now}."
            embed = discord.Embed(title="timezone", description=desc, color=INVIS_COLOR)
            await ctx.send(embed=embed)
        except ZoneInfoNotFoundError:
            embed = discord.Embed(title="timezone", description="saved timezone seems invalid. please change it with '/tz change <zone>'.", color=INVIS_COLOR)
            await ctx.send(embed=embed)

    # set subcommand
    @tz.command(name="set")
    async def tz_set(self, ctx: commands.Context, zone: str):
        """save your timezone (first time)."""
        user_id = str(ctx.author.id)
        if user_id in self.user_zones:
            embed = discord.Embed(title="timezone", description="timezone already set. use '/tz change <zone>' to update it.", color=INVIS_COLOR)
            await ctx.send(embed=embed)
            return
        await self._update_timezone(ctx, user_id, zone, new=True)

    # supported subcommand
    @tz.command(name="current")
    async def tz_current(self, ctx: commands.Context):
        """show your saved timezone."""
        user_id = str(ctx.author.id)
        zone = self.user_zones.get(user_id)
        if not zone:
            await ctx.send(embed=discord.Embed(title="timezone", description="no timezone set. use /tz set <zone> first.", color=INVIS_COLOR))
            return
        embed = discord.Embed(title="timezone", description=f"your timezone is set to {zone}.", color=INVIS_COLOR)
        await ctx.send(embed=embed)

    @tz.command(name="supported")
    async def tz_supported(self, ctx: commands.Context):
        """list all supported timezone aliases."""
        lines = [f"{alias} → {iana}".lower() for alias, iana in sorted(ALIASES.items())]
        description = "\n".join(lines)
        embed = discord.Embed(title="supported timezones", description=description, color=INVIS_COLOR)
        await ctx.send(embed=embed)

    # change subcommand
    @tz.command(name="change")
    async def tz_change(self, ctx: commands.Context, zone: str):
        """change existing timezone."""
        user_id = str(ctx.author.id)
        await self._update_timezone(ctx, user_id, zone, new=False)

    async def _update_timezone(self, ctx: commands.Context, user_id: str, zone: str, *, new: bool):
        zone_original = zone
        zone = zone.lower()
        zone = ALIASES.get(zone, zone)  # map alias if exists
        try:
            ZoneInfo(zone)  # validate
        except ZoneInfoNotFoundError:
            embed = discord.Embed(title="timezone", description="unknown timezone. please provide a valid iana timezone like 'america/new_york' or a common alias like 'est', 'utc'.", color=INVIS_COLOR)
            await ctx.send(embed=embed)
            return
        self.user_zones[user_id] = zone
        save_timezones(self.user_zones)

        action = "saved" if new else "updated"
        now = datetime.datetime.now(ZoneInfo(zone)).strftime("%Y-%m-%d %I:%M:%S %p")
        desc = f"timezone {action}. set to {zone.lower()}. current time there is {now}."
        embed = discord.Embed(title="timezone", description=desc, color=INVIS_COLOR)
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TimezoneCommands(bot))
