import asyncio
import logging
import sys

from tools.utils import find_new_flats
from db.database import init_db
from db.database import get_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('olx_worker.log')
    ]
)

logger = logging.getLogger(__name__)

init_db()
db = next(get_db())

async def worker_main():
    while True:
        try:
            logger.info("Starting new flat search cycle")
            await find_new_flats(db)
        except Exception as e:
            logger.error(f"Error in flat finder: {e}", exc_info=True)
        logger.info("Sleeping for 60 seconds before next cycle")
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        logger.info("Starting OLX flat notification worker")
        asyncio.run(worker_main())
    finally:
        logger.info("Shutting down OLX flat notification worker")
        db.close()
