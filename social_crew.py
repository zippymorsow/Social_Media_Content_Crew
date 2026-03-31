from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from ddgs import DDGS
from dotenv import load_dotenv
import requests
import logging
import time
import os

# --- Load .env ---
load_dotenv()
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# --- Logging Setup ---
os.makedirs("logs", exist_ok=True)
log_filename = f"logs/social_crew_{time.strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Model ---
logger.info("Initializing LLM model...")
model = LLM(model="ollama/llama3.1", base_url="http://localhost:11434")
logger.info("LLM model ready!")

# --- Tools ---
class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the web for current information about a topic."

    def _run(self, query: str) -> str:
        logger.info(f"[WebSearch] Searching: {query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results:
                    return "No results found"
                output = ""
                for r in results:
                    output += f"Title: {r['title']}\nSummary: {r['body']}\n\n"
                logger.info(f"[WebSearch] Found {len(results)} results")
                return output
        except Exception as e:
            logger.error(f"[WebSearch] Failed: {str(e)}")
            return f"Search failed: {str(e)}"


class PexelsImageTool(BaseTool):
    name: str = "Pexels Image Search"
    description: str = "Search for a relevant image URL from Pexels. Input should be a short search keyword."

    def _run(self, query: str) -> str:
        logger.info(f"[Pexels] Searching image for: {query}")
        try:
            headers = {"Authorization": PEXELS_API_KEY}
            response = requests.get(
                f"https://api.pexels.com/v1/search?query={query}&per_page=1",
                headers=headers
            )
            data = response.json()
            if data.get("photos"):
                image_url = data["photos"][0]["src"]["large"]
                photographer = data["photos"][0]["photographer"]
                logger.info(f"[Pexels] Found image by {photographer}")
                return f"Image URL: {image_url}\nPhotographer: {photographer}"
            return "No image found"
        except Exception as e:
            logger.error(f"[Pexels] Failed: {str(e)}")
            return f"Image search failed: {str(e)}"


class FacebookPostTool(BaseTool):
    name: str = "Facebook Post"
    description: str = "Post a message with an image to Facebook Page. Input format: IMAGE_URL|||POST_CAPTION"

    def _run(self, input: str) -> str:
        logger.info("[Facebook] Preparing to post...")
        try:
            parts = input.split("|||")
            if len(parts) != 2:
                return "Invalid input format. Use: IMAGE_URL|||POST_CAPTION"

            image_url = parts[0].strip()
            caption = parts[1].strip()

            response = requests.post(
                f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/photos",
                data={
                    "url": image_url,
                    "caption": caption,
                    "access_token": FACEBOOK_PAGE_TOKEN
                }
            )
            result = response.json()
            if "id" in result:
                logger.info(f"[Facebook] Posted successfully! Post ID: {result['id']}")
                return f"Successfully posted to Facebook! Post ID: {result['id']}"
            else:
                logger.error(f"[Facebook] Failed: {result}")
                return f"Facebook post failed: {result}"
        except Exception as e:
            logger.error(f"[Facebook] Error: {str(e)}")
            return f"Error posting to Facebook: {str(e)}"


# --- Initialize Tools ---
web_search_tool = WebSearchTool()
pexels_tool = PexelsImageTool()
facebook_tool = FacebookPostTool()

# --- Define Agents ---
logger.info("Setting up agents...")

researcher = Agent(
    role="Researcher",
    goal="Find the latest and most interesting information about the given topic",
    backstory="You are a curious and thorough researcher who finds the most interesting and relevant facts about any topic. You focus on recent developments and surprising facts.",
    tools=[web_search_tool],
    llm=model,
    verbose=True
)

writer = Agent(
    role="Social Media Writer",
    goal="Write a fun, engaging and informative Facebook post based on the research",
    backstory="""You are a witty and creative social media writer who specializes in Facebook content. 
    You write in a fun, conversational tone that makes people stop scrolling. 
    Your posts are informative but never boring. You use emojis naturally.
    Your posts are between 100-150 words. Always end with a question to encourage engagement.""",
    llm=model,
    verbose=True
)

hashtag_agent = Agent(
    role="Hashtag Specialist",
    goal="Find the best hashtags for the post and categorize it correctly",
    backstory="""You are a social media hashtag expert. You know exactly which hashtags trend and which ones 
    reach the right audience. You always add 5-10 relevant hashtags and correctly categorize 
    the post (Tech, Science, Business, Lifestyle, Entertainment, etc.)""",
    llm=model,
    verbose=True
)

image_agent = Agent(
    role="Image Curator",
    goal="Find the most relevant and eye-catching image for the post from Pexels",
    backstory="You are a visual content curator who knows exactly what image will make a Facebook post stand out. You search for images that are relevant, high quality, and eye-catching.",
    tools=[pexels_tool],
    llm=model,
    verbose=True
)

poster = Agent(
    role="Facebook Publisher",
    goal="Combine the caption, hashtags and image and post to Facebook",
    backstory="You are responsible for publishing the final content to Facebook. You combine the caption, hashtags and image URL into a perfect post and publish it.",
    tools=[facebook_tool],
    llm=model,
    verbose=True
)

logger.info("All agents ready!")

# --- Read Topics from File ---
TOPICS_FILE = "topics.txt"
if not os.path.exists(TOPICS_FILE):
    logger.error(f"topics.txt not found!")
    print("❌ Please create a topics.txt file with one topic per line.")
    exit()

with open(TOPICS_FILE, "r") as f:
    topics = [line.strip() for line in f.readlines() if line.strip()]

if not topics:
    print("❌ topics.txt is empty! Add some topics.")
    exit()

logger.info(f"Found {len(topics)} topics: {topics}")

# --- Process Each Topic ---
for topic in topics:
    print(f"\n🚀 Processing topic: {topic}\n")
    logger.info(f"Starting crew for topic: {topic}")

    research_task = Task(
        description=f"Research this topic thoroughly and find the most interesting recent facts: {topic}",
        expected_output="A detailed summary of the most interesting and recent facts about the topic.",
        agent=researcher
    )

    writing_task = Task(
        description=f"""Using the research, write a fun and engaging Facebook post about: {topic}
        - Fun and conversational tone
        - Use emojis naturally
        - 100-150 words
        - Informative but entertaining
        - End with an engaging question
        - Do NOT include hashtags yet (that's another agent's job)""",
        expected_output="A fun, engaging Facebook post caption without hashtags.",
        agent=writer
    )

    hashtag_task = Task(
        description=f"""Take the written Facebook post and:
        1. Add 5-10 relevant trending hashtags at the end
        2. Add a category label at the very top like: 📌 Category: Technology
        Return the complete post with category and hashtags.""",
        expected_output="Complete post with category label at top and hashtags at bottom.",
        agent=hashtag_agent
    )

    image_task = Task(
        description=f"Search for the best image on Pexels that represents this topic: {topic}. Return the image URL.",
        expected_output="A Pexels image URL that best represents the topic.",
        agent=image_agent
    )

    posting_task = Task(
        description=f"""Combine the image URL and the post caption and post to Facebook.
        Format your input to the Facebook Post tool exactly like this:
        IMAGE_URL|||POST_CAPTION_WITH_HASHTAGS
        Make sure to include the full caption with category and hashtags.""",
        expected_output="Confirmation that the post was published to Facebook with the Post ID.",
        agent=poster
    )

    crew = Crew(
        agents=[researcher, writer, hashtag_agent, image_agent, poster],
        tasks=[research_task, writing_task, hashtag_task, image_task, posting_task],
        process=Process.sequential,
        verbose=True
    )

    start_time = time.time()
    result = crew.kickoff()
    elapsed = round(time.time() - start_time, 2)

    logger.info(f"Topic '{topic}' completed in {elapsed} seconds")
    print(f"\n✅ Done! Topic: '{topic}' posted in {elapsed} seconds")
    print(f"📋 Log: {log_filename}\n")

    # Small delay between topics to avoid rate limits
    if len(topics) > 1:
        logger.info("Waiting 5 seconds before next topic...")
        time.sleep(5)

print("\n🎉 All topics processed and posted!")
