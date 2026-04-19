"""
tools/facebook.py
Facebook posting tools for Feed and Story.
Uses shared utilities from utils/helpers.py.
"""

import os
import time
import requests
from crewai.tools import BaseTool
from config.settings import FACEBOOK_PAGE_ID, FACEBOOK_PAGE_TOKEN, setup_logger, log_step
from tools.image_tool import ImageTool
from utils.helpers import (
    clean_caption,
    validate_image_file,
    cleanup_temp_file,
    parse_tool_input,
    post_image_to_feed,
    post_text_to_feed,
    post_image_to_story,
    handle_facebook_result
)

logger = setup_logger("facebook")


# ============================================================
# FACEBOOK FEED POST TOOL (used by social_crew)
# ============================================================

class FacebookPostTool(BaseTool):
    name: str = "Facebook Post"
    description: str = "Post image + caption to Facebook Page Feed. Input: TEMP_IMAGE_PATH:path|||CAPTION"
    current_topic: str = ""

    def _retry_image(self, topic: str) -> str:
        """Retry ImageTool up to 3 times if temp file is missing."""
        image_tool = ImageTool()
        for retry in range(1, 4):
            log_step(logger, "PUBLISHER", "TOOL:Facebook", f"Image retry {retry}/3...")
            result = image_tool._run(topic)
            if result.startswith("TEMP_IMAGE_PATH:"):
                temp_path = result.replace("TEMP_IMAGE_PATH:", "").strip()
                log_step(logger, "PUBLISHER", "TOOL:Facebook", f"✅ Got image on retry {retry}")
                return temp_path
            time.sleep(2)
        return None

    def _run(self, input: str) -> str:
        log_step(logger, "PUBLISHER", "TOOL:Facebook", "Preparing feed post...")
        log_step(logger, "PUBLISHER", "DEBUG", f"Raw input: {input[:200]}")

        try:
            image_ref, raw_caption = parse_tool_input(input)
            if not image_ref:
                return "Invalid format. Use: TEMP_IMAGE_PATH:path|||CAPTION"

            caption = clean_caption(raw_caption)
            log_step(logger, "PUBLISHER", "TOOL:Facebook", f"Caption preview: {caption[:80]}...")

            # --- Case 1: Temp image file ---
            if image_ref.startswith("TEMP_IMAGE_PATH:"):
                temp_path = image_ref.replace("TEMP_IMAGE_PATH:", "").strip()

                if not validate_image_file(temp_path):
                    log_step(logger, "PUBLISHER", "TOOL:Facebook", "⚠️ File not found — retrying ImageTool...")
                    temp_path = self._retry_image(self.current_topic or "nature")

                    if not temp_path:
                        log_step(logger, "PUBLISHER", "TOOL:Facebook", "❌ All retries failed — text only")
                        result = post_text_to_feed(caption)
                        return handle_facebook_result(result, "Feed Text Only", logger)

                log_step(logger, "PUBLISHER", "TOOL:Facebook", f"Uploading: {temp_path}")
                result = post_image_to_feed(temp_path, caption)
                cleanup_temp_file(temp_path)

            # --- Case 2: No image ---
            elif image_ref == "NO_IMAGE":
                log_step(logger, "PUBLISHER", "TOOL:Facebook", "No image — text only")
                result = post_text_to_feed(caption)

            # --- Case 3: Direct URL ---
            else:
                log_step(logger, "PUBLISHER", "TOOL:Facebook", "Using direct image URL")
                safe = caption.encode('utf-16', 'surrogatepass').decode('utf-16')
                response = requests.post(
                    f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos",
                    params={"access_token": FACEBOOK_PAGE_TOKEN},
                    json={"url": image_ref, "caption": safe, "published": True}
                )
                result = response.json()

            return handle_facebook_result(result, "Feed", logger)

        except Exception as e:
            log_step(logger, "PUBLISHER", "TOOL:Facebook", f"ERROR: {str(e)}")
            return f"Error: {str(e)}"


# ============================================================
# FACEBOOK AFFIRMATION TOOL (used by affirmation_crew)
# Posts to BOTH Story (MyDay) AND Feed
# ============================================================

class FacebookAffirmationTool(BaseTool):
    name: str = "Facebook Affirmation Publisher"
    description: str = "Post affirmation image to Facebook Story (MyDay) AND Feed. Input: TEMP_IMAGE_PATH:path|||CAPTION"

    def _run(self, input: str) -> str:
        log_step(logger, "AFFIRMATION_PUBLISHER", "TOOL:Facebook", "Preparing affirmation post...")
        log_step(logger, "AFFIRMATION_PUBLISHER", "DEBUG", f"Raw input: {input[:200]}")

        try:
            image_ref, raw_caption = parse_tool_input(input)
            if not image_ref:
                return "Invalid format. Use: TEMP_IMAGE_PATH:path|||CAPTION"

            if not image_ref.startswith("TEMP_IMAGE_PATH:"):
                return "Error: Expected TEMP_IMAGE_PATH"

            temp_path = image_ref.replace("TEMP_IMAGE_PATH:", "").strip()
            caption = clean_caption(raw_caption)

            if not validate_image_file(temp_path):
                return f"Error: Image file not found or invalid: {temp_path}"

            results = []

            # --- Post to Story (MyDay) ---
            story_result = post_image_to_story(temp_path)
            results.append(handle_facebook_result(story_result, "Story/MyDay", logger))

            # --- Post to Feed ---
            # feed_result = post_image_to_feed(temp_path, caption)
            # results.append(handle_facebook_result(feed_result, "Feed", logger))

            # --- Cleanup ---
            cleanup_temp_file(temp_path)

            return " | ".join(results)

        except Exception as e:
            log_step(logger, "AFFIRMATION_PUBLISHER", "TOOL:Facebook", f"ERROR: {str(e)}")
            return f"Error: {str(e)}"
