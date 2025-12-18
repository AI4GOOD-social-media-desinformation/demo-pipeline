import requests
import os
import firebase_admin
from firebase_admin import firestore


from src.utils.dataclasses import FirestoreObject
from src.eventbus.InMemoryEventBus import InMemoryEventBus



class ReelsDownloader:

    def __init__(self, project_id: str = "gen-lang-client-0915299548", database: str = "ai4good", eventbus: InMemoryEventBus = None, saving_dir: str = "data/requests"):
        """
        Initialize ClaimExtraction with Firestore credentials.
        
        Args:
            project_id: GCP project ID for Firestore
            database: Firestore database name
        """
        
        self.db = firestore.Client(project=project_id, database=database)
        self.eventbus = eventbus
        self.saving_dir = saving_dir
        os.makedirs(self.saving_dir, exist_ok=True)

    def set_eventbus(self, eventbus: InMemoryEventBus):
        """
        Set the event bus for publishing events.
        
        Args:
            eventbus: InMemoryEventBus instance
        """
        self.eventbus = eventbus

    def _sanity_check(self, event_data: dict) -> bool:
        """
        Perform sanity checks on the event data.
        
        Args:
            event_data: Dictionary containing event data.
            
        Returns:
            bool: True if sanity checks pass, False otherwise.
        """
        if not event_data.get("data", {}).get("videoUrl") and event_data.get("data", {}).get("id"):
            print("Sanity Check Failed: 'videoUrl' or 'id' missing in event data.")
            return False
        return True

    def run(self,  event_data: dict) -> dict:

        """
        Downloads the reel video from the provided URL in event_data.
        
        Args:
            event_data: Dictionary containing 'video_url' key with the reel URL.

        """
        if not self._sanity_check(event_data):
            raise ValueError("Sanity check failed for event data.")

        url = event_data.get("data", {}).get("videoUrl")
        request_id = event_data.get("id")
        try:
    # Use stream=True to download the file in chunks
            response = requests.get(url, stream=True)
            response.raise_for_status() # Raise an exception for bad status codes
            video_path = os.path.abspath(os.path.join(self.saving_dir, f'{request_id}.mp4'))
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk: # Filter out keep-alive new chunks
                        f.write(chunk)
            print(f"Video successfully downloaded and saved to: {video_path}")
            

            firebase_object = FirestoreObject(
                userId=event_data.get("data", {}).get("userId"),
                videoUrl=url,
                videoId=event_data["data"].get("videoId"),
                videoPath=video_path,
                videoText=event_data["data"].get("videoText"),
                claim="",
                context="",
                message=""
            )
            # Save to Firestore
            self.db.collection("requests").document(request_id).set(firebase_object.__dict__)
            self.eventbus.publish("reels_download.completed", {"id": request_id, "data": firebase_object.__dict__})

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the request: {e}")
            raise e
        
        except IOError as e:
            print(f"An error occurred while writing the file: {e}")
            raise e