import discord

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
from discord.ext import commands
from discord import app_commands


class GeneralCommands(commands.Cog):
    """General utility commands for the bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="invite", description="get the bot invite link")
    async def invite(self, ctx: commands.Context):
        """DMs you the OAuth2 invite link."""
        client_id = ctx.bot.user.id
        perms = 2147601408  # adjust if needed
        url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions={perms}&scope=bot%20applications.commands"
        try:
            await ctx.user.send(f"add me using this link:\n{url}")
            await ctx.reply("sent you a DM with my invite link.")
        except discord.Forbidden:
            await ctx.reply(url)

    @commands.hybrid_command(name="servercount", description="how many servers i am in")
    async def servercount(self, ctx: commands.Context):
        """shows how many servers the bot is in."""
        await ctx.reply(f"i'm currently in **{len(ctx.bot.guilds)}** servers.")

    @commands.hybrid_command(name="userinfo")
    async def userinfo(self, ctx: commands.Context, member: discord.Member | None = None):
        """show information about a user."""
        target = member or ctx.author
        joined = target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "unknown"
        created = target.created_at.strftime("%Y-%m-%d")
        embed = discord.Embed(title="userinfo", color=INVIS_COLOR)
        embed.add_field(name="id", value=str(target.id), inline=False)
        embed.add_field(name="created", value=created, inline=True)
        embed.add_field(name="joined", value=joined, inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="serverinfo")
    async def serverinfo(self, ctx: commands.Context):
        """show information about this server."""
        guild = ctx.guild
        if guild is None:
            await ctx.send(embed=discord.Embed(title="serverinfo", description="not in a server.", color=INVIS_COLOR))
            return
        embed = discord.Embed(title="serverinfo", description=guild.name, color=INVIS_COLOR)
        embed.add_field(name="id", value=str(guild.id), inline=False)
        embed.add_field(name="members", value=str(guild.member_count), inline=True)
        if guild.owner:
            embed.add_field(name="owner", value=str(guild.owner), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="about")
    async def about(self, ctx: commands.Context):
        """short info about the bot."""
        desc = "minimal discord bot with moderation and utilities."
        await ctx.send(embed=discord.Embed(title="about", description=desc, color=INVIS_COLOR))

    @app_commands.command(name="help", description="show all commands")
    async def help_command(self, ctx: discord.Interaction):
        """Shows this help message with paged embeds."""

        categories: dict[str, list[tuple[str, str]]] = {
            "fun": [],
            "security & moderation": [],
            "utilities": [],
        }
        seen: set[str] = set()
        all_commands = list(self.bot.commands) + list(self.bot.tree.walk_commands())
        for cmd in all_commands:
            if getattr(cmd, "hidden", False):
                continue
            name = f"/{cmd.qualified_name}".lower()
            if name in seen:
                continue
            seen.add(name)
            desc = (getattr(cmd, "help", None) or getattr(cmd, "description", None) or "no description provided.").lower()
            cog = getattr(cmd, "cog_name", None) or (getattr(cmd, "binding", None).__class__.__name__ if getattr(cmd, "binding", None) else "")
            if cog in ("ModerationCommands", "Security"):
                cat = "moderation"
            elif cog in ("FunCommands",):
                cat = "fun"
            else:
                cat = "utilities"
            categories.setdefault(cat, []).append((name, desc))

        embeds: list[discord.Embed] = []
        for title, items in categories.items():
            emb = discord.Embed(title=f"{title} commands", color=INVIS_COLOR)
            for n, d in items:
                emb.add_field(name=n, value=d, inline=False)
            embeds.append(emb)

        if not embeds:
            await ctx.response.send_message("no commands found.")
            return

        class Pager(discord.ui.View):
            def __init__(self, pages: list[discord.Embed]):
                super().__init__(timeout=60)
                self.pages = pages
                self.idx = 0

            async def _update(self, interaction: discord.Interaction):
                await interaction.response.edit_message(embed=self.pages[self.idx], view=self)

            @discord.ui.button(label="prev", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
                self.idx = (self.idx - 1) % len(self.pages)
                await self._update(interaction)

            @discord.ui.button(label="next", style=discord.ButtonStyle.secondary)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
                self.idx = (self.idx + 1) % len(self.pages)
                await self._update(interaction)

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True

        view = Pager(embeds)
        await ctx.response.send_message(embed=embeds[0], view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCommands(bot))
