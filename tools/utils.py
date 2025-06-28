import time
import logging
from datetime import datetime, timedelta
from typing import List
import pytz

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
        # Parse the time from OLX (which appears to be in UTC based on debugging)
        parsed_time = datetime.strptime(time_str, time_format).time()
        
        # Get current time in UTC (since OLX seems to use UTC)
        utc_tz = pytz.UTC
        now_utc = datetime.now(utc_tz)
        
        # Create datetime object for the parsed time in UTC
        time_provided_utc = utc_tz.localize(
            datetime.combine(now_utc.date(), parsed_time)
        )
        
        # Calculate n minutes ago in UTC
        n_minutes_ago_utc = now_utc - timedelta(minutes=n)
        
        return time_provided_utc >= n_minutes_ago_utc
        
    except ValueError:
        logger.error(f"Invalid time format: {time_str}")
        return False


def get_flat_description(flat_url: str) -> str:
    response = requests.get(flat_url)
    soup = BeautifulSoup(response.text, "html.parser")
    description = soup.find("div", attrs={"data-cy": "ad_description"})
    description = description.get_text(strip=True)
    return description


async def get_new_flats(url: str = settings.URL, db=None) -> List[Flat]:
    logger.info(f"Getting new flats at {datetime.now().strftime('%H:%M')}")
    
    # Fetch existing flat URLs from database if db is provided
    existing_urls = set()
    if db:
        existing_urls = {url[0] for url in db.query(FlatRecord.flat_url).all()}
        logger.info(f"Found {len(existing_urls)} existing flats in database")
    
    result = []
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pl-PL,pl;q=0.9,en-GB;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "X-Forwarded-For": "83.0.0.0",  # Polish IP range to get Polish timezone
        "CF-IPCountry": "PL",
    }
    response = requests.get(url, headers=headers)
    logger.info(f"Response status code: {response.status_code}")
    soup = BeautifulSoup(response.text, "html.parser")
    divs = soup.find_all("div", attrs={"data-testid": "l-card"})
    
    skipped_count = 0
    for div in divs[:]:
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

        # Extract the URL early to check for duplicates
        title_div = div.find("div", attrs={"data-cy": "ad-card-title"})
        a_tag = title_div.find("a")
        flat_url = a_tag["href"]
        if not flat_url.startswith("http"):
            flat_url = "https://www.olx.pl" + flat_url
            
        # Check if this flat already exists in the database
        if flat_url in existing_urls:
            logger.debug(f"Skipping already existing flat: {flat_url}")
            skipped_count += 1
            continue
            
        # Continue processing only for new flats
        image_url = None
        img_tag = div.find("img")
        if img_tag and img_tag.has_attr("src"):
            image_url = img_tag["src"]

        price_tag = div.find("p", attrs={"data-testid": "ad-price"})
        price = price_tag.get_text(strip=True)

        title = title_div.get_text(strip=True)

        # Process description
        if "otodom" in flat_url:
            description = "Otodom link will be implemented soon"
        else:
            try:
                description = get_flat_description(flat_url)
                description = await get_description_summary(description)
                if not description:
                    logger.error(f"Error generating description for flat {flat_url}")
                    raise Exception(f"error generating description for flat {flat_url}")
            except Exception as e:
                logger.error(f"Failed to load description for flat {flat_url}: {e}")
                description = f"Failed to load description for flat {flat_url}: {e}"

        # Parse time and create timezone-aware datetime
        parsed_time = datetime.strptime(time, "%H:%M").time()
        utc_tz = pytz.UTC
        now_utc = datetime.now(utc_tz)
        
        # Create datetime in UTC (since OLX appears to use UTC)
        datetime_provided_utc = utc_tz.localize(
            datetime.combine(now_utc.date(), parsed_time)
        )
        
        # Convert to Polish timezone for both storage and display
        poland_tz = pytz.timezone('Europe/Warsaw')
        datetime_provided_poland = datetime_provided_utc.astimezone(poland_tz)
        
        # Store as naive datetime in Polish time (since most DBs don't handle timezones well)
        datetime_provided = datetime_provided_poland.replace(tzinfo=None)
        
        created_at = datetime_provided_poland.strftime("%d.%m.%Y - *%H:%M*")
        logger.debug(f"Saving flat - UTC: {datetime_provided_utc}, Poland: {datetime_provided_poland}, DB storage: {datetime_provided}")

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
    
    logger.info(f"Found {len(result)} new flats, skipped {skipped_count} existing flats")
    return result


async def find_new_flats(db):
    """Periodically check for new flats and store them in the database."""
    distinct_urls = db.query(MonitoringTask.url).distinct().all()
    
    logger.info(f"Starting flat monitoring loop")
    
    for (url,) in distinct_urls:
        logger.info(f"Fetching flats for URL: {url}")
        try:
            # Pass the database session to get_new_flats for early duplicate checking
            flats = await get_new_flats(url=url, db=db)
            logger.info(f"Found {len(flats)} new flats for URL: {url}")
        except Exception as e:
            logger.error(f"Failed to fetch flats for URL: {url} — {e}", exc_info=True)
            continue
        
        # Add all flats to the database (they're already filtered)
        for flat in flats:
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
            logger.info(f"New flat added: {flat.title} | {flat.flat_url}")

        logger.info(f"Finished processing URL: {url}. New flats added: {len(flats)}")
        logger.debug(f"Sleeping before next URL...")

        # Optional: sleep between URL requests to avoid hitting server too hard
        time.sleep(3)

    logger.info("All URLs processed.")