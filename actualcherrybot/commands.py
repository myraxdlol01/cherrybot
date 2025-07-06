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

    @commands.hybrid_command(name="servercount", description="how many servers I am in")
    async def servercount(self, ctx: commands.Context):
        """shows how many servers the bot is in."""
        await ctx.response.send_message(f"i'm currently in **{len(ctx.bot.guilds)}** servers.")

    @commands.command(name="about")
    async def about(self, ctx: commands.Context):
        """Provides information about the bot."""
        embed = discord.Embed(title="about", description="bot made by cherieware's lead developer. this cozy nyan cat bot is here to make your day brighter! featuring many commands like 'ping' (shows latency), 'about' (info about the bot), and 'help' (lists all commands).", color=INVIS_COLOR)
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="help", description="show all commands")
    async def help_command(self, ctx: discord.Interaction):
        """Shows this help message with paged embeds."""

        # build embeds grouped by category
        embeds: list[discord.Embed] = []
        categories: dict[str, list[tuple[str, str]]] = {
            "fun": [],
            "security & moderation": [],
            "utilities": [],
        }
        for cmd in self.bot.commands:
            if cmd.hidden:
                continue
            desc = (cmd.help or cmd.description or "no description provided.").lower()
            name = f"/{cmd.qualified_name}".lower()
            cog = cmd.cog_name or ""
            if cog in ("FunCommands",):
                categories["fun"].append((name, desc))
            elif cog in ("ModerationCommands", "Moderation", "Security") or name.startswith("z!securitysetup"):
                categories["security & moderation"].append((name, desc))
            else:
                categories["utilities"].append((name, desc))

        for title, items in categories.items():
            if not items:
                continue
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

            @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
                self.idx = (self.idx - 1) % len(self.pages)
                await self._update(interaction)

            @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
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
