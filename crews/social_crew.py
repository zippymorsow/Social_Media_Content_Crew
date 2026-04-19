"""
crews/social_crew.py
Researches topics and posts engaging content to Facebook Feed.
"""

import os
import re
import time
import atexit
from crewai import Task, Crew, Process
from agents.researcher import create_researcher
from agents.writer import create_writer
from agents.hashtag_agent import create_hashtag_agent
from tools.facebook import FacebookPostTool
from tools.image_tool import ImageTool
from config.settings import DATA_DIR, setup_logger, log_step
import config.settings as settings
from utils.helpers import (
    read_lines_from_file,
    log_crew_start,
    log_crew_done,
    wait_between_items,
    cleanup_crew_threads,
    cleanup_all_threads
)

settings.CURRENT_CREW = "social_crew"

logger = setup_logger("social_crew")


def extract_temp_image_path(text: str) -> str:
    """
    Pull the TEMP_IMAGE_PATH value out of the image agent's raw output.
    Handles cases where the agent wraps it in extra text.
    """
    # Match TEMP_IMAGE_PATH:/some/path/file.jpg  (greedy to end of word)
    match = re.search(r'TEMP_IMAGE_PATH:\S+', text)
    if match:
        return match.group(0).strip()
    return None


def run():
    log_step(logger, "SYSTEM", "STARTUP", "Initializing Social Media Crew...")

    # --- Initialize Facebook tool ---
    facebook_tool = FacebookPostTool()

    # --- Read topics ---
    topics = read_lines_from_file(os.path.join(DATA_DIR, "topics.txt"))
    if not topics:
        print("❌ data/topics.txt is missing or empty.")
        return

    log_step(logger, "SYSTEM", "STARTUP", f"Found {len(topics)} topic(s)")

    # --- Process each topic ---
    overall_start_time = time.time()
    for index, topic in enumerate(topics, start=1):
        start_time = time.time()
        log_crew_start(logger, index, len(topics), topic)

        # Recreate agents fresh each iteration to avoid stale state
        facebook_tool.current_topic = topic
        researcher    = create_researcher()
        writer        = create_writer()
        hashtag_agent = create_hashtag_agent()

        log_step(logger, "SYSTEM", "STARTUP", "All 4 agents ready!")

        research_task = Task(
            description=f"""Research this topic and find the most surprising, fascinating, 
            and mind-blowing facts about it: {topic}
            Focus on: recent news, unexpected facts, wow moments, human stories.""",
            expected_output="A rich collection of fascinating facts and recent news.",
            agent=researcher,
            callback=lambda output: log_step(logger, "RESEARCHER", "STEP:1 DONE", "Research complete ✅")
        )

        writing_task = Task(
            description=f"""Using the research, write a VIBRANT, WHIMSICAL, LIVELY Facebook post about: {topic}
            RULES:
            - Write with ENERGY and ENTHUSIASM
            - Use emojis expressively throughout
            - 100-150 words maximum
            - End with a fun engaging question
            - No hashtags (another agent handles that)
            - NEVER be flat or generic""",
            expected_output="A vibrant Facebook post caption bursting with personality.",
            agent=writer,
            callback=lambda output: log_step(logger, "WRITER", "STEP:2 DONE", "Post written ✅")
        )

        hashtag_task = Task(
            description=f"""You will receive a written Facebook post.
            YOUR ONLY JOB:
            1. Add ONE category label at the TOP: ✨ Category: [Category Name]
            2. Add 8-10 hashtags at the BOTTOM
            STRICT RULES:
            - DO NOT rewrite or repeat the post
            - ONLY add category at top and hashtags at bottom""",
            expected_output="Category label + original post + hashtags. No repetition.",
            agent=hashtag_agent,
            callback=lambda output: log_step(logger, "HASHTAG_SPECIALIST", "STEP:3 DONE", "Hashtags added ✅")
        )

        crew = Crew(
            agents=[researcher, writer, hashtag_agent],
            tasks=[research_task, writing_task, hashtag_task],
            process=Process.sequential,
            verbose=True
        )

        try:
            crew.kickoff()
        finally:
            cleanup_crew_threads(crew, logger)

        
        # ----------------------------------------------------------------
        # STEP 5: Publish directly in Python
        # ----------------------------------------------------------------
        log_step(logger, "PUBLISHER", "STEP:5 START", "Publishing to Facebook...")

        caption_raw = hashtag_task.output.raw.strip()

        # Get image directly from ImageTool — don't trust the LLM to relay the path
        image_tool = ImageTool()
        image_ref = image_tool._run(topic).strip()  # returns "TEMP_IMAGE_PATH:/path/to/img.jpg"

        if not image_ref.startswith("TEMP_IMAGE_PATH:"):
            log_step(logger, "PUBLISHER", "STEP:5 WARN", f"⚠️ ImageTool returned unexpected: {image_ref}")
            image_ref = "NO_IMAGE"

        # Pass directly into FacebookPostTool — it handles retry, upload, cleanup
        tool_input = f"{image_ref}|||{caption_raw}"
        post_result = facebook_tool._run(tool_input)
        log_step(logger, "PUBLISHER", "STEP:5 DONE", f"Result: {post_result}")
        print(f"\n📣 Facebook result: {post_result}\n")

        # ----------------------------------------------------------------

        elapsed = round(time.time() - start_time, 2)
        log_crew_done(logger, index, len(topics), topic, elapsed)

        if index < len(topics):
            wait_between_items(logger)

    overall_elapsed = round(time.time() - overall_start_time, 2)
    log_step(logger, "SYSTEM", "FINISHED", f"All topics processed! Total duration: {overall_elapsed} seconds")
    print(f"\n🎉 All topics processed and posted in {overall_elapsed} seconds!")


# Register cleanup on exit
atexit.register(cleanup_all_threads)


if __name__ == "__main__":
    run()
