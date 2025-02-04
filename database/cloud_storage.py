import io
from PIL import Image

from google.cloud import storage
from google.oauth2 import service_account



class MLBStorageBucket:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            "config/cloud_storage_service_account_key.json", 
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        self.storage_client = storage.Client(
            credentials=credentials,
            project=credentials.project_id,
        )


    def upload_play_banner(self, game_pk, play_id, image_file):
        try:
            print(0)
            bucket = self.storage_client.bucket("mlb_storage_bucket")
            print(1)
            
            gcs_file_path = f"play_banners/{game_pk}/{play_id}.png"
            blob = bucket.blob(gcs_file_path)
            print(2)

            blob.upload_from_string(image_file, content_type="image/png")
            print(3)
            return True
        
        except Exception as error:
            print(f"ERROR: {error}")
            print(f"Saving image to GCS failed!!!\n")
            return False


    def fetch_play_banner(self, game_pk, play_id):
        try:
            bucket = self.storage_client.bucket("mlb_storage_bucket")
            
            gcs_file_path = f"play_banners/{game_pk}/{play_id}.png"
            blob = bucket.blob(gcs_file_path)

            image_bytes = blob.download_as_bytes()
            return Image.open(io.BytesIO(image_bytes))
        
        except Exception as error:
            print(f"ERROR: {error}")
            print(f"Error Fetching image from GCS!!!\n")
            return None


if __name__ == "__main__":
    mlb_storage_bucket = MLBStorageBucket()

    game_pk = "747962"
    play_id = "c985139e-106c-46df-8db3-ee7ec5a7ec35"
    image_file = "test2.png"
    
    ans = mlb_storage_bucket.upload_play_banner(game_pk, play_id, image_file)
    print(ans, "\n\n")
    
    ans = mlb_storage_bucket.fetch_play_banner(game_pk, play_id)
    print(ans, "\n")