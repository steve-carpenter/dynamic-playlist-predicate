import requests
from datetime import datetime, timezone
import os

SCREENLY_TOKEN = os.getenv('SCREENLY_TOKEN')
CALENDARIFIC_TOKEN = os.environ.get('CALENDARIFIC_TOKEN')

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
        method= 'GET',
        url= 'https://calendarific.com/api/v2/holidays?',
        params={"api_key":get_holiday_headers()['API_KEY'],"country":"US", "year":get_current_year()}
    )
    return { holiday['name']:holiday['date']['iso']
        for holiday in response.json()['response']['holidays']
        } if response.ok else {}


def iso_to_ms(date: str) -> int:
    date_obj = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
    return int(date_obj.timestamp() * 1000)

def update_playlist(playlist: dict, predicate: str):
    if playlist.get('id'):
        response = requests.request(
                method='PATCH',
                url=f'https://api.screenlyapp.com/api/v3/playlists/{playlist.get("id")}/',
                json={'predicate': predicate},
                headers=get_screenly_headers()
            )
        print(f'{playlist.get("title")} updated' if response.ok else "")

def process_playlists(playlists: list, holidays: dict):
    for playlist in playlists:
            if 'RANGE' in playlist['title']: # Pattern RANGE|{FIRST_EVENT}|{SECOND_EVENT}
                clean_title = playlist['title'].split('|')
                start_date = holidays.get(clean_title[1])
                end_date = holidays.get(clean_title[2])
                if start_date and end_date:
                    update_playlist(playlist,f'TRUE AND ($DATE <= {iso_to_ms(end_date)}) AND ($DATE >= {iso_to_ms(start_date)})')
            else:
                holiday = holidays.get(playlist['title'])
                if holiday:
                    update_playlist(playlist, f'TRUE AND ($DATE = {iso_to_ms(holiday)})')

def main():
    process_playlists(get_screenly_playlists(), get_holidays())

if __name__ == '__main__':
    main()
    