
from src.eventbus.InMemoryEventBus import InMemoryEventBus
import requests

import os



GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class ProcessingMessageSender:
    """
    Module responsible for sending processing messages to Instagram user.

    """

    def __init__(self, eventbus: InMemoryEventBus = None):
        """
        Initialize ClaimExtraction with Firestore credentials.
        
        Args:
            project_id: GCP project ID for Firestore
            database: Firestore database name
        """

        self.eventbus = eventbus

    def set_eventbus(self, eventbus: InMemoryEventBus):
        """
        Set the event bus for publishing events.
        
        Args:
            eventbus: InMemoryEventBus instance
        """
        self.eventbus = eventbus

   
    def sanity_check_event_data(self, data: dict) -> None:
        """
        Ensure required fields are present in event data.
        
        Args:
            data: Event data dictionary
            
        Raises:
            ValueError: If any required field is missing
        """
        required_fields = ["userId"]
        for field in required_fields:
            if field not in data["data"]:
                raise ValueError(f"Missing required field: {field}")

    def run(self, event_data: dict) -> dict:
        """
        Main method: Extract claim from video and save to Firestore.
        
        Args:
            video_file: Uploaded video file object with uri and mime_type
            video_id: Instagram video ID
            video_url: Video URL
            video_path: Local path to video file
            video_text: Video text/caption
            user_id: User ID (optional)
            summarization_prompt: Custom summarization prompt (optional)
            claim_prompt: Custom claim extraction prompt (optional)
            
        Returns:
            Dictionary containing:
                - id: Firestore document ID
                - videoId: Instagram video ID
                - claim: Extracted claim
                - context: Video summary (used as context)
                - videoUrl: Video URL
                - videoPath: Video path
                - videoText: Original video text
                - userId: User ID
        """
        
        
        self.sanity_check_event_data(event_data)

        url = "https://graph.instagram.com/v21.0/me/messages"
        token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        sender_id = event_data["data"]["userId"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "message": {
                "text": "Estamos processando seu vídeo, a análise será finalizada em alguns instantes!"
            },
            "recipient": {
                "id": sender_id
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status() # Raises an error for 4xx/5xx responses
            print("Success:", response.json())
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            print("Response Body:", response.text)
        # Step 5: Publish success event
        self.eventbus.publish("processing_message.completed", {"id": event_data["id"]})
        
