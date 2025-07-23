import asyncio
import logging
import sys

from olx_db import get_db, init_db

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

init_db()
db = next(get_db())


async def worker_main():
    monitor = ItemMonitor(db=db, scraper_cls=OLXScraper)
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


if __name__ == "__main__":
    try:
        logger.info("Starting OLX item notification worker")
        asyncio.run(worker_main())
    finally:
        logger.info("Shutting down OLX item notification worker")
        db.close()
