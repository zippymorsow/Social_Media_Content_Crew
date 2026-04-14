"""
crews/affirmation_crew.py
Reads affirmations, generates warm sunny images, 
and posts to both Facebook Story (MyDay) and Feed.
"""

import os
from dotenv import load_dotenv
import time
from crewai import Task, Crew, Process
from agents.writer import create_affirmation_writer
from agents.publisher import create_affirmation_publisher
from tools.affirmation_image import create_affirmation_image
from config.settings import DATA_DIR, setup_logger, log_step
from utils.helpers import (
    read_lines_from_file,
    validate_image_file,
    log_crew_start,
    log_crew_done,
    wait_between_items
)

# Force load .env from project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

print(f"Loading .env from: {BASE_DIR}")
print(f"Page ID loaded: {os.getenv('FACEBOOK_PAGE_ID')}")
print(f"Token loaded: {'YES' if os.getenv('FACEBOOK_PAGE_TOKEN') else 'NO'}")

logger = setup_logger("affirmation_crew")


def run():
    log_step(logger, "SYSTEM", "STARTUP", "Initializing Affirmation Crew...")

    affirmation_writer    = create_affirmation_writer()
    affirmation_publisher = create_affirmation_publisher()

    log_step(logger, "SYSTEM", "STARTUP", "All agents ready!")

    # --- Read affirmations ---
    affirmations = read_lines_from_file(os.path.join(DATA_DIR, "affirmations.txt"))
    if not affirmations:
        print("❌ data/affirmations.txt is missing or empty.")
        return

    log_step(logger, "SYSTEM", "STARTUP", f"Found {len(affirmations)} affirmation(s)")

    # --- Process each affirmation ---
    for index, affirmation in enumerate(affirmations, start=1):
        log_crew_start(logger, index, len(affirmations), affirmation)

        # --- Step 1: Expand affirmation with AI ---
        writing_task = Task(
            description=f"""Expand this affirmation into a warm, hopeful, uplifting message:

            Affirmation: "{affirmation}"

            RULES:
            - Maximum 2-3 sentences
            - Warm, hopeful, deeply human tone
            - Use gentle emojis naturally
            - Make people want to screenshot and share it
            - No hashtags""",
            expected_output="A short, warm, uplifting affirmation message with gentle emojis.",
            agent=affirmation_writer,
            callback=lambda output: log_step(logger, "AFFIRMATION_WRITER", "STEP:1 DONE", "Written ✅")
        )

        writing_crew = Crew(
            agents=[affirmation_writer],
            tasks=[writing_task],
            process=Process.sequential,
            verbose=True
        )

        log_step(logger, "SYSTEM", f"AFFIRMATION {index}", "Writing expanded affirmation...")
        writing_result = writing_crew.kickoff()
        expanded_text = str(writing_result).strip()
        log_step(logger, "AFFIRMATION_WRITER", "STEP:1", f"Expanded: {expanded_text[:80]}...")

        # --- Step 2: Create image with Pillow ---
        log_step(logger, "IMAGE_CREATOR", "STEP:2", "Creating affirmation image...")
        temp_path = create_affirmation_image(expanded_text)

        if not temp_path or not validate_image_file(temp_path):
            log_step(logger, "IMAGE_CREATOR", "STEP:2", "❌ Image creation failed — skipping")
            continue

        log_step(logger, "IMAGE_CREATOR", "STEP:2 DONE", f"Image ready: {temp_path} ✅")

        # --- Step 3: Publish to Story + Feed ---
        posting_task = Task(
            description=f"""Publish the affirmation image to Facebook Story (MyDay) and Feed.

            Use this EXACT format for the Facebook Affirmation Publisher tool:
            TEMP_IMAGE_PATH:{temp_path}|||{expanded_text}

            CRITICAL RULES:
            - Call the tool ONLY ONCE
            - Use the EXACT path: TEMP_IMAGE_PATH:{temp_path}
            - Use the EXACT caption shown above""",
            expected_output="Confirmation the affirmation was posted to both Story and Feed with Post IDs.",
            agent=affirmation_publisher,
            callback=lambda output: log_step(logger, "AFFIRMATION_PUBLISHER", "STEP:3 DONE", "Published ✅")
        )

        publishing_crew = Crew(
            agents=[affirmation_publisher],
            tasks=[posting_task],
            process=Process.sequential,
            verbose=True
        )

        start_time = time.time()
        publishing_crew.kickoff()
        elapsed = round(time.time() - start_time, 2)

        log_crew_done(logger, index, len(affirmations), affirmation, elapsed)

        if index < len(affirmations):
            wait_between_items(logger)

    log_step(logger, "SYSTEM", "FINISHED", "All affirmations processed!")
    print("\n🌟 All affirmations posted to MyDay and Feed!")


if __name__ == "__main__":
    run()
