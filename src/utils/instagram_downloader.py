import os
import re
import subprocess
from typing import List, Dict, Any

"""
Usage example:

if __name__ == "__main__":
    downloader = InstagramDownloader(
        base_download_path="./instagram_downloads"
    )

    urls = [
        "https://www.instagram.com/p/ABC123/",
        "https://www.instagram.com/reel/XYZ456/"
    ]

    result = downloader.instagram_info(urls)
"""

class InstagramDownloader:

    def __init__(self, base_download_path: str):
        self.base_download_path = os.path.abspath(base_download_path)
        os.makedirs(self.base_download_path, exist_ok=True)

    def extract_instagram_id(self, url: str) -> str:
        patterns = [
            r'/p/([A-Za-z0-9_-]+)/?',
            r'/reels/([A-Za-z0-9_-]+)/?',
            r'/reel/([A-Za-z0-9_-]+)/?',
            r'/tv/([A-Za-z0-9_-]+)/?'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract Instagram ID from URL: {url}")

    def _get_post_dir(self, instagram_id: str) -> str:
        path = os.path.join(self.base_download_path, instagram_id)
        os.makedirs(path, exist_ok=True)
        return path

    def run_instaloader(self, instagram_id: str, post_dir: str) -> bool:
        command = ["instaloader", "--", f"-{instagram_id}"]

        try:
            print(f"Running command in {post_dir}: {' '.join(command)}")
            subprocess.run(
                command,
                cwd=post_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return True

        except subprocess.CalledProcessError as e:
            print(f"Instaloader failed: {e}")
            return False

    def find_created_files(self, post_dir: str) -> List[str]:
        all_files = []

        for root, _, files in os.walk(post_dir):
            for file in files:
                all_files.append(os.path.join(root, file))

        return all_files

    def read_text_file_content(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ""

    def create_records(self, files: List[str]) -> List[Dict[str, Any]]:
        records = []

        for file_path in files:
            record = {}

            ext = os.path.splitext(file_path)[1].lower()

            record["file_path"] = file_path
            record["filename"] = os.path.basename(file_path)
            record["directory"] = os.path.dirname(file_path)

            if ext == ".txt":
                record["file_type"] = "text"
                record["content"] = self.read_text_file_content(file_path)
            elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
                record["file_type"] = "video"
                record["content"] = ""
            elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                record["file_type"] = "image"
                record["content"] = ""
            else:
                record["file_type"] = "other"
                record["content"] = ""

            try:
                record["size_bytes"] = os.path.getsize(file_path)
            except OSError:
                record["size_bytes"] = 0

            records.append(record)

        return records

    def process_instagram_url(self, url: str) -> Dict[str, Any] | None:
        try:
            instagram_id = self.extract_instagram_id(url)
            print(f"Processing {instagram_id}")
        except ValueError as e:
            print(e)
            return None

        post_dir = self._get_post_dir(instagram_id)

        if not self.run_instaloader(instagram_id, post_dir):
            return None

        files = self.find_created_files(post_dir)
        if not files:
            print("No files found")
            return None

        return {
            "instagram_id": instagram_id,
            "source_url": url,
            "download_path": post_dir,
            "files": self.create_records(files)
        }

    def instagram_info(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        results = {}

        for url in urls:
            data = self.process_instagram_url(url)

            if data:
                results[data["instagram_id"]] = data
            else:
                print(f"No data collected for {url}")

        return results


