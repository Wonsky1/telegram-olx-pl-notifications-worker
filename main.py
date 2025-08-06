import asyncio
import logging
import sys

from clients import close_client, topn_db_client
from core.config import settings
from tools.monitoring.monitor import ItemMonitor
from tools.scraping.olx import OLXScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler('olx_worker.log')
    ],
)

logger = logging.getLogger(__name__)


async def worker_main():
    monitor = ItemMonitor(db_client=topn_db_client, scraper_cls=OLXScraper)
    try:
        while True:
            try:
                logger.info("Starting new item search cycle")
                await monitor.run_once()
            except Exception as e:
                logger.error(f"Error in item finder: {e}", exc_info=True)
            logger.info(
                f"Sleeping for {settings.CYCLE_FREQUENCY_SECONDS} seconds before next cycle"
            )
            await asyncio.sleep(settings.CYCLE_FREQUENCY_SECONDS)
    finally:
        logger.info("Closing ItemMonitor and scraper resources")
        await monitor.close()


async def main():
    try:
        logger.info("Starting OLX item notification worker")
        await worker_main()
    finally:
        logger.info("Shutting down OLX item notification worker")
        await close_client()


if __name__ == "__main__":
    asyncio.run(main())
