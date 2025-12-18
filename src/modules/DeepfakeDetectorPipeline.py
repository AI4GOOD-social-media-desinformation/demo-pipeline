import os
import torch
import librosa
import moviepy.editor as mp
import uuid
from transformers import (
    Wav2Vec2FeatureExtractor,
    AutoModelForAudioClassification
)

from src.utils.video_detector import VideoDeepfakeDetector
from src.utils.dataclasses import FirestoreObject
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from firebase_admin import firestore

"""
Usage example:

if __name__ == "__main__":
    detector = DeepfakeDetectorPipeline()

    video_path = "instagram_data/real/2025-08-18_14-41-45_UTC.mp4"
    result = detector.predict(video_path)
"""

class DeepfakeDetectorPipeline:
    """
    DeepfakeDetectorPipeline

    A multimodal deepfake detection system that analyzes
    both audio and video content from a single video file.

    - Audio is analyzed using a pretrained Wav2Vec2-based
      classifier fine-tuned for deepfake detection.
    - Video is analyzed using a frame-based CNN detector.

    The final decision is made by combining audio and
    video probabilities.
    """

    def __init__(self, video_model_path: str = "src/models/best_model-v3.pt", project_id: str = "gen-lang-client-0915299548", database: str = "ai4good", eventbus: InMemoryEventBus | None = None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.db = firestore.Client(project=project_id, database=database)
        self.eventbus = eventbus

        self.audio_model_name = "Hemgg/Deepfake-audio-detection"
        self.audio_processor = Wav2Vec2FeatureExtractor.from_pretrained(
            self.audio_model_name
        )
        self.audio_model = AutoModelForAudioClassification.from_pretrained(
            self.audio_model_name
        ).to(self.device)

        self.video_detector = VideoDeepfakeDetector(
            model_path=video_model_path,
            num_frames=100
        )

        print("Audio + Video models loaded")

    def set_eventbus(self, eventbus: InMemoryEventBus):
        self.eventbus = eventbus

    def _extract_audio(self, video_path, audio_path):
        try:
            video = mp.VideoFileClip(video_path)
            if video.audio is None:
                return None
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        except Exception as e:
            print(f"Audio extraction error: {e}")
            return None

    def _process_audio(self, audio_path):
        if not audio_path:
            return 0.5, "No audio"

        speech, sr = librosa.load(audio_path, sr=16000)

        max_seconds = 10
        speech = speech[: max_seconds * sr]

        inputs = self.audio_processor(
            speech,
            sampling_rate=sr,
            return_tensors="pt",
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.audio_model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)

        fake_prob = probs[0][1].item()
        return fake_prob, "Analyzed"

    def _process_video(self, video_path):
        return self.video_detector.predict(video_path)


    def run(self, event_data, method: str = "audio+video"):
        try:
            video_path = event_data.get("data", {}).get("videoPath", "")
            request_id = event_data.get("id", str(uuid.uuid4()))

            audio_path = f"data/audio_requests/{request_id}.wav"
            if not os.path.exists(video_path):
                err = {"id": request_id, "error": "File not found", "data": event_data.get("data", {})}
                if self.eventbus:
                    self.eventbus.publish("deepfake_detection.failed", err)
                return err

            self._extract_audio(video_path, audio_path)
            audio_prob, _ = self._process_audio(audio_path)
            video_prob, _ = self._process_video(video_path)

            firestore_object = FirestoreObject(
                userId=event_data.get("data", {}).get("userId", ""),
                videoUrl=event_data.get("data", {}).get("videoUrl", ""),
                videoId=event_data.get("data", {}).get("videoId", ""),
                videoPath=video_path,
                videoText=event_data.get("data", {}).get("videoText", ""),
                claim=event_data.get("data", {}).get("claim", ""),
                context=event_data.get("data", {}).get("context", ""),
                analysisMessage=event_data.get("data", {}).get("analysisMessage", []),
                newsMessage=event_data.get("data", {}).get("newsMessage", []),
                probVideoFake=video_prob,
                probAudioFake=audio_prob
            )

            # Update only probability fields in Firestore for the existing document
            try:
                self.db.collection('requests').document(request_id).update({
                    "probVideoFake": video_prob,
                    "probAudioFake": audio_prob
                })
            except Exception as e:
                print(f"Error updating Firestore with ID: {request_id}, error: {e}")
                if self.eventbus:
                    self.eventbus.publish("deepfake_detection.failed", {
                        "id": request_id,
                        "error": "Firestore update error",
                        "data": firestore_object.__dict__
                    })
                return {"id": request_id, "error": "Firestore update error"}

            out_event = {"id": request_id, "data": firestore_object.__dict__}
            if self.eventbus:
                self.eventbus.publish("deepfake_detection.completed", out_event)
            return out_event
        except Exception as e:
            print(f"Deepfake detection unexpected error: {e}")
            if self.eventbus:
                self.eventbus.publish("deepfake_detection.failed", {
                    "id": event_data.get("id", "unknown"),
                    "error": str(e)
                })
            return None
     