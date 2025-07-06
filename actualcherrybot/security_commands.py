"""anti-nuke / anti-raid protection cog.
monitors destructive actions and mass joins to auto-mitigate attacks.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import datetime
from collections import defaultdict, deque
from typing import Deque, Dict, List

import discord
from discord.ext import commands
from discord import app_commands

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)

# CONFIGURABLE THRESHOLDS
JOIN_THRESHOLD = 6            # joins within window triggers raid mode
JOIN_WINDOW = 10              # seconds

CHANNEL_DEL_THRESHOLD = 3     # deletions within window triggers ban
ROLE_DEL_THRESHOLD = 3        # role deletions within window triggers ban
DEL_WINDOW = 30               # seconds

TEXT_LOG_NAMES = ("modlogs", "mod-logs")


class Security(commands.Cog):
    # ---------- internal logging helpers ----------
    async def _get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
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

    # ---------------------------------------------
    ENABLE_FILE = Path(__file__).with_name("security_enabled.json")
    """Passive anti-nuke & anti-raid monitoring."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled_guilds: set[int] = self._load_enabled()
        # track join timestamps per guild
        self.joins: Dict[int, Deque[float]] = defaultdict(lambda: deque(maxlen=50))
        # track destructive action counts: {(guild_id, user_id, action): deque[timestamps]}
        self.actions: Dict[tuple, Deque[float]] = defaultdict(lambda: deque(maxlen=10))

    # -------- HELPER PERSISTENCE --------
    def _load_enabled(self) -> set[int]:
        if self.ENABLE_FILE.exists():
            try:
                return set(json.loads(self.ENABLE_FILE.read_text()))
            except Exception:
                pass
        return set()

    def _save_enabled(self):
        self.ENABLE_FILE.write_text(json.dumps(list(self.enabled_guilds)))

    # -------- RAID JOIN DETECTION --------
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id not in self.enabled_guilds:
            return
        now = self._now()
        dq = self.joins[member.guild.id]
        dq.append(now)
        # count joins in window
        recent = [t for t in dq if now - t <= JOIN_WINDOW]
        if len(recent) >= JOIN_THRESHOLD:
            await self._activate_raid_mode(member.guild)

    async def _activate_raid_mode(self, guild: discord.Guild):
        # lock @everyone send perms and enable 30s slowmode on all text channels
        for channel in guild.text_channels:
            try:
                await channel.edit(slowmode_delay=30)
                overwrite = channel.overwrites_for(guild.default_role)
                if overwrite.send_messages is not False:
                    overwrite.send_messages = False
                    await channel.set_permissions(guild.default_role, overwrite=overwrite)
            except Exception:
                pass
        log = f"raid mode activated in {guild.name}: mass join detected"
        print(log)
        await self._notify_owners(guild, log)

    # -------- DESTRUCTIVE ACTIONS --------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        await self._handle_destructive_action(channel.guild, "channel_delete")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self._handle_destructive_action(role.guild, "role_delete")

    async def _handle_destructive_action(self, guild: discord.Guild, action: str):
        if guild.id not in self.enabled_guilds:
            return
        # fetch audit log entry to get executor
        try:
            entry = await guild.audit_logs(limit=1, action=getattr(discord.AuditLogAction, action)).flatten()
        except Exception:
            return
        if not entry:
            return
        entry = entry[0]
        user = entry.user
        now = self._now()
        key = (guild.id, user.id, action)
        dq = self.actions[key]
        dq.append(now)
        threshold = CHANNEL_DEL_THRESHOLD if action == "channel_delete" else ROLE_DEL_THRESHOLD
        recent = [t for t in dq if now - t <= DEL_WINDOW]
        if len(recent) >= threshold:
            try:
                await guild.ban(user, reason=f"antinuke: too many {action}s")
                log = f"banned {user} for mass {action}s"
                print(log)
                await self._notify_owners(guild, log)
            except Exception:
                pass

    # -------- UTIL --------
    async def _notify_owners(self, guild: discord.Guild, message: str):
        for owner in guild.owners if hasattr(guild, 'owners') else [guild.owner]:
            try:
                await owner.send(message)
            except Exception:
                pass

    def _now(self) -> float:
        return datetime.datetime.utcnow().timestamp()

    # OWNER COMMANDS TO TOGGLE / STATUS
    @commands.is_owner()
    @commands.hybrid_group(name="securitysetup", invoke_without_command=True)
    async def security_root(self, ctx: commands.Context):
        """show security status:"""
        desc = (
            f"raid join threshold: {JOIN_THRESHOLD}/{JOIN_WINDOW}s\n"
            f"channel delete threshold: {CHANNEL_DEL_THRESHOLD}/{DEL_WINDOW}s\n"
            f"role delete threshold: {ROLE_DEL_THRESHOLD}/{DEL_WINDOW}s"
        )
        status = "enabled" if ctx.guild.id in self.enabled_guilds else "disabled"
        await ctx.send(embed=discord.Embed(title="security", description=desc+f"\nstatus: {status}", color=INVIS_COLOR))

    @security_root.command(name="enable")
    async def security_enable(self, ctx: commands.Context):
        """enable security for this guild."""
        self.enabled_guilds.add(ctx.guild.id)
        self._save_enabled()
        await ctx.send(embed=discord.Embed(title="security", description="security enabled.", color=INVIS_COLOR))

    @security_root.command(name="disable")
    async def security_disable(self, ctx: commands.Context):
        """disable security for this guild."""
        self.enabled_guilds.discard(ctx.guild.id)
        self._save_enabled()
        await ctx.send(embed=discord.Embed(title="security", description="security disabled.", color=INVIS_COLOR))


async def setup(bot: commands.Bot):
    await bot.add_cog(Security(bot))
