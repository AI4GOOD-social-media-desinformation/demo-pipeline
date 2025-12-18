from dataclasses import dataclass

@dataclass
class DatasetSample:
    videoId: str
    videoPath: str
    videoText: str
    videoUrl: str
    
@dataclass
class FirestoreObject:
    userId: str
    videoUrl: str
    videoId: str
    videoPath: str
    videoText: str
    claim: str
    context: str
    analysisMessage: list[str]
    newsMessage: list[str]
    probVideoFake: float| None = None
    probAudioFake: float|None = None