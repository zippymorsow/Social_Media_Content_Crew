"""
utils/helpers.py
Shared utility functions used across tools, agents, and crews.
"""

import os
import re
import time
import requests
from config.settings import (
    FACEBOOK_PAGE_TOKEN,
    FACEBOOK_PAGE_ID,
    TEMP_IMAGE_DIR,
    setup_logger,
    log_step
)

logger = setup_logger("helpers")


# ============================================================
# CAPTION UTILITIES
# ============================================================

def clean_caption(text: str) -> str:
    """
    Fix encoding issues, newlines, unicode escapes, and duplication.
    Used by both FacebookPostTool and FacebookAffirmationTool.
    """
    # Fix literal newlines
    text = text.replace('\\n', '\n')
    text = text.replace('\\\\n', '\n')

    # Decode literal \uXXXX unicode escapes into real emoji characters
    def replace_unicode(match):
        try:
            return chr(int(match.group(1), 16))
        except:
            return match.group(0)
    text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)

    # Fix surrogate characters — keeps valid emojis intact
    try:
        text = text.encode('utf-16', 'surrogatepass').decode('utf-16')
    except:
        pass

    text = text.strip()

    # Fix duplication — keep the half with hashtags
    half = len(text) // 2
    first_half = text[:half].strip()
    second_half = text[half:].strip()
    if first_half in second_half or second_half in first_half:
        text = second_half if '#' in second_half else first_half

    return text.strip()


def safe_encode(text: str) -> bytes:
    """Encode caption safely keeping valid emojis as bytes for requests."""
    safe = text.encode('utf-16', 'surrogatepass').decode('utf-16')
    return safe.encode('utf-8', 'surrogatepass')


# ============================================================
# FILE UTILITIES
# ============================================================

def validate_image_file(temp_path: str, min_size_bytes: int = 1000) -> bool:
    """
    Check if a temp image file exists and is large enough to be valid.
    Returns True if valid, False otherwise.
    """
    if not os.path.exists(temp_path):
        log_step(logger, "FILE", "VALIDATE", f"❌ File not found: {temp_path}")
        return False

    file_size = os.path.getsize(temp_path)
    if file_size < min_size_bytes:
        log_step(logger, "FILE", "VALIDATE", f"❌ File too small ({file_size} bytes): {temp_path}")
        return False

    log_step(logger, "FILE", "VALIDATE", f"✅ File valid: {temp_path} ({file_size} bytes)")
    return True


def cleanup_temp_file(temp_path: str):
    """Safely delete a temp image file after upload."""
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            log_step(logger, "FILE", "CLEANUP", f"✅ Temp file removed: {temp_path}")
    except Exception as e:
        log_step(logger, "FILE", "CLEANUP", f"⚠️ Could not remove {temp_path}: {str(e)}")


def parse_tool_input(input: str, separator: str = "|||") -> tuple:
    """
    Parse tool input string into (image_ref, caption).
    Returns (None, None) if format is invalid.
    """
    parts = input.split(separator)
    if len(parts) != 2:
        log_step(logger, "PARSE", "INPUT", f"❌ Invalid format. Expected: ref{separator}caption")
        return None, None
    return parts[0].strip(), parts[1].strip()


# ============================================================
# DATA FILE UTILITIES
# ============================================================

def read_lines_from_file(filepath: str) -> list:
    """
    Read non-empty lines from a text file.
    Returns empty list if file not found or empty.
    """
    if not os.path.exists(filepath):
        log_step(logger, "FILE", "READ", f"❌ File not found: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    log_step(logger, "FILE", "READ", f"✅ Read {len(lines)} line(s) from {filepath}")
    return lines


# ============================================================
# FACEBOOK API UTILITIES
# ============================================================

def post_image_to_feed(temp_path: str, caption: str) -> dict:
    """
    Upload a local image file and post it to the Facebook Page Feed.
    Used by both social crew and affirmation crew.
    """
    log_step(logger, "FACEBOOK", "FEED", f"Posting image to feed: {temp_path}")
    with open(temp_path, "rb") as img_file:
        response = requests.post(
            f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos",
            params={"access_token": FACEBOOK_PAGE_TOKEN},
            data={"caption": safe_encode(caption), "published": True},
            files={"source": ("image.jpg", img_file, "image/jpeg")}
        )
    return response.json()


def post_text_to_feed(caption: str) -> dict:
    """
    Post text-only content to Facebook Page Feed (fallback when no image).
    """
    log_step(logger, "FACEBOOK", "FEED", "Posting text only to feed...")
    safe = caption.encode('utf-16', 'surrogatepass').decode('utf-16')
    response = requests.post(
        f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/feed",
        params={"access_token": FACEBOOK_PAGE_TOKEN},
        json={"message": safe, "published": True}
    )
    return response.json()


def post_image_to_story(temp_path: str) -> dict:
    """
    Upload a local image file and post it to Facebook Page Story (MyDay).
    """
    log_step(logger, "FACEBOOK", "STORY", f"Posting image to story: {temp_path}")
    with open(temp_path, "rb") as img_file:
        response = requests.post(
            f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/stories",
            params={"access_token": FACEBOOK_PAGE_TOKEN},
            files={"source": ("image.jpg", img_file, "image/jpeg")},
            data={"media_type": "IMAGE"}

            # f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photo_stories",
            # params={"access_token": FACEBOOK_PAGE_TOKEN},
            # files={"source": ("image.jpg", img_file, "image/jpeg")}
        )
    return response.json()


def handle_facebook_result(result: dict, context: str, logger_ref) -> str:
    """
    Check Facebook API response and return a human-readable result string.
    Used by all Facebook posting functions.
    """
    post_id = result.get("id") or result.get("post_id")
    if post_id:
        log_step(logger_ref, "FACEBOOK", context, f"✅ Posted! ID: {post_id}")
        return f"Successfully posted ({context})! Post ID: {post_id}"
    else:
        log_step(logger_ref, "FACEBOOK", context, f"❌ Failed: {result}")
        return f"Failed ({context}): {result}"


# ============================================================
# CREW UTILITIES
# ============================================================

def log_crew_start(logger_ref, index: int, total: int, item: str):
    """Log the start of processing an item in a crew loop."""
    log_step(logger_ref, "SYSTEM", f"ITEM {index}/{total}", f"Starting: '{item}'")
    print(f"\n🚀 Processing {index}/{total}: {item}\n")


def log_crew_done(logger_ref, index: int, total: int, item: str, elapsed: float):
    """Log the completion of processing an item in a crew loop."""
    log_step(logger_ref, "SYSTEM", f"ITEM {index}/{total}", f"Completed in {elapsed}s ✅")
    print(f"\n✅ Done! '{item}' completed in {elapsed} seconds\n")


def wait_between_items(logger_ref, seconds: int = 30):
    """Wait between crew runs to avoid rate limits."""
    log_step(logger_ref, "SYSTEM", "DELAY", f"Waiting {seconds} seconds before next item...")
    time.sleep(seconds)


# ============================================================
# THREAD CLEANUP UTILITIES
# ============================================================

def cleanup_crew_threads(crew, logger_ref):
    """
    Properly clean up thread pools created by CrewAI.
    Call this after each crew.kickoff() execution.
    """
    try:
        # Stop any active executor threads
        for agent in crew.agents:
            if hasattr(agent, '_executor') and agent._executor:
                agent._executor.shutdown(wait=False)
        
        # Stop the manager's executor if it exists
        if hasattr(crew, '_manager') and hasattr(crew._manager, '_executor'):
            crew._manager._executor.shutdown(wait=False)
    except Exception as e:
        log_step(logger_ref, "CLEANUP", "THREADS", f"Debug: {e}")


def cleanup_all_threads():
    """
    Emergency cleanup for any remaining daemon threads at exit.
    Automatically registered to run on program exit.
    """
    try:
        # Give daemon threads a brief moment to finish
        time.sleep(0.1)
    except Exception:
        pass
