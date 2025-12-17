import cv2
import torch
import numpy as np
from torchvision import transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from PIL import Image

"""
Video Deepfake Detection Module

This implementation is adapted from and inspired by:
https://github.com/TRahulsingh/DeepfakeDetector

Original author: TRahulsingh
Modifications:
- Refactored into a reusable class
- Integrated into multimodal (audio + video) pipeline
- Added GPU handling and clean API
"""

class VideoDeepfakeDetector:
    def __init__(self, model_path="../models/best_model-v3.pt", num_frames=100):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.num_frames = num_frames

        weights = EfficientNet_B0_Weights.IMAGENET1K_V1
        self.model = efficientnet_b0(weights=weights)

        num_features = self.model.classifier[1].in_features
        self.model.classifier = torch.nn.Sequential(
            torch.nn.Dropout(0.4),
            torch.nn.Linear(num_features, 2)
        )

        self.model.load_state_dict(
            torch.load(model_path, map_location=self.device)
        )
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        print(f"Video model loaded on {self.device}")

    def _extract_frames(self, video_path):
        frames = []
        cap = cv2.VideoCapture(video_path)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return frames

        indices = np.linspace(
            0, total_frames - 1, self.num_frames, dtype=int
        )

        frame_set = set(indices.tolist())

        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            if i in frame_set:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))

        cap.release()
        return frames

    def predict(self, video_path):
        frames = self._extract_frames(video_path)

        if not frames:
            return 0.5, "No frames extracted"

        probs = []

        with torch.no_grad():
            for frame in frames:
                x = self.transform(frame).unsqueeze(0).to(self.device)
                out = self.model(x)
                prob = torch.softmax(out, dim=1)
                probs.append(prob)

        avg_prob = torch.mean(torch.stack(probs), dim=0)

        # label 1 = fake
        fake_prob = avg_prob[0, 1].item()

        return fake_prob, f"Averaged over {len(frames)} frames"
