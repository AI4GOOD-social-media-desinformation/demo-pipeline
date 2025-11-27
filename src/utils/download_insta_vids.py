import instaloader
import re
import os
import pathlib

def download_insta_vids(url, output_folder):
    # Initialize Instaloader
    L = instaloader.Instaloader()

    # Extract shortcode
    shortcode_match = re.search(r'(?:/p/|/reel/)([^/?#&]+)', url)
    if not shortcode_match:
        raise ValueError("Invalid URL. Could not parse shortcode.")
    
    shortcode = shortcode_match.group(1)

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        if not post.is_video:
            print("Target post is not a video.")
            return

        print(f"Targeting folder: {output_folder}")
        
        # Instaloader creates the folder defined in 'target' if it is missing.
        # It saves the video and metadata files into this directory.

        output_path = pathlib.Path(output_folder) / shortcode
        output_path.mkdir(parents=True, exist_ok=True)
        L.download_post(post, target=output_path)
        
        print(f"Download completed in: {os.path.abspath(output_path)}")

    except Exception as e:
        print(f"Error: {e}")
