import re
import requests
from datetime import datetime, timedelta, timezone
import os
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
def setup_logging():
    logger = logging.getLogger('dynamic-playlist')
    logger.setLevel(logging.INFO)
    
    # Create handlers
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler with rotation (max 5MB, keep 5 backup files)
    file_handler = RotatingFileHandler(
        'dynamic-playlist.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Global logger instance
logger = setup_logging()

SCREENLY_TOKEN = os.getenv('SCREENLY_TOKEN')
CALENDARIFIC_TOKEN = os.environ.get('CALENDARIFIC_TOKEN')
START_HOLIDAY = 1
END_HOLIDAY = 2
START_HOLIDAY_OFFSET = 3
END_HOLIDAY_OFFSET = 4
RANGE_PATTERN = r"^([\w\s\d\.']+)\|(?:(\d+)|(?:([A-Za-z\s\.']+)(?:\+([\d]+))?))\|(?:(\d+)|(?:([A-Za-z\s\.']+)(?:\+([\d]+))?))$"
PATTERN = re.compile(RANGE_PATTERN)

def get_screenly_headers() -> dict:
    logger.debug("Getting Screenly headers")
    if not SCREENLY_TOKEN:
        logger.error("SCREENLY_TOKEN environment variable not set")
        raise ValueError("SCREENLY_TOKEN not set")
    return {
        "Authorization": f"Token {SCREENLY_TOKEN}",
        "Content-Type": "application/json"
    }

def get_holiday_headers() -> dict:
    logger.debug("Getting holiday headers")
    if not CALENDARIFIC_TOKEN:
        logger.error("CALENDARIFIC_TOKEN environment variable not set")
        raise ValueError("CALENDARIFIC_TOKEN not set")
    return {"API_KEY": f"{CALENDARIFIC_TOKEN}"}

def iso_to_ms(date: str, delta: int = 0) -> int:
    date_obj = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    date_obj += timedelta(days=delta)
    return int(date_obj.timestamp() * 1000)


def create_date(date: str, delta: int = 0) -> int:
    date_obj = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    date_obj += timedelta(days=delta)
    return date_obj.isoformat()

def get_screenly_playlists() -> dict:
    logger.info("Fetching Screenly playlists")
    try:
        response = requests.request(
            method='GET',
            url='https://api.screenlyapp.com/api/v3/playlists/',
            headers=get_screenly_headers()
        )
        response.raise_for_status()
        logger.info(f"Successfully fetched {len(response.json())} playlists")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch playlists: {str(e)}")
        return {}

def get_holidays(country: str = "US", year: int = datetime.now().year):
    logger.info(f"Fetching holidays for {country} in {year}")
    try:
        response = requests.request(
            method='GET',
            url='https://calendarific.com/api/v2/holidays?',
            params={
                "api_key": get_holiday_headers()['API_KEY'],
                "country": country,
                "year": year
            }
        )
        response.raise_for_status()
        holidays = {
            holiday['name']: holiday['date']['iso']
            for holiday in response.json()['response']['holidays']
        }
        logger.info(f"Successfully fetched {len(holidays)} holidays")
        return holidays
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch holidays: {str(e)}")
        return {}

def update_playlist(playlist: dict, new_predicate: str):
    if not playlist.get('id'):
        logger.warning(f"No ID found for playlist: {playlist.get('title', 'Unknown')}")
        return

    if not new_predicate or playlist['predicate'] == new_predicate:
        logger.info(f"No update needed for playlist: {playlist['title']}")
        return

    try:
        response = requests.request(
            method='PATCH',
            url=f'https://api.screenlyapp.com/api/v3/playlists/{playlist["id"]}/',
            json={'predicate': new_predicate},
            headers=get_screenly_headers()
        )
        response.raise_for_status()
        logger.info(f"Successfully updated playlist: {playlist['title']}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update playlist {playlist['title']}: {str(e)}")

def regex_to_values(playlist_title, holidays):
    if not (regex_result := PATTERN.match(playlist_title)):
        logger.warning(f"Playlist title doesn't match regex pattern: {playlist_title}")
        return (None,) * 6
    
    logger.debug(f"Successfully parsed playlist title: {playlist_title}")
    return (
        regex_result.group(2),
        holidays.get(regex_result.group(3)),
        regex_result.group(4),
        regex_result.group(5),
        holidays.get(regex_result.group(6)),
        regex_result.group(7)
    )

def process_playlists(playlists: list, holidays: dict):
    logger.info(f"Processing {len(playlists)} playlists with {len(holidays)} holidays")
    
    for playlist in playlists:
        if not playlist['is_enabled']:
            logger.info(f"Skipping disabled playlist: {playlist['title']}")
            continue

        if '|' not in playlist['title']:
            holiday = holidays.get(playlist['title'])
            if holiday:
                logger.debug(f"Processing simple holiday playlist: {playlist['title']}")
                update_playlist(playlist, f'TRUE AND ($DATE = {iso_to_ms(holiday)})')
            else:
                logger.info(f"Skipping non-holiday playlist: {playlist['title']}")
            continue

        start_offset, start_date, start_date_delta, end_offset, end_date, end_date_delta = regex_to_values(
            playlist['title'], holidays)

        if not start_date and not end_date:
            logger.error(f"Invalid expression for playlist {playlist['title']}: need a date to reference")
            continue

        try:
            final_start_date = final_end_date = None
            
            if start_date and start_date_delta:
                final_start_date = create_date(start_date, int(start_date_delta))
            elif start_offset and end_date:
                final_start_date = create_date(end_date, -int(start_offset))
            elif start_date:
                final_start_date = start_date

            if end_date and end_date_delta:
                final_end_date = create_date(end_date, int(end_date_delta))
            elif end_offset and start_date:
                final_end_date = create_date(start_date, int(end_offset))
            elif end_date:
                final_end_date = end_date

            if final_start_date and final_end_date:
                predicate = f'TRUE AND ($DATE >= {iso_to_ms(final_start_date)}) AND ($DATE <= {iso_to_ms(final_end_date)})'
                update_playlist(playlist, predicate)
                
        except ValueError as e:
            logger.error(f"Error processing dates for playlist {playlist['title']}: {str(e)}")

def main():
    logger.info("Starting dynamic playlist update process")
    try:
        process_playlists(get_screenly_playlists(), get_holidays())
        logger.info("Successfully completed playlist updates")
    except Exception as e:
        logger.critical(f"Critical error in main process: {str(e)}", exc_info=True)

if __name__ == '__main__':
    main()
