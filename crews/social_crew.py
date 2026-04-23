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
from agents.ideator import create_ideator
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


def generate_ideator_topic(ideator):
    ideator_task = Task(
        description="""Produce exactly one short topic title, using one of these themes:
        Magical Thoughts, Cosmic Whimsy, Joyful Inspirations, Daily Magic / Miracles,
        Psychic, Astrology, Divination, Meditation, Chakras, Spiritual Healing.

        Write as if you are a psychic reader, tarot reader, white witch, positive motivator,
        divination coach, and spiritual healer. Output only the topic title, with no explanation.
        """,
        expected_output="A single short topic title inspired by mystical, magical, and spiritual themes.",
        agent=ideator,
        callback=lambda output: log_step(logger, "IDEATOR", "STEP:1 DONE", "Ideator topic generated ✅")
    )

    ideator_crew = Crew(
        agents=[ideator],
        tasks=[ideator_task],
        process=Process.sequential,
        verbose=True
    )

    try:
        topic_result = ideator_crew.kickoff()
    finally:
        cleanup_crew_threads(ideator_crew, logger)

    result = str(topic_result).strip() if topic_result is not None else ""
    if not result:
        return "Cosmic Magic and Daily Miracles"

    result = result.splitlines()[0].strip()
    if result.startswith('"') and result.endswith('"'):
        result = result[1:-1].strip()
    return result


def run():
    log_step(logger, "SYSTEM", "STARTUP", "Initializing Social Media Crew...")

    # --- Initialize Facebook tool ---
    facebook_tool = FacebookPostTool()

    # --- Read topics ---
    file_topics = read_lines_from_file(os.path.join(DATA_DIR, "topics.txt"))
    if not file_topics:
        logger.warning("data/topics.txt is missing or empty. Ideator will supply the topic.")
        file_topics = []

    log_step(logger, "SYSTEM", "STARTUP", f"Found {len(file_topics)} topic(s) in data/topics.txt")

    # --- Initialize ideator ---
    ideator = create_ideator()

    # --- Process each topic set ---
    overall_start_time = time.time()
    source_topics = file_topics if file_topics else [None]
    for index, topic in enumerate(source_topics, start=1):
        start_time = time.time()
        ideator_topic = generate_ideator_topic(ideator)
        effective_topic = topic and ideator_topic
        log_crew_start(logger, index, len(source_topics), effective_topic)

        # Recreate agents fresh each iteration to avoid stale state
        facebook_tool.current_topic = effective_topic
        researcher    = create_researcher()
        writer        = create_writer()
        hashtag_agent = create_hashtag_agent()

        log_step(logger, "SYSTEM", "STARTUP", "All agents ready!")

        combined_topic_prompt = f"Primary idea: {ideator_topic}."
        if topic:
            combined_topic_prompt += f"\nAdditional topic from data/topics.txt: {topic}."

        research_task = Task(
            description=f"""Research the topic ideas and find the most surprising, fascinating,
            and mind-blowing facts about them.
            {combined_topic_prompt}
            Focus on: recent news, unexpected facts, wow moments, human stories.
            Always treat the ideator topic as the default source of inspiration.""",
            expected_output="A rich collection of fascinating facts and recent news.",
            agent=researcher,
            callback=lambda output: log_step(logger, "RESEARCHER", "STEP:1 DONE", "Research complete ✅")
        )

        writing_task = Task(
            description=f"""Using the research, write a VIBRANT, WHIMSICAL, LIVELY Facebook post inspired by the ideator topic: {ideator_topic}
            {f'Also include the data/topics.txt topic: {topic}' if topic else ''}
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

        # Get image directly from ImageTool — use the effective topic so the image matches the selected content.
        image_tool = ImageTool()
        image_ref = image_tool._run(effective_topic).strip()  # returns "TEMP_IMAGE_PATH:/path/to/img.jpg"

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
        log_crew_done(logger, index, len(source_topics), effective_topic, elapsed)

        if index < len(source_topics):
            wait_between_items(logger)

    overall_elapsed = round(time.time() - overall_start_time, 2)
    log_step(logger, "SYSTEM", "FINISHED", f"All topics processed! Total duration: {overall_elapsed} seconds")
    print(f"\n🎉 All topics processed and posted in {overall_elapsed} seconds!")


# Register cleanup on exit
atexit.register(cleanup_all_threads)


if __name__ == "__main__":
    run()
