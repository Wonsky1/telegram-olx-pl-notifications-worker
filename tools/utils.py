import time
import logging
from datetime import datetime, timedelta
from typing import List

import validators
import requests
from bs4 import BeautifulSoup

from core.config import settings
from prompts import get_description_summary_prompt
from tools.models import Flat
from db.database import FlatRecord, MonitoringTask

logger = logging.getLogger(__name__)

async def get_description_summary(description: str) -> str:
    response = await settings.GENERATIVE_MODEL.ainvoke(
        input=get_description_summary_prompt(description)
    )
    return response.content


def is_time_within_last_n_minutes(
    time_str: str, n: int = settings.DEFAULT_LAST_MINUTES_GETTING
) -> bool:
    time_format = "%H:%M"
    try:
        time_provided = (
            datetime.strptime(time_str, time_format) + timedelta(minutes=60)
        ).time()
    except ValueError:
        logger.error(f"Invalid time format: {time_str}")
        return False

    now = datetime.now()
    current_time = now.time()

    # time_provided = (datetime.combine(now.date(), now.time())
    n_minutes_ago = (
        datetime.combine(now.date(), current_time) - timedelta(minutes=n)
    ).time()

    return time_provided >= n_minutes_ago


def is_valid_and_accessible(url: str) -> bool:
    """Check if a URL is valid and returns a successful response."""
    if not validators.url(url):
        return False

    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.RequestException:
        return False


def get_valid_url(url: str, fallback_url: str) -> str:
    """Return the provided URL if valid and accessible, otherwise return the fallback URL."""
    return url if is_valid_and_accessible(url) else fallback_url


async def get_new_flats(url: str = settings.URL) -> List[Flat]:
    url = get_valid_url(url, settings.URL)
    logger.info(f"Getting new flats at {datetime.now().strftime('%H:%M')}")
    result = []
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "max-age=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    }
    response = requests.get(url, headers=headers)
    logger.info(f"Response status code: {response.status_code}")
    soup = BeautifulSoup(response.text, "html.parser")
    divs = soup.find_all("div", attrs={"data-testid": "l-card"})
    for div in divs[:10]: # TODO RM
        location_date = div.find("p", attrs={"data-testid": "location-date"}).get_text(
            strip=True
        )
        if not "Dzisiaj" in location_date:
            logger.debug(f"Skipping flat not from today: {location_date}")
            continue

        location, time = location_date.split("Dzisiaj o ")
        location = location.strip()
        if location.endswith("-"):
            location = location[:-1]
        is_within = is_time_within_last_n_minutes(time)
        if not is_within:
            logger.debug(f"Skipping flat with time outside window: {time}")
            continue

        image_url = None
        img_tag = div.find("img")
        if img_tag and img_tag.has_attr("src"):
            image_url = img_tag["src"]

        price_tag = div.find("p", attrs={"data-testid": "ad-price"})
        price = price_tag.get_text(strip=True)

        title = div.find("div", attrs={"data-cy": "ad-card-title"})
        a_tag = title.find("a")

        flat_url = a_tag["href"]
        if "otodom" in flat_url:
            description = "otodom link"
        else:
            flat_url = "https://www.olx.pl" + flat_url
            try:
                description = get_flat_description(flat_url)
                description = await get_description_summary(description)
                if not description:
                    logger.error(f"Error generating description for flat {flat_url}")
                    raise Exception(f"error generating description for flat {flat_url}")
            except Exception as e:
                logger.error(f"Failed to load description for flat {flat_url}: {e}")
                description = f"Failed to load description for flat {flat_url}: {e}"

        title = title.get_text(strip=True)

        time_provided = datetime.strptime(time, "%H:%M").time()
        datetime_provided = datetime.combine(datetime.now(), time_provided)
        created_at = datetime_provided.strftime("%d.%m.%Y - *%H:%M*")
        logger.debug(f"Saving flat with created_at: {created_at}")

        result.append(
            Flat(
                title=title,
                price=price,
                location=location,
                created_at=datetime_provided,
                created_at_pretty=created_at,
                image_url=image_url,
                flat_url=flat_url,
                description=description
            )
        )
    logger.info(f"Found {len(result)} flats")
    return result


def get_flat_description(flat_url: str) -> str:
    response = requests.get(flat_url)
    soup = BeautifulSoup(response.text, "html.parser")
    description = soup.find("div", attrs={"data-cy": "ad_description"})
    description = description.get_text(strip=True)
    return description


async def find_new_flats(db):
    """Periodically check for new flats and store them in the database."""
    distinct_urls = db.query(MonitoringTask.url).distinct().all()
    
    logger.info(f"Starting flat monitoring loop")
    
    for (url,) in distinct_urls:
        logger.info(f"Fetching flats for URL: {url}")
        try:
            flats = await get_new_flats(url=url)
            logger.info(f"Found {len(flats)} flats for URL: {url}")
        except Exception as e:
            logger.error(f"Failed to fetch flats for URL: {url} — {e}", exc_info=True)
            continue
        
        new_count = 0
        for flat in flats:
            # Check if flat already exists in database
            existing = db.query(FlatRecord).filter(FlatRecord.flat_url == flat.flat_url).first()
            if not existing:
                flat_record = FlatRecord(
                    flat_url=flat.flat_url,
                    title=flat.title,
                    price=flat.price,
                    location=flat.location,
                    created_at=flat.created_at,
                    created_at_pretty=flat.created_at_pretty,
                    image_url=flat.image_url,
                    description=flat.description
                )
                db.add(flat_record)
                db.commit()
                new_count += 1
                logger.info(f"New flat added: {flat.title} | {flat.flat_url}")
            else:
                logger.debug(f"Flat already exists: {flat.title} | {flat.flat_url}")

        logger.info(f"Finished processing URL: {url}. New flats added: {new_count}")
        logger.debug(f"Sleeping before next URL...")

        # Optional: sleep between URL requests to avoid hitting server too hard
        time.sleep(3)

    logger.info("All URLs processed.")
