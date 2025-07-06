"""Utility functions and cache for cherrybot premium support.

Premium data is stored in a simple JSON file with two arrays:
    {
        "users":  [<discord_user_ids>],
        "guilds": [<discord_guild_ids>]
    }

Functions are provided to load / save this data and to grant / revoke
premium.  When a user is granted premium the helper optionally assigns
(or creates) a `premium` role in any mutual guilds.

The module keeps an in-memory cache so disk reads are minimal.
"""
from __future__ import annotations

import json
import pathlib
from typing import List, Dict

import discord
from discord.ext import commands

__all__ = [
    "PREMIUM_JSON",
    "premium_cache",
    "load_premium",
    "save_premium",
    "is_premium_user",
    "is_premium_guild",
    "grant_premium_user",
    "revoke_premium_user",
]

PREMIUM_JSON = pathlib.Path("premium.json")

# ---------------------------------------------------------------------------
# persistence helpers
# ---------------------------------------------------------------------------

def _default_data() -> Dict[str, List[int]]:
    return {"users": [], "guilds": []}


def load_premium() -> Dict[str, List[int]]:
    if PREMIUM_JSON.exists():
        try:
            return json.loads(PREMIUM_JSON.read_text())
        except Exception:
            # corrupt? back up and start fresh
            PREMIUM_JSON.rename(PREMIUM_JSON.with_suffix(".bak"))
    return _default_data()


def save_premium(data: Dict[str, List[int]]):
    PREMIUM_JSON.write_text(json.dumps(data, indent=2))


premium_cache: Dict[str, List[int]] = load_premium()

# ---------------------------------------------------------------------------
# query helpers
# ---------------------------------------------------------------------------

def is_premium_user(user_id: int) -> bool:
    return user_id in premium_cache["users"]


def is_premium_guild(guild_id: int | None) -> bool:
    return guild_id is not None and guild_id in premium_cache["guilds"]

# ---------------------------------------------------------------------------
# mutation helpers – keep cache + disk in sync and optionally give roles
# ---------------------------------------------------------------------------

aSYNC_ROLE_NAME = "premium"  # role name in guilds

async def _ensure_premium_role(guild: discord.Guild) -> discord.Role | None:
    """Return existing premium role or attempt to create it."""
    role = discord.utils.get(guild.roles, name=aSYNC_ROLE_NAME)
    if role is None:
        try:
            role = await guild.create_role(name=aSYNC_ROLE_NAME, colour=discord.Colour.purple(), reason="premium role")
        except discord.Forbidden:
            return None
    return role


async def _assign_role(bot: commands.Bot, user_id: int):
    for guild in bot.guilds:
        member = guild.get_member(user_id)
        if not member:
            continue
        role = await _ensure_premium_role(guild)
        if role and role not in member.roles:
            try:
                await member.add_roles(role, reason="premium purchase")
            except discord.Forbidden:
                pass


async def grant_premium_user(bot: commands.Bot, user_id: int):
    if user_id not in premium_cache["users"]:
        premium_cache["users"].append(user_id)
        save_premium(premium_cache)
    await _assign_role(bot, user_id)


def revoke_premium_user(user_id: int):
    if user_id in premium_cache["users"]:
        premium_cache["users"].remove(user_id)
        save_premium(premium_cache)
