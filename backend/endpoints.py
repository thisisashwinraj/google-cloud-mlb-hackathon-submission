import json
import requests
import pandas as pd
from datetime import datetime

from google.cloud import translate_v3
from google.oauth2 import service_account
from google.auth.transport.requests import Request



class MLBStatsAPI:
    def __init__(self):
        pass


    def get_mlb_live_feed(self, game_pk):    
        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        response = requests.get(url)

        if response.status_code == 200:
            json_response = response.content
            data = json.loads(json_response)
            return data
        
        else:
            return None
        
    
    def get_mlb_schedule(self, date):
        url = f"""https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date.strftime("%Y-%m-%d")}"""

        response = requests.get(url)

        if response.status_code != 200:
            return None
        
        data = response.json()

        matches = {}

        for date_data in data.get("dates", []):
            if date_data.get("date") == date.strftime("%Y-%m-%d"):
                for game in date_data.get("games", []):
                    away_team = game["teams"]["away"]["team"]["name"]
                    home_team = game["teams"]["home"]["team"]["name"]
                    game_pk = game["gamePk"]

                    matches[f"{away_team} vs {home_team}"] = game_pk

        return matches
    

    def get_mlb_season_schedule(self, year=2025):
        endpoint_url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={year}'
        pop_key = "dates"

        json_result = requests.get(endpoint_url).content
        data = json.loads(json_result)
        if pop_key:
            schedule_dates = pd.json_normalize(data.pop(pop_key), sep = '_')
        else:
            schedule_dates = pd.json_normalize(data)
        
        games = pd.json_normalize(
            schedule_dates.explode('games').reset_index(drop = True)['games']
        )

        sub_games = games[['officialDate', 'teams.away.team.name', 'teams.home.team.name', 'venue.name']]

        sub_games.rename(columns={
            'officialDate': 'Game Date',
            'teams.away.team.name': 'Away Team',
            'teams.home.team.name': 'Home Team',
            'venue.name': 'Venue'
            }, inplace=True)

        return sub_games


    def get_all_teams(self, only_mlb=True):
        url = "https://statsapi.mlb.com/api/v1/teams"
        if only_mlb:
            url = url + "?sportId=1"

        response = requests.get(url)
        if response.status_code != 200:
            return None
        
        data = response.json()

        try:
            team_data = json.loads(data) if isinstance(data, str) else data
            teams = team_data.get('teams', [])

            name_id_map = {}
            for team in teams:
                name = team.get('name')
                team_id = team.get('id')

                if name and team_id:
                    name_id_map[name] = team_id

            return name_id_map

        except (json.JSONDecodeError, AttributeError, TypeError):  # Handle potential errors
            return {}


    def get_game_highlight_videos(self, game_pk):
        url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/content"
        response = requests.get(url)

        if response.status_code == 200:
            json_response = response.content
            data = json.loads(json_response)
        else:
            return None

        game_highlights = {}

        for item in data.get('highlights').get('highlights').get('items'):
            if item.get('type') == 'video':
                headline = item.get('headline')

                for pb_video in item.get('playbacks'):
                    if pb_video.get('name') == 'highBit':
                        game_highlights[headline] = pb_video.get('url')

        del response
        return game_highlights


class CloudTranslationAPI:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            "config/cloud_translation_api_admin_service_account_key.json", 
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())

        self.client = translate_v3.TranslationServiceClient(credentials=credentials)


    def translate_text(self, text, language):        
        if language.lower() == "english":
            return text
        
        parent = f"projects/project-mlb-tool-tips/locations/global"

        language_codes = {
            "english": "en",
            "spanish": "es",
            "japanese": "ja",
            "hindi": "hi",
        }

        response = self.client.translate_text(
            contents=[text],
            target_language_code=language_codes[language.lower()],
            parent=parent,
            mime_type="text/plain",
        )

        return response.translations[0].translated_text



if __name__ == "__main__":
    #mlb_stats_api = MLBStatsAPI()
    #ans = mlb_stats_api.get_mlb_schedule(datetime.strptime("29-09-2024", "%d-%m-%Y"))
    #print(ans)

    trans_api = CloudTranslationAPI()
    print(trans_api.translate_text("Hello there!", "spanish"))
