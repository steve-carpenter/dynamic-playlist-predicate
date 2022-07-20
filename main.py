import re
import requests
from datetime import datetime, timedelta, timezone
import os

SCREENLY_TOKEN = os.getenv('SCREENLY_TOKEN')
CALENDARIFIC_TOKEN = os.environ.get('CALENDARIFIC_TOKEN')
START_HOLIDAY = 1
END_HOLIDAY = 2
START_HOLIDAY_OFFSET = 3
END_HOLIDAY_OFFSET = 4
RANGE_PATTERN = "^([\w\s\d]+)\|(?:(\d+)|(?:([A-Za-z\s]+)(?:(?:\+)([\d]+))*))\|(?:(\d+)|(?:([A-Za-z\s]+)(?:(?:\+)([\d]+))*))$"
PATTERN = re.compile(RANGE_PATTERN)


def get_screenly_headers() -> dict:
    headers = {
        "Authorization": f"Token {SCREENLY_TOKEN}",
        "Content-Type": "application/json"
    }
    return headers


def get_holiday_headers() -> dict:
    return {"API_KEY": f"{CALENDARIFIC_TOKEN}"}


def get_current_year() -> str:
    return datetime.now().year


def get_screenly_playlists() -> dict:
    response = requests.request(
        method='GET',
        url='https://api.screenlyapp.com/api/v3/playlists/',
        headers=get_screenly_headers()
    )
    return response.json() if response.ok else {}


def get_screenly_playlist(id: str) -> dict:
    response = requests.request(
        method='GET',
        url=f'https://api.screenlyapp.com/api/v3/playlists/{id}/',
        headers=get_screenly_headers()
    )


def get_holidays():
    response = requests.request(
        method='GET',
        url='https://calendarific.com/api/v2/holidays?',
        params={"api_key": get_holiday_headers(
        )['API_KEY'], "country": "US", "year": get_current_year()}
    )
    return {holiday['name']: holiday['date']['iso']
            for holiday in response.json()['response']['holidays']
            } if response.ok else {}


def iso_to_ms(date: str, delta: int = 0) -> int:
    date_obj = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    date_obj += timedelta(days=delta)
    return int(date_obj.timestamp() * 1000)


def create_date(date: str, delta: int = 0) -> int:
    date_obj = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    date_obj += timedelta(days=delta)
    return date_obj.isoformat()


def update_playlist(playlist: dict, predicate: str):
    if playlist.get('id'):
        response = requests.request(
            method='PATCH',
            url=f'https://api.screenlyapp.com/api/v3/playlists/{playlist.get("id")}/',
            json={'predicate': predicate},
            headers=get_screenly_headers()
        )
        print(f'{playlist.get("title")} updated' if response.ok else "")


def regex_to_values(playlist_title, holidays):
    regex_result = PATTERN.match(playlist_title)
    start_offset = regex_result.group(2)
    start_date = holidays.get(regex_result.group(3))
    start_date_delta = regex_result.group(4)
    end_offset = regex_result.group(5)
    end_date = holidays.get(regex_result.group(6))
    end_date_delta = regex_result.group(7)
    return start_offset, start_date, start_date_delta, end_offset, end_date, end_date_delta


def process_playlists(playlists: list, holidays: dict):
    for playlist in playlists:
        if '|' in playlist['title']:
            start_offset, start_date, start_date_delta, end_offset, end_date, end_date_delta = regex_to_values(
                playlist['title'], holidays)
            # Grab & update groups from regex
            if (start_date_delta and start_date) and (end_date_delta and end_date):
                start_date = create_date(start_date, int(start_date_delta))
                end_date = create_date(end_date, int(end_date_delta))
            elif start_offset and end_date:
                start_date = create_date(end_date, -int(start_offset))
            elif end_offset and start_date:
                end_date = create_date(start_date, int(end_offset))
            elif start_date and start_date_delta:
                start_date = create_date(start_date, int(start_date_delta))
            elif end_date and end_date_delta:
                end_date = create_date(end_date, int(end_date_delta))
            # Grab & update groups from regex
            if start_date and end_date:
                update_playlist(
                    playlist, f'TRUE AND ($DATE >= {iso_to_ms(start_date)}) AND ($DATE <= {iso_to_ms(end_date)})')
        else:
            holiday = holidays.get(playlist['title'])
            if holiday:
                update_playlist(
                    playlist, f'TRUE AND ($DATE = {iso_to_ms(holiday)})')


def main():
    process_playlists(get_screenly_playlists(), get_holidays())


if __name__ == '__main__':
    main()
