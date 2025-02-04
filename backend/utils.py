import pandas as pd

class MLBPlayUtils:
    def __init__(self):
        pass

    def create_scorecard(self, api_response):
        innings = api_response['liveData']['linescore']['innings']

        home_team_name = api_response['gameData']['teams']['home']['teamName']
        away_team_name = api_response['gameData']['teams']['away']['teamName']

        home_data = []
        away_data = []

        for inning in innings:
            home_data.append({
                'runs': inning['home']['runs'],
                'hits': inning['home']['hits'],
                'errors': inning['home']['errors'],
                'inning_num': str(inning['num'])
            })

            away_data.append({
                'runs': inning['away']['runs'],
                'hits': inning['away']['hits'],
                'errors': inning['away']['errors'],
                'inning_num': str(inning['num'])
            })

        home_df = pd.DataFrame(home_data, columns=['runs', 'hits', 'errors', 'inning_num'])
        away_df = pd.DataFrame(away_data, columns=['runs', 'hits', 'errors', 'inning_num'])

        home_df['team'] = home_team_name
        away_df['team'] = away_team_name

        combined_df = pd.concat([away_df, home_df], ignore_index=True)
        
        # Rename columns before pivoting
        combined_df = combined_df.rename(columns={
            'inning_num': 'Inning',
            'runs': 'Runs',
            'hits': 'Hits',
            'errors': 'Errors',
            'team': 'Team'  # Rename the 'team' column to 'Team'
        })

        #combined_df = combined_df.add_prefix('inning_')
        #combined_df = combined_df.set_index('inning_team')
        
        scorecard_df = combined_df.pivot(
            index='Team',
            columns='Inning', 
            values='Runs',
        )

        scorecard_df = scorecard_df.reindex(index=[away_team_name, home_team_name])
        return scorecard_df


    def get_player_details(self, data):
        player_details = {'home': {}, 'away': {}}
        
        try:
            for team_type in ['home', 'away']:
                team_data = data['liveData']['boxscore']['teams'][team_type]
                players = team_data['players']

                for player_id, player_info in players.items():
                    person = player_info['person']
                    player_details[team_type][player_id] = {
                        'player_id': person.get('id', ''),
                        'full_name': person.get('fullName', ''),
                        'jersey_number': player_info.get('jerseyNumber', ''),
                    }
        except (KeyError, TypeError):
            print("Error: Invalid API response structure.")
            return None

        return player_details


    #def get_venue(self, data):