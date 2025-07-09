"""Premium management cog for cherrybot.

Commands (owner only):
  /premium add_user <user>
  /premium remove_user <user>
  /premium info – generic info visible to everyone
"""
from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands, Interaction

from premium_utils import (
    is_premium_user,
    is_premium_guild,
    grant_premium_user,
    revoke_premium_user,
)


# check decorator ------------------------------------------------------------

def premium_only():
    def predicate(inter: Interaction):
        return is_premium_user(inter.user.id) or is_premium_guild(inter.guild_id)

    return app_commands.check(predicate)


# main cog -------------------------------------------------------------------

class PremiumAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # root group
    premium = app_commands.Group(name="premium", description="premium functions")

    # public command
    @premium.command(name="info", description="learn about cherrybot premium")
    async def info(self, inter: Interaction):
        emb = discord.Embed(
            title="cherrybot premium",
            description=(
                "support hosting and unlock perks like /cat_gif, custom embed colours, and more.\n"
                "visit https://your-site/premium to subscribe."
            ),
            colour=discord.Colour.magenta(),
        )
        await inter.response.send_message(embed=emb, ephemeral=True)

    # owner-only subcommands --------------------------------------------------

    @premium.command(name="add_user", description="grant premium to a user")
    @app_commands.describe(user="user to grant")
    @commands.is_owner()
    async def add_user(self, inter: Interaction, user: discord.User):
        await grant_premium_user(self.bot, user.id)
        await inter.response.send_message(f"{user.mention} is now premium.")

    @premium.command(name="remove_user", description="revoke premium from a user")
    @app_commands.describe(user="user to revoke")
    @commands.is_owner()
    async def remove_user(self, inter: Interaction, user: discord.User):
        revoke_premium_user(user.id)
        await inter.response.send_message(f"{user.mention} premium revoked.")


async def setup(bot: commands.Bot):
    await bot.add_cog(PremiumAdmin(bot))
