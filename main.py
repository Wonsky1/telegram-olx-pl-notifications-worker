import asyncio
import logging
import sys

from tools.monitoring.monitor import ItemMonitor
from tools.scraping.olx import OLXScraper
from db.database import init_db
from db.database import get_db
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler('olx_worker.log')
    ]
)

logger = logging.getLogger(__name__)

init_db()
db = next(get_db())

async def worker_main():
    while True:
        try:
            logger.info("Starting new item search cycle")
            monitor = ItemMonitor(db=db, scraper_cls=OLXScraper)
            await monitor.run_once()
        except Exception as e:
            logger.error(f"Error in item finder: {e}", exc_info=True)
        logger.info(f"Sleeping for {settings.CYCLE_FREQUENCY_SECONDS} seconds before next cycle")
        await asyncio.sleep(settings.CYCLE_FREQUENCY_SECONDS)

if __name__ == "__main__":
    try:
        logger.info("Starting OLX item notification worker")
        asyncio.run(worker_main())
    finally:
        logger.info("Shutting down OLX item notification worker")
        db.close()
