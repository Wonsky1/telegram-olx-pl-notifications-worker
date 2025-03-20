import asyncio

from tools.utils import find_new_flats
from db.database import init_db
from db.database import get_db

init_db()

db = next(get_db())



async def worker_main():
    while True:
        try:
            await find_new_flats(db)
        except Exception as e:
            print(f"Error in flat finder: {e}")
        print("sleeping for 60 sec")
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(worker_main())
    finally:
        db.close()
