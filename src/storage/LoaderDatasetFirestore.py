from src.utils.dataclasses import DatasetSample, FirestoreObject
import os
import firebase_admin
from firebase_admin import firestore
import uuid

import os


class LocalDatasetFirestore:

    def __init__(self, data_dir: str):


        # Application Default credentials are automatically created.
        self.db = firestore.Client(project="gen-lang-client-0915299548", database="ai4good")

        self.data_dir = data_dir
        self._sanity_check_data_dir()


    def _sanity_check_data_dir(self) -> None:
        
        """Checks if the data directory exists."""
        if not os.path.exists(self.data_dir) or not os.path.isdir(f"{self.data_dir}/vids"):
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")
        

    
    def upload(self, id: str):

        """Uploads dataset samples to GCP Firestore"""
        for f in os.listdir(f"{self.data_dir}/vids/{id}"):
            if f.endswith(".mp4"):
                video_path = f"{self.data_dir}/vids/{id}/{f}"
            if f.endswith(".txt"):
                with open(f"{self.data_dir}/vids/{id}/{f}", 'r', encoding='utf-8') as file:
                    video_text = file.read()

        
        firestore_id = str(uuid.uuid4())

        data = DatasetSample(
            videoId=id,
            videoUrl=f"https://www.instagram.com/p/{id}",
            videoPath=video_path,
            videoText=video_text,
            
        )

        obj = FirestoreObject(
            userId="",
            videoUrl=data.videoUrl,
            videoId=data.videoId,
            videoPath=data.videoPath,
            videoText=data.videoText,
            claim="",
            context="",
            analysisMessage=[],
            newsMessage=[],
        )

        

        response = self.db.collection('requests').document(firestore_id).set(obj.__dict__)
        return {"response": response, "id": firestore_id, "data": obj.__dict__}
    
    def close(self):
        """Closes the Firestore client."""
        self.db.close()


    def on_upload_failed(self, event_data: dict):
        
        """Handler for upload failed event."""
        print(f"Upload failed for dataset ID: {event_data['id']}. Error: {event_data['error']}")


        




        
      

        
