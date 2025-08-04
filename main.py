import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class RiskRaiderBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Load cogs and sync slash commands."""
        cogs_to_load = ['cogs.nft_check']
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Successfully loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

async def main():
    bot = RiskRaiderBot()
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.critical("DISCORD_BOT_TOKEN not found in environment variables!")
        return

    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
