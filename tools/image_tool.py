"""
tools/image_tool.py
Image fetching tool with Pexels + Unsplash fallback and retry loop.
Uses shared utilities from utils/helpers.py.
"""

import os
import time
import random
import uuid
import requests
from crewai.tools import BaseTool
from config.settings import PEXELS_API_KEY, TEMP_IMAGE_DIR, setup_logger, log_step
from utils.helpers import validate_image_file, cleanup_temp_file

logger = setup_logger("image_tool")


class ImageTool(BaseTool):
    name: str = "Image Search"
    description: str = "Get a relevant image for a topic. Input should be a short search keyword."

    def _get_pexels_image(self, query: str) -> dict:
        """Try Pexels first — returns image dict or None"""
        log_step(logger, "IMAGE_CURATOR", "TOOL:Pexels", f"Trying Pexels for: {query}")
        headers = {"Authorization": PEXELS_API_KEY}
        response = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=15&page=1",
            headers=headers,
            timeout=10
        )
        data = response.json()
        if data.get("photos") and len(data["photos"]) > 0:
            photo = random.choice(data["photos"])
            img_response = requests.get(photo["src"]["large"], stream=True, timeout=10)
            img_response.raise_for_status()
            log_step(logger, "IMAGE_CURATOR", "TOOL:Pexels", f"✅ Got image by {photo['photographer']}")
            return {"bytes": img_response.content, "source": "pexels", "credit": photo["photographer"]}
        return None

    def _get_unsplash_image(self, query: str) -> dict:
        """Fallback to Unsplash — returns image dict or None"""
        log_step(logger, "IMAGE_CURATOR", "TOOL:Unsplash", f"Trying Unsplash for: {query}")
        keyword = query.replace(" ", ",")
        seed = random.randint(1, 9999)
        url = f"https://source.unsplash.com/1200x630/?{keyword}&sig={seed}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            log_step(logger, "IMAGE_CURATOR", "TOOL:Unsplash", "✅ Got Unsplash image")
            return {"bytes": response.content, "source": "unsplash", "credit": "Unsplash"}
        return None

    def _fetch_image(self, query: str) -> dict:
        """Try Pexels first, then Unsplash — returns image dict or None"""
        for fetcher, name in [(self._get_pexels_image, "Pexels"), (self._get_unsplash_image, "Unsplash")]:
            try:
                image = fetcher(query)
                if image:
                    return image
            except Exception as e:
                log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"{name} failed: {str(e)}")
        return None

    def _save_image(self, image: dict) -> str:
        """Save image bytes to temp file — returns path or None"""
        try:
            os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
            temp_path = os.path.join(
                TEMP_IMAGE_DIR,
                f"temp_image_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
            )
            with open(temp_path, "wb") as f:
                f.write(image["bytes"])

            if not validate_image_file(temp_path):
                cleanup_temp_file(temp_path)
                return None

            log_step(logger, "IMAGE_CURATOR", "TOOL:Image",
                f"✅ Saved: {temp_path} | Source: {image['source']} | Credit: {image['credit']}")
            return temp_path

        except Exception as e:
            log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"❌ Save error: {str(e)}")
            return None

    def _run(self, query: str) -> str:
        log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"Finding image for: {query}")

        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"Attempt {attempt}/{MAX_RETRIES}...")

            image = self._fetch_image(query)
            if not image:
                log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"❌ Both sources failed on attempt {attempt}")
                time.sleep(2)
                continue

            temp_path = self._save_image(image)
            if temp_path:
                return f"TEMP_IMAGE_PATH:{temp_path}"

            log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"❌ Save failed on attempt {attempt} — retrying...")
            time.sleep(2)

        log_step(logger, "IMAGE_CURATOR", "TOOL:Image", f"❌ All {MAX_RETRIES} attempts failed")
        return "NO_IMAGE"
