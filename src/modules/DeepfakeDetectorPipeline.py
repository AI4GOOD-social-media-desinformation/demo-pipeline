import os
import subprocess
import torch
import librosa
import moviepy.editor as mp
import numpy as np
from transformers import (
    Wav2Vec2FeatureExtractor,
    AutoModelForAudioClassification
)

from src.utils.video_detector import VideoDeepfakeDetector

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

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.audio_model_name = "Hemgg/Deepfake-audio-detection"
        self.audio_processor = Wav2Vec2FeatureExtractor.from_pretrained(
            self.audio_model_name
        )
        self.audio_model = AutoModelForAudioClassification.from_pretrained(
            self.audio_model_name
        ).to(self.device)

        self.video_detector = VideoDeepfakeDetector(
            model_path="best_model-v3.pt",
            num_frames=100
        )

        print("Audio + Video models loaded")

    def _extract_audio(self, video_path, audio_output="temp_audio.wav"):
        try:
            video = mp.VideoFileClip(video_path)
            if video.audio is None:
                return None
            video.audio.write_audiofile(audio_output, verbose=False, logger=None)
            return audio_output
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


    def predict(self, video_path, method="audio+video"):
        if not os.path.exists(video_path):
            return {"error": "File not found"}

        audio_file = self._extract_audio(video_path)
        audio_prob, audio_msg = self._process_audio(audio_file)

        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)

        video_prob, video_msg = self._process_video(video_path)

        combined_score = (video_prob * 0.6) + (audio_prob * 0.4)

        if video_prob >= 0.8:
            verdict = "FAKE"
        elif combined_score >= 0.8:
            verdict = "FAKE"
        elif combined_score >= 0.4:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "REAL"

        return {
            "video_path": video_path,
            "audio_fake_prob": round(audio_prob, 4),
            "video_fake_prob": round(video_prob, 4),
            "combined_fake_prob": round(combined_score, 4),
            "verdict": verdict,
            "details": {
                "audio_status": audio_msg,
                "video_status": video_msg,
                "method": method
            }
        }
