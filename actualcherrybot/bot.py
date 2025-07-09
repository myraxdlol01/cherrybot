import os
from discord.ext import commands, tasks
import discord

INVIS_COLOR = discord.Color.from_rgb(47, 49, 54)
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for commands




bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents, help_command=None)


@tasks.loop(seconds=5)
async def _rotate_status():
    prefix = "/"
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name=f"{len(bot.guilds)} servers"),
        discord.Activity(type=discord.ActivityType.listening, name=f"{prefix}help"),
        discord.Activity(type=discord.ActivityType.watching, name=f"over your server and protecting it!"),
        discord.Game("with cute cats"),
    ]
    _rotate_status.idx = (_rotate_status.idx + 1) % len(statuses)  # type: ignore
    await bot.change_presence(activity=statuses[_rotate_status.idx], status=discord.Status.online)

_rotate_status.idx = -1  # type: ignore

@bot.event
async def on_ready():
    _rotate_status.start()
    print(f"{bot.user} is online and connected to Discord!")


# Extensions (cogs) to load
INITIAL_EXTENSIONS = (
    "ping_commands",
    "commands",  # generic commands cog
    "fun_commands",  # fun and utility
    "timezone_commands",  # timezone management
    "moderation_clean",  # moderation
    "security_commands",  # anti-raid / anti-nuke
    "premium_cog",  # premium management
)


@bot.event
async def setup_hook():
    """Called by discord.py before the bot becomes ready.
    We load our extensions here because `load_extension` is async in v2.x."""
    for ext in INITIAL_EXTENSIONS:
        try:
            await bot.load_extension(ext)
            print(f"Loaded extension: {ext}")
        except Exception as e:
            print(f"Failed to load extension {ext}: {e}")

    # after all extensions loaded, sync application (slash) commands once
    synced = await bot.tree.sync()
    print(f"synced {len(synced)} slash commands")


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    # let local cog handler run first
    if hasattr(ctx.command, 'on_error'):
        return

    emb = discord.Embed(color=INVIS_COLOR)
    if isinstance(error, commands.CommandNotFound):
        return  # silently ignore unknown commands
    elif isinstance(error, commands.MissingRequiredArgument):
        emb.title = "missing argument"
        emb.description = f"usage: `!{ctx.command.qualified_name} {ctx.command.signature}`"
    elif isinstance(error, commands.BadArgument):
        emb.title = "bad argument"
        emb.description = str(error).lower()
    elif isinstance(error, commands.MissingPermissions):
        miss = ', '.join(error.missing_permissions)
        emb.title = "permission denied"
        emb.description = f"you need {miss} permission(s) to use that command."
    elif isinstance(error, commands.BotMissingPermissions):
        miss = ', '.join(error.missing_permissions)
        emb.title = "permission error"
        emb.description = f"i'm missing the {miss} permission(s)."
    elif isinstance(error, commands.CommandOnCooldown):
        emb.title = "slow down"
        emb.description = f"this command is on cooldown for {error.retry_after:.1f}s."
    else:
        emb.title = "error"
        emb.description = (
            str(error).lower() if str(error) else "an unexpected error occurred."
        )
    try:
        await ctx.send(embed=emb)
    except discord.Forbidden:
        pass  # can't send anything


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not found in environment or .env file")
    bot.run(TOKEN)
