from google import genai
from google.genai import types
from src.utils.dataclasses import FirestoreObject
from src.eventbus.InMemoryEventBus import InMemoryEventBus

import firebase_admin
from firebase_admin import firestore
import os
import time


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class GeminiClaimExtraction:
    """
    Module for extracting claims and context from videos using LLM.
    Processes video content, saves results to Firestore, and returns structured data.
    """

    def __init__(self, project_id: str = "gen-lang-client-0915299548", database: str = "ai4good", eventbus: InMemoryEventBus = None):
        """
        Initialize ClaimExtraction with Firestore credentials.
        
        Args:
            project_id: GCP project ID for Firestore
            database: Firestore database name
        """
        self.db = firestore.Client(project=project_id, database=database)
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.model = "gemini-2.5-flash"
        self.mime_type = "video/mp4"
        self.eventbus = eventbus

    def set_eventbus(self, eventbus: InMemoryEventBus):
        """
        Set the event bus for publishing events.
        
        Args:
            eventbus: InMemoryEventBus instance
        """
        self.eventbus = eventbus

    def analyze_with_prompt(self, video_file, prompt_text: str) -> str:
        """
        Analyze video with a specific prompt using Gemini API.
        
        Args:
            video_file: Uploaded video file object with uri and mime_type
            prompt_text: Analysis prompt
            
        Returns:
            Analysis result text
        """
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_uri(
                    file_uri=video_file.uri,
                    mime_type=video_file.mime_type
                ),
                prompt_text
            ]
        )
        return response.text

    def upload_video(self, video_path: str, wait_for_processing: bool = True):
        """
        Upload a video file to Google GenAI.
        
        Args:
            video_path: Path to the video file to upload
            wait_for_processing: If True, wait for video to be processed before returning
            
        Returns:
            Video file object with uri and mime_type attributes
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            ValueError: If video processing fails
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        print(f"Uploading video: {video_path}")
        
        with open(video_path, 'rb') as f:
            video_file = self.client.files.upload(
                file=f,
                config=types.UploadFileConfig(mime_type=self.mime_type)
            )

        print(f"Uploaded file: {video_file.name}")
        
        if wait_for_processing:
            video_file = self._wait_for_processing(video_file)
        
        return video_file

    def _wait_for_processing(self, video_file, timeout: int = 300):
        """
        Wait for video file to complete processing on Google's servers.
        
        Args:
            video_file: File object to monitor
            timeout: Maximum seconds to wait (default: 300)
            
        Returns:
            Processed file object
            
        Raises:
            TimeoutError: If processing takes longer than timeout
            ValueError: If processing fails
        """
        print("Waiting for video processing...")
        start_time = time.time()
        
        while video_file.state == "PROCESSING":
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Video processing exceeded {timeout} seconds timeout")
            
            time.sleep(2)
            video_file = self.client.files.get(name=video_file.name)

        if video_file.state == "FAILED":
            raise ValueError("Video processing failed on server")

        print("Video processing complete!")
        return video_file

    def extract_claim(self, video_file, summarization_prompt: str, claim_prompt: str) -> dict:
        """
        Extract claim from video through two-step analysis:
        1. Summarize video content
        2. Extract claim from summary
        
        Args:
            video_file: Uploaded video file object
            summarization_prompt: Prompt for video summarization
            claim_prompt: Prompt template for claim extraction (can use {summary} placeholder)
            
        Returns:
            Dictionary with summary and claim
        """
        # Step 1: Summarize video
        summary = self.analyze_with_prompt(video_file, summarization_prompt)
        
        # Step 2: Extract claim from summary
        formatted_claim_prompt = claim_prompt.format(summary=summary) if "{summary}" in claim_prompt else claim_prompt
        claim = self.analyze_with_prompt(video_file, formatted_claim_prompt)
        
        return {
            "summary": summary,
            "claim": claim
        }
    def sanity_check_event_data(self, data: dict) -> None:
        """
        Ensure required fields are present in event data.
        
        Args:
            data: Event data dictionary
            
        Raises:
            ValueError: If any required field is missing
        """
        required_fields = ["id", "data"]
        required_fields_data = ["videoPath"]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in event data: {field}")
            
        for field in required_fields_data:
            if field not in data["data"]:
                raise ValueError(f"Missing required field in event data['data']: {field}")

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

        # Set default prompts if not provided
        summarization_prompt = """
            Por favor faça uma extração deste vídeo incluindo:
            - Principais tópicos discutidos
            - Participantes do vídeo e tom do discurso
            """
        
        claim_prompt = """
            Com base no seguinte resumo do vídeo, gere em uma sentença a mensagem do vídeo:
            {summary}
            """
        
        # Step 1: Upload video
        video_file = self.upload_video(event_data["data"]["videoPath"])
        
        # Step 2: Extract claim and summary
        analysis_results = self.extract_claim(video_file, summarization_prompt, claim_prompt)
        
        # Step 3: Create Firestore object
        
        firestore_obj = FirestoreObject(
            userId=event_data["data"].get("userId"),
            videoUrl=event_data["data"].get("videoUrl"),
            videoId=event_data["data"].get("videoId"),
            videoPath=event_data["data"].get("videoPath"),
            videoText=event_data["data"].get("videoText"),
            claim=analysis_results["claim"],
            context=analysis_results["summary"],
            analysisMessage=[],
            newsMessage=[],
        )
        
        # Step 4: Save to Firestore
        try:
            self.db.collection('requests').document(event_data["id"]).set(firestore_obj.__dict__)
        except Exception as e:
            print("Error saving to Firestore with  ID:", event_data["id"], "error:", e)
            self.eventbus.publish("claim_extraction.failed", {"id": event_data["id"], "error": "Firestore save error"})

        # Step 5: Publish success event
        self.eventbus.publish("claim_extraction.completed", {"id": event_data["id"], "data": firestore_obj.__dict__})
        


    def on_claim_extraction_completed(self, event_data):
            print(f"Claim extraction completed for ID: {event_data['id']}")

    def on_claim_extraction_failed(self, event_data):
            print(f"Claim extraction failed for ID: {event_data['id']}, Error: {event_data['error']}")