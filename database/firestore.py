import firebase_admin
from firebase_admin import credentials, firestore



class MLBLiveFeedSummaryCollection:
    def __init__(self):
        try:
            cred = credentials.Certificate("config/firebase_service_account_key.json")
            firebase_admin.initialize_app(cred)
        except: pass

        self.db = firestore.client()


    def add_play_summary(self, game_pk, data_english, data_spanish=None, data_japanese=None, data_hindi=None):
        self.db.collection("mlb_live_feed_summary").document(str(game_pk)).set(data_english, merge=True)

        if data_spanish:
            try:
                self.db.collection("mlb_live_feed_summary_es").document(str(game_pk)).set(data_spanish, merge=True)
            except Exception as error:
                print(error)

        if data_japanese:
            try:
                self.db.collection("mlb_live_feed_summary_ja").document(str(game_pk)).set(data_japanese, merge=True)
            except Exception as error:
                print(error)

        if data_hindi:
            try:
                self.db.collection("mlb_live_feed_summary_hi").document(str(game_pk)).set(data_hindi, merge=True)
            except Exception as error:
                print(error)

        return True


    def fetch_live_feed_summary(self, game_pk, language='english'):
        if language.lower() == 'english':
            result = self.db.collection("mlb_live_feed_summary").document(str(game_pk)).get()

        elif language.lower() == 'spanish':
            result = self.db.collection("mlb_live_feed_summary_es").document(str(game_pk)).get()

        elif language.lower() == 'japanese':
            result = self.db.collection("mlb_live_feed_summary_ja").document(str(game_pk)).get()

        elif language.lower() == 'hindi':
            result = self.db.collection("mlb_live_feed_summary_hi").document(str(game_pk)).get()
    
        return result.to_dict() or {}
