"""
crews/social_crew.py
Researches topics and posts engaging content to Facebook Feed.
"""

import os
import time
from crewai import Task, Crew, Process
from agents.researcher import create_researcher
from agents.writer import create_writer
from agents.hashtag_agent import create_hashtag_agent
from agents.image_agent import create_image_agent
from agents.publisher import create_publisher
from tools.facebook import FacebookPostTool
from config.settings import DATA_DIR, setup_logger, log_step
from utils.helpers import read_lines_from_file, log_crew_start, log_crew_done, wait_between_items

logger = setup_logger("social_crew")


def run():
    log_step(logger, "SYSTEM", "STARTUP", "Initializing Social Media Crew...")

    # --- Initialize tools and agents ---
    facebook_tool = FacebookPostTool()
    researcher    = create_researcher()
    writer        = create_writer()
    hashtag_agent = create_hashtag_agent()
    image_agent   = create_image_agent()
    poster        = create_publisher(facebook_tool)

    log_step(logger, "SYSTEM", "STARTUP", "All 5 agents ready!")

    # --- Read topics ---
    topics = read_lines_from_file(os.path.join(DATA_DIR, "topics.txt"))
    if not topics:
        print("❌ data/topics.txt is missing or empty.")
        return

    log_step(logger, "SYSTEM", "STARTUP", f"Found {len(topics)} topic(s)")

    # --- Process each topic ---
    for index, topic in enumerate(topics, start=1):
        log_crew_start(logger, index, len(topics), topic)
        facebook_tool.current_topic = topic

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

        image_task = Task(
            description=f"""Search for the most visually stunning image for: {topic}
            Return the TEMP_IMAGE_PATH value exactly as returned by the tool.""",
            expected_output="A TEMP_IMAGE_PATH value pointing to the downloaded image.",
            agent=image_agent,
            callback=lambda output: log_step(logger, "IMAGE_CURATOR", "STEP:4 DONE", "Image found ✅")
        )

        posting_task = Task(
            description=f"""You have results from previous agents:
            1. IMAGE PATH from Image Curator (starts with TEMP_IMAGE_PATH:)
            2. POST CAPTION from Hashtag Specialist

            Call the Facebook Post tool ONCE with this EXACT format:
            [ACTUAL TEMP_IMAGE_PATH VALUE]|||[ACTUAL POST CAPTION]

            CRITICAL: Call the tool ONLY ONCE. Use the ACTUAL path — not placeholder text.""",
            expected_output="Confirmation the post was published with Post ID.",
            agent=poster,
            callback=lambda output: log_step(logger, "PUBLISHER", "STEP:5 DONE", "Published ✅")
        )

        crew = Crew(
            agents=[researcher, writer, hashtag_agent, image_agent, poster],
            tasks=[research_task, writing_task, hashtag_task, image_task, posting_task],
            process=Process.sequential,
            verbose=True
        )

        start_time = time.time()
        crew.kickoff()
        elapsed = round(time.time() - start_time, 2)

        log_crew_done(logger, index, len(topics), topic, elapsed)

        if index < len(topics):
            wait_between_items(logger)

    log_step(logger, "SYSTEM", "FINISHED", "All topics processed!")
    print("\n🎉 All topics processed and posted!")

 

if __name__ == "__main__":
    run()
