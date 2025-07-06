"""moderation commands cog: kick, ban, timeout, purge, slowmode, lock/unlock, warn (with storage)"""

import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord.ext import commands

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
STORAGE_FILE = Path(__file__).with_name("warnings.json")
TEXT_LOG_NAMES = ("modlogs", "mod-logs")


def load_warnings() -> Dict[str, List[dict]]:
    if STORAGE_FILE.exists():
        try:
            return json.loads(STORAGE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_warnings(data: Dict[str, List[dict]]):
    STORAGE_FILE.write_text(json.dumps(data))


class ModerationCommands(commands.Cog):
    """Moderation commands with logging and graceful error handling."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warnings: Dict[str, List[dict]] = load_warnings()

    # ---------- helpers ----------
    async def _get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Return (or create) a #modlogs channel."""
        for name in TEXT_LOG_NAMES:
            chan = discord.utils.get(guild.text_channels, name=name)
            if chan:
                return chan
        try:
            return await guild.create_text_channel("modlogs")
        except Exception:
            return None

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        chan = await self._get_log_channel(guild)
        if chan:
            try:
                await chan.send(embed=embed)
            except Exception:
                pass

    async def _safe_send(self, ctx: commands.Context, embed: discord.Embed):
        """Try to send embed, fallback to text on failure."""
        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            try:
                await ctx.send(embed.description or "error")
            except Exception:
                pass

    # ---------- commands ----------
    @commands.has_permissions(kick_members=True)
    @commands.command(name="kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
        """kick a member."""
        try:
            await member.kick(reason=reason)
            desc = f"{member} has been kicked. reason: {reason or 'no reason provided.'}"
            embed = discord.Embed(title="kick", description=desc.lower(), color=INVIS_COLOR)
            await self._safe_send(ctx, embed)
            await self._log(ctx.guild, embed)
        except discord.Forbidden:
            await self._safe_send(ctx, discord.Embed(title="permission error", description="i don't have permission to kick.", color=INVIS_COLOR))

    @commands.has_permissions(ban_members=True)
    @commands.command(name="ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
        """ban a member."""
        try:
            await member.ban(reason=reason, delete_message_days=0)
            desc = f"{member} has been banned. reason: {reason or 'no reason provided.'}"
            embed = discord.Embed(title="ban", description=desc.lower(), color=INVIS_COLOR)
            await self._safe_send(ctx, embed)
            await self._log(ctx.guild, embed)
        except discord.Forbidden:
            await self._safe_send(ctx, discord.Embed(title="permission error", description="i don't have permission to ban.", color=INVIS_COLOR))

    @commands.has_permissions(moderate_members=True)
    @commands.command(name="timeout")
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str | None = None):
        """timeout (mute) a member for <minutes>."""
        if not 1 <= minutes <= 43200:
            await self._safe_send(ctx, discord.Embed(title="timeout", description="minutes must be between 1 and 43200.", color=INVIS_COLOR))
            return
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=reason)
        except AttributeError:
            await member.edit(timed_out_until=until, reason=reason)
        desc = f"{member} has been timed out for {minutes} minutes."
        embed = discord.Embed(title="timeout", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @commands.has_permissions(manage_messages=True)
    @commands.command(name="purge")
    async def purge(self, ctx: commands.Context, count: int):
        """bulk delete <count> messages (max 100)."""
        if not 1 <= count <= 100:
            await self._safe_send(ctx, discord.Embed(title="purge", description="count must be 1-100.", color=INVIS_COLOR))
            return
        deleted = await ctx.channel.purge(limit=count + 1)  # include command message
        desc = f"deleted {len(deleted) - 1} messages."
        embed = discord.Embed(title="purge", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="slowmode")
    async def slowmode(self, ctx: commands.Context, seconds: int):
        """set channel slowmode (0 disables)."""
        if not 0 <= seconds <= 21600:
            await self._safe_send(ctx, discord.Embed(title="slowmode", description="seconds must be 0-21600.", color=INVIS_COLOR))
            return
        await ctx.channel.edit(slowmode_delay=seconds)
        desc = "slowmode disabled." if seconds == 0 else f"slowmode set to {seconds} seconds."
        embed = discord.Embed(title="slowmode", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="lock")
    async def lock(self, ctx: commands.Context):
        """lock the current channel."""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="lock", description="channel locked.", color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="unlock")
    async def unlock(self, ctx: commands.Context):
        """unlock the current channel."""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="unlock", description="channel unlocked.", color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @commands.has_permissions(manage_messages=True)
    @commands.command(name="warn")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str):
        """warn a member."""
        entry = {"reason": reason.lower(), "mod": ctx.author.id, "time": datetime.datetime.utcnow().isoformat()}
        self.warnings.setdefault(str(member.id), []).append(entry)
        save_warnings(self.warnings)
        desc = f"{member.mention} has been warned: {reason}"
        embed = discord.Embed(title="warn", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)
        try:
            await member.send(f"⚠️ you were warned in {ctx.guild.name}: {reason.lower()}")
        except discord.Forbidden:
            pass

    @commands.has_permissions(manage_messages=True)
    @commands.command(name="warnings")
    async def warnings(self, ctx: commands.Context, member: discord.Member):
        """list warnings for a member."""
        entries = self.warnings.get(str(member.id), [])
        if not entries:
            await self._safe_send(ctx, discord.Embed(title="warnings", description="no warnings found.", color=INVIS_COLOR))
            return
        lines = [f"{idx+1}. {e['reason']} (mod <@{e['mod']}>)" for idx, e in enumerate(entries)]
        embed = discord.Embed(title="warnings", description="\n".join(lines), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)

    # ---------- cog-level error handler ----------
    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            missing = ', '.join(error.missing_permissions)
            await self._safe_send(ctx, discord.Embed(title="permission error", description=f"i don't have the permission to {missing}.", color=INVIS_COLOR))
        elif isinstance(error, discord.Forbidden):
            await self._safe_send(ctx, discord.Embed(title="error", description="i don't have enough permissions to perform that.", color=INVIS_COLOR))
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCommands(bot))
import discord
from discord.ext import commands

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
STORAGE_FILE = Path(__file__).with_name("warnings.json")


def load_warnings() -> Dict[str, List[dict]]:
    if STORAGE_FILE.exists():
        try:
            return json.loads(STORAGE_FILE.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def save_warnings(data: Dict[str, List[dict]]):
    STORAGE_FILE.write_text(json.dumps(data))



    async def _get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        """find or create a modlog channel"""
        for name in TEXT_LOG_NAMES:
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel:
                return channel
        # create channel
        try:
            return await guild.create_text_channel("modlogs")
        except Exception:
            return None

        async def _safe_send(self, ctx: commands.Context, embed: discord.Embed):
        try:
            await ctx.send(embed=embed)
        except discord.Forbidden:
            # fallback to plain text
            await ctx.send(embed.description if embed.description else "oops, couldn't send embed.")

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        channel = await self._get_log_channel(guild)
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception:
                pass
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.warnings: Dict[str, List[dict]] = load_warnings()

    # kick command
    @commands.has_permissions(kick_members=True)
    @commands.command(name="kick")
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
        """kick a member."""
        await member.kick(reason=reason)
        desc = f"{member.name}#{member.discriminator} has been kicked. reason: {reason or 'no reason provided.'}"
        embed = discord.Embed(title="kick", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    # ban command
    @commands.has_permissions(ban_members=True)
    @commands.command(name="ban")
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str | None = None):
        """ban a member."""
        await member.ban(reason=reason, delete_message_days=0)
        desc = f"{member.name}#{member.discriminator} has been banned. reason: {reason or 'no reason provided.'}"
        embed = discord.Embed(title="ban", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    # timeout command
    @commands.has_permissions(moderate_members=True)
    @commands.command(name="timeout")
    async def timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str | None = None):
        """timeout (mute) a member for <minutes>."""
        if minutes <= 0 or minutes > 43200:  # max 30 days
            await self._safe_send(ctx, discord.Embed(title="timeout", description="minutes must be between 1 and 43200.", color=INVIS_COLOR))
            return
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=reason)
        except AttributeError:
            # older discord.py versions use edit
            await member.edit(timed_out_until=until, reason=reason)
        desc = f"{member.name}#{member.discriminator} has been timed out for {minutes} minutes."
        embed = discord.Embed(title="timeout", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    # purge command
    @commands.has_permissions(manage_messages=True)
    @commands.command(name="purge")
    async def purge(self, ctx: commands.Context, count: int):
        """bulk delete <count> messages (max 100)."""
        if count <= 0 or count > 100:
            await self._safe_send(ctx, discord.Embed(title="purge", description="count must be 1-100.", color=INVIS_COLOR))
            return
        deleted = await ctx.channel.purge(limit=count + 1)  # include command message
        desc = f"deleted {len(deleted)-1} messages."
        embed = discord.Embed(title="purge", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    # slowmode command
    @commands.has_permissions(manage_channels=True)
    @commands.command(name="slowmode")
    async def slowmode(self, ctx: commands.Context, seconds: int):
        """set channel slowmode (0 disables)."""
        if seconds < 0 or seconds > 21600:  # 6 hours
            await self._safe_send(ctx, discord.Embed(title="slowmode", description="seconds must be 0-21600.", color=INVIS_COLOR))
            return
        await ctx.channel.edit(slowmode_delay=seconds)
        desc = "slowmode disabled." if seconds == 0 else f"slowmode set to {seconds} seconds."
        embed = discord.Embed(title="slowmode", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    # lock / unlock channel
    @commands.has_permissions(manage_channels=True)
    @commands.command(name="lock")
    async def lock(self, ctx: commands.Context):
        """lock the current channel (disallow @everyone to speak)."""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="lock", description="channel locked.", color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="unlock")
    async def unlock(self, ctx: commands.Context):
        """unlock the current channel."""
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None  # reset to default
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="unlock", description="channel unlocked.", color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    # warn command
    @commands.has_permissions(manage_messages=True)
    @commands.command(name="warn")
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str):
        """warn a member."""
        entry = {"reason": reason.lower(), "mod": ctx.author.id, "time": datetime.datetime.utcnow().isoformat()}
        self.warnings.setdefault(str(member.id), []).append(entry)
        save_warnings(self.warnings)
        desc = f"{member.mention} has been warned: {reason}"
        await ctx.send(embed=discord.Embed(title="warn", description=desc.lower(), color=INVIS_COLOR))
        try:
            await member.send(f"⚠️ you were warned in {ctx.guild.name}: {reason.lower()}")
        except discord.Forbidden:
            pass

    @commands.has_permissions(manage_messages=True)
    @commands.command(name="warnings")
        async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            missing = ', '.join(error.missing_permissions)
            msg = f"i don't have the permission to {missing}."
            await self._safe_send(ctx, discord.Embed(title="permission error", description=msg, color=INVIS_COLOR))
        elif isinstance(error, discord.Forbidden):
            await self._safe_send(ctx, discord.Embed(title="error", description="i don't have enough permissions to perform that.", color=INVIS_COLOR))
        else:
            raise error  # re-raise for global handler or logs

    async def warnings(self, ctx: commands.Context, member: discord.Member):
        """list warnings for a member."""
        entries = self.warnings.get(str(member.id), [])
        if not entries:
            await self._safe_send(ctx, discord.Embed(title="warnings", description="no warnings found.", color=INVIS_COLOR))
            return
        lines = [f"{idx+1}. {e['reason']} (mod <@{e['mod']}>)" for idx, e in enumerate(entries)]
        embed = discord.Embed(title="warnings", description="\n".join(lines), color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCommands(bot))
