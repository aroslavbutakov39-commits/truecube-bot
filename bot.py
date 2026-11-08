import asyncio
import discord
from discord.ext import commands
import config

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

async def load_extensions():
    await bot.load_extension("cogs.events")
    await bot.load_extension("cogs.general")
    await bot.load_extension("cogs.moderation")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
