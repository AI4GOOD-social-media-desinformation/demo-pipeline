import json
from google import genai


def save_video_file_metadata(video_file, filepath="video_metadata.json"):
    """
    Save video file metadata to JSON for later retrieval
    
    Args:
        video_file: Uploaded video file object
        filepath: Path to save metadata
    """
    metadata = {
        "name": video_file.name,
        "uri": video_file.uri,
        "mime_type": video_file.mime_type,
        "state": video_file.state,
        "size_bytes": video_file.size_bytes if hasattr(video_file, 'size_bytes') else None,
        "create_time": str(video_file.create_time) if hasattr(video_file, 'create_time') else None,
        "expiration_time": str(video_file.expiration_time) if hasattr(video_file, 'expiration_time') else None,
    }
    
    with open(filepath, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved video metadata to {filepath}")
    return metadata

def load_video_file_from_metadata(filepath="video_metadata.json"):
    """
    Load video file reference from saved metadata
    
    Args:
        filepath: Path to metadata file
        
    Returns:
        Video file object (retrieved from API)
    """
    client = genai.Client()
    with open(filepath, 'r') as f:
        metadata = json.load(f)
    
    # Retrieve the file from the API using its name
    video_file = client.files.get(name=metadata["name"])
    print(f"Loaded video file: {video_file.name}")
    return video_file