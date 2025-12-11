"""
Example pipeline to test ClaimExtraction class.
Processes videos and extracts claims using Google GenAI.
"""

import os
from src.modules.GeminiClaimExtraction import GeminiClaimExtraction
from src.eventbus.InMemoryEventBus import InMemoryEventBus


def find_video_for_id(video_id: str, data_dir: str = "../data/socialdf/socialdf_vids") -> str:
    """
    Find the first video file for a given video ID.
    
    Args:
        video_id: Instagram video ID
        data_dir: Base directory containing video folders
        
    Returns:
        Path to the video file
        
    Raises:
        FileNotFoundError: If no video found for the ID
    """
    video_dir = os.path.join(data_dir, "vids", video_id)
    
    if not os.path.exists(video_dir):
        raise FileNotFoundError(f"Video directory not found: {video_dir}")
    
    # Find first .mp4 file in the directory
    for file in os.listdir(video_dir):
        if file.endswith(".mp4"):
            return os.path.join(video_dir, file)
    
    raise FileNotFoundError(f"No MP4 video found in {video_dir}")


def main():
    """Test ClaimExtraction with multiple videos."""
    
    # Video IDs to process
    ids = ["DELIpWZN3tU"]
    data_dir = "../data/socialdf/socialdf_vids"
    data_paths = [find_video_for_id(video_id, data_dir) for video_id in ids]

    list_data = [{"id": vid_id, "data": {"videoPath": path}} for vid_id, path in zip(ids, data_paths)]
    
    # Initialize ClaimExtraction module
    claim_extraction = GeminiClaimExtraction(eventbus=InMemoryEventBus())
    
    print("=" * 80)
    print("Testing ClaimExtraction Pipeline")
    print("=" * 80)
    
    for data in list_data:
        print(f"\n[Processing] Video ID: {data['id']}")
        print("-" * 80)
        
        # Find video file

        # Create event data
        event_data = {
            "id": f"claim-{data['id']}",
            "data": {
                "videoId": data['id'],
                "videoPath": data['data']['videoPath'],
                "videoUrl": f"https://instagram.com/p/{data['id']}/",
                "videoText": f"Video {data['id']}",
                "userId": "test-user"
            }
        }
        
        # Run claim extraction
        claim_extraction.run(event_data)

        
        
    
    print("\n" + "=" * 80)
    print("Pipeline Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
