import os
import time
import uuid
import textwrap
from PIL import Image, ImageDraw, ImageFont
from config.settings import TEMP_IMAGE_DIR, setup_logger, log_step

logger = setup_logger("affirmation_image")

def create_affirmation_image(affirmation_text: str) -> str:
    """
    Creates a warm sunny affirmation image with text overlay.
    Returns the temp file path.
    """
    log_step(logger, "IMAGE_CREATOR", "TOOL:AffirmationImage", "Creating affirmation image...")

    try:
        os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)

        # --- Canvas size (Story format: 9:16 ratio) ---
        WIDTH, HEIGHT = 1080, 1920

        # --- Create warm sunny gradient background ---
        image = Image.new("RGB", (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(image)

        # Draw gradient from warm orange to golden yellow
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            r = int(255 * 1.0)                        # Red stays 255
            g = int(140 + (215 - 140) * (1 - ratio))  # Green: 140 → 215
            b = int(0 + (50 * ratio))                  # Blue: 0 → 50
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

        # --- Add soft white overlay for readability ---
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, 60))
        image = image.convert("RGBA")
        image = Image.alpha_composite(image, overlay)
        image = image.convert("RGB")
        draw = ImageDraw.Draw(image)

        # --- Add decorative top and bottom bars ---
        draw.rectangle([(0, 0), (WIDTH, 12)], fill=(255, 200, 0))
        draw.rectangle([(0, HEIGHT - 12), (WIDTH, HEIGHT)], fill=(255, 200, 0))

        # --- Load fonts (fallback to default if custom not available) ---
        try:
            font_large = ImageFont.truetype("arial.ttf", 80)
            font_medium = ImageFont.truetype("arial.ttf", 55)
            font_small = ImageFont.truetype("arial.ttf", 40)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # --- Header ---
        header = "✨ Daily Affirmation ✨"
        draw.text((WIDTH // 2, 180), header, font=font_medium,
                  fill=(120, 60, 0), anchor="mm")

        # --- Decorative line under header ---
        draw.line([(WIDTH // 2 - 200, 240), (WIDTH // 2 + 200, 240)],
                  fill=(180, 100, 0), width=4)

        # --- Main affirmation text (wrapped) ---
        wrapped = textwrap.wrap(affirmation_text, width=22)
        total_text_height = len(wrapped) * 110
        start_y = (HEIGHT // 2) - (total_text_height // 2)

        for i, line in enumerate(wrapped):
            y = start_y + (i * 110)
            # Shadow effect
            draw.text((WIDTH // 2 + 3, y + 3), line, font=font_large,
                      fill=(150, 80, 0), anchor="mm")
            # Main text
            draw.text((WIDTH // 2, y), line, font=font_large,
                      fill=(80, 30, 0), anchor="mm")

        # --- Decorative line above footer ---
        draw.line([(WIDTH // 2 - 200, HEIGHT - 260), (WIDTH // 2 + 200, HEIGHT - 260)],
                  fill=(180, 100, 0), width=4)

        # --- Footer ---
        footer = "🌟 Start your day with intention 🌟"
        draw.text((WIDTH // 2, HEIGHT - 200), footer, font=font_small,
                  fill=(120, 60, 0), anchor="mm")

        sub_footer = "Share this with someone who needs it 💛"
        draw.text((WIDTH // 2, HEIGHT - 130), sub_footer, font=font_small,
                  fill=(150, 80, 0), anchor="mm")

        # --- Save ---
        temp_path = os.path.join(TEMP_IMAGE_DIR, f"affirmation_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg")
        image.save(temp_path, "JPEG", quality=95)

        file_size = os.path.getsize(temp_path)
        log_step(logger, "IMAGE_CREATOR", "TOOL:AffirmationImage",
                 f"✅ Image created: {temp_path} | Size: {file_size} bytes")

        return temp_path

    except Exception as e:
        log_step(logger, "IMAGE_CREATOR", "TOOL:AffirmationImage", f"❌ Failed: {str(e)}")
        return None
