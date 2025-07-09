"""Clean moderation commands cog. Provides kick, ban, timeout, purge, slowmode, lock/unlock, warn, warnings.
Fully replaces the buggy duplicate file.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional

import discord
from discord.ext import commands
from discord import app_commands

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

    async def _safe_send(self, target, embed: discord.Embed):
        """Send an embed to either a context or interaction."""
        try:
            if isinstance(target, discord.Interaction):
                if not target.response.is_done():
                    await target.response.send_message(embed=embed)
                else:
                    await target.followup.send(embed=embed)
            else:
                await target.send(embed=embed)
        except discord.Forbidden:
            try:
                text = embed.description or "error"
                if isinstance(target, discord.Interaction):
                    if not target.response.is_done():
                        await target.response.send_message(text)
                    else:
                        await target.followup.send(text)
                else:
                    await target.send(text)
            except Exception:
                pass

    # ---------- commands ----------
    @app_commands.command(name="kick", description="kick a member")
    @commands.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None):
        """kick a member"""
        try:
            await member.kick(reason=reason)
            desc = f"{member} has been kicked. reason: {reason or 'no reason provided.'}"
            embed = discord.Embed(title="kick", description=desc.lower(), color=INVIS_COLOR)
            await self._safe_send(interaction, embed)
            await self._log(interaction.guild, embed)
        except discord.Forbidden:
            await self._safe_send(interaction, discord.Embed(title="permission error", description="i don't have permission to kick.", color=INVIS_COLOR))

    @app_commands.command(name="ban", description="ban a member")
    @commands.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None):
        """ban a member"""
        try:
            await member.ban(reason=reason, delete_message_days=0)
            desc = f"{member} has been banned. reason: {reason or 'no reason provided.'}"
            embed = discord.Embed(title="ban", description=desc.lower(), color=INVIS_COLOR)
            await self._safe_send(interaction, embed)
            await self._log(interaction.guild, embed)
        except discord.Forbidden:
            await self._safe_send(interaction, discord.Embed(title="permission error", description="i don't have permission to ban.", color=INVIS_COLOR))

    @commands.command(name="massban")
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx: commands.Context, members: commands.Greedy[discord.Member]):
        """ban multiple members at once (prefix only)."""
        if not members:
            await self._safe_send(ctx, discord.Embed(title="massban", description="no members given.", color=INVIS_COLOR))
            return
        banned = 0
        for m in members:
            try:
                await m.ban(reason=f"massban by {ctx.author}", delete_message_days=0)
                banned += 1
            except discord.Forbidden:
                pass
        desc = f"banned {banned} member(s)."
        embed = discord.Embed(title="massban", description=desc, color=INVIS_COLOR)
        await self._safe_send(ctx, embed)
        await self._log(ctx.guild, embed)

    @app_commands.command(name="unban", description="unban a user by id")
    @commands.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user_obj = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user_obj)
            embed = discord.Embed(title="unban", description=f"unbanned {user_obj}.", color=INVIS_COLOR)
            await self._safe_send(interaction, embed)
            await self._log(interaction.guild, embed)
        except Exception:
            await self._safe_send(interaction, discord.Embed(title="unban", description="could not unban that user.", color=INVIS_COLOR))

    @app_commands.command(name="timeout", description="timeout (mute) a member for <minutes>")
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str | None = None):
        """timeout (mute) a member for <minutes>"""
        if not 1 <= minutes <= 43200:
            await self._safe_send(interaction, discord.Embed(title="timeout", description="minutes must be between 1 and 43200.", color=INVIS_COLOR))
            return
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=reason)
        except AttributeError:
            await member.edit(timed_out_until=until, reason=reason)
        desc = f"{member} has been timed out for {minutes} minutes."
        embed = discord.Embed(title="timeout", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)

    @app_commands.command(name="purge", description="bulk delete <count> messages (max 100)")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, count: int):
        """bulk delete <count> messages (max 100)"""
        if not 1 <= count <= 100:
            await self._safe_send(interaction, discord.Embed(title="purge", description="count must be 1-100.", color=INVIS_COLOR))
            return
        deleted = await interaction.channel.purge(limit=count + 1)
        desc = f"deleted {len(deleted)-1} messages."
        embed = discord.Embed(title="purge", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)

    @app_commands.command(name="purge_user", description="delete a user's messages (max 100)")
    @commands.has_permissions(manage_messages=True)
    async def purge_user(self, interaction: discord.Interaction, member: discord.Member, count: int):
        if not 1 <= count <= 100:
            await self._safe_send(interaction, discord.Embed(title="purge_user", description="count must be 1-100.", color=INVIS_COLOR))
            return
        def check(m: discord.Message) -> bool:
            return m.author.id == member.id
        deleted = await interaction.channel.purge(limit=count, check=check)
        desc = f"deleted {len(deleted)} messages from {member}."
        embed = discord.Embed(title="purge_user", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)

    @app_commands.command(name="slowmode", description="set channel slowmode delay (0 disables)")
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        """set channel slowmode delay (0 disables)"""
        if not 0 <= seconds <= 21600:
            await self._safe_send(interaction, discord.Embed(title="slowmode", description="seconds must be 0-21600.", color=INVIS_COLOR))
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        desc = "slowmode disabled." if seconds == 0 else f"slowmode set to {seconds} seconds."
        embed = discord.Embed(title="slowmode", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)

    @app_commands.command(name="lock", description="lock the current channel")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        """lock the current channel"""
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="lock", description="channel locked.", color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)

    @app_commands.command(name="unlock", description="unlock the current channel")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        """unlock the current channel"""
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        embed = discord.Embed(title="unlock", description="channel unlocked.", color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)

    @app_commands.command(name="modlog", description="show the moderation log channel")
    @commands.has_permissions(manage_guild=True)
    async def modlog(self, interaction: discord.Interaction):
        chan = await self._get_log_channel(interaction.guild)
        if chan:
            desc = f"logs are in {chan.mention}"
        else:
            desc = "could not create log channel."
        await self._safe_send(interaction, discord.Embed(title="modlog", description=desc, color=INVIS_COLOR))

    @app_commands.command(name="warn", description="warn a member")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        """warn a member"""
        entry = {"reason": reason.lower(), "mod": interaction.user.id, "time": datetime.datetime.utcnow().isoformat()}
        self.warnings.setdefault(str(member.id), []).append(entry)
        save_warnings(self.warnings)
        desc = f"{member.mention} has been warned: {reason}"
        embed = discord.Embed(title="warn", description=desc.lower(), color=INVIS_COLOR)
        await self._safe_send(interaction, embed)
        await self._log(interaction.guild, embed)
        try:
            await member.send(f"you were warned in {interaction.guild.name}: {reason.lower()}")
        except discord.Forbidden:
            pass

    @app_commands.command(name="warnings", description="list warnings for a member")
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        """list warnings for a member"""
        entries = self.warnings.get(str(member.id), [])
        if not entries:
            await self._safe_send(interaction, discord.Embed(title="warnings", description="no warnings found.", color=INVIS_COLOR))
            return
        lines = [f"{idx+1}. {e['reason']} (mod <@{e['mod']}>)" for idx, e in enumerate(entries)]
        embed = discord.Embed(title="warnings", description="\n".join(lines), color=INVIS_COLOR)
        await self._safe_send(interaction, embed)

    # ---------- error handler ----------
    async def cog_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            missing = ', '.join(error.missing_permissions)
            await self._safe_send(ctx, discord.Embed(title="permission denied", description=f"you need {missing} permission(s) to use that command.", color=INVIS_COLOR))
        elif isinstance(error, commands.BotMissingPermissions):
            missing = ', '.join(error.missing_permissions)
            await self._safe_send(ctx, discord.Embed(title="permission error", description=f"i'm missing the {missing} permission(s).", color=INVIS_COLOR))
        elif isinstance(error, discord.Forbidden):
            await self._safe_send(ctx, discord.Embed(title="error", description="action failed due to hierarchy or permission issues.", color=INVIS_COLOR))
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCommands(bot))
