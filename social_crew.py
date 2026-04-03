from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from ddgs import DDGS
from dotenv import load_dotenv
import requests
import logging
import time
import os
import random
import re
import uuid

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
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def log_step(agent_name, step, message):
    """Structured agent step logger"""
    logger.info(f"[{agent_name}] [{step}] {message}")

# --- Model ---
log_step("SYSTEM", "STARTUP", "Initializing LLM model...")
model = LLM(model="ollama/llama3.1", base_url="http://localhost:11434")
log_step("SYSTEM", "STARTUP", "LLM model ready!")

# ============================================================
# TOOLS
# ============================================================

class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the web for current information about a topic."

    def _run(self, query: str) -> str:
        log_step("RESEARCHER", "TOOL:WebSearch", f"Searching: {query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results:
                    log_step("RESEARCHER", "TOOL:WebSearch", "No results found")
                    return "No results found"
                output = ""
                for r in results:
                    output += f"Title: {r['title']}\nSummary: {r['body']}\n\n"
                log_step("RESEARCHER", "TOOL:WebSearch", f"Found {len(results)} results ✅")
                return output
        except Exception as e:
            log_step("RESEARCHER", "TOOL:WebSearch", f"FAILED: {str(e)}")
            return f"Search failed: {str(e)}"


class ImageTool(BaseTool):
    name: str = "Image Search"
    description: str = "Get a relevant image for a topic. Input should be a short search keyword."

    def _get_pexels_image(self, query: str):
        """Try Pexels first"""
        log_step("IMAGE_CURATOR", "TOOL:Pexels", f"Trying Pexels for: {query}")
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
            log_step("IMAGE_CURATOR", "TOOL:Pexels", f"✅ Got image by {photo['photographer']}")
            return {
                "bytes": img_response.content,
                "source": "pexels",
                "credit": photo["photographer"]
            }
        return None

    def _get_unsplash_image(self, query: str):
        """Fallback to Unsplash"""
        log_step("IMAGE_CURATOR", "TOOL:Unsplash", f"Trying Unsplash for: {query}")
        keyword = query.replace(" ", ",")
        seed = random.randint(1, 9999)
        url = f"https://source.unsplash.com/1200x630/?{keyword}&sig={seed}"
        response = requests.get(url, timeout=10, allow_redirects=True)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            log_step("IMAGE_CURATOR", "TOOL:Unsplash", "✅ Got Unsplash image")
            return {
                "bytes": response.content,
                "source": "unsplash",
                "credit": "Unsplash"
            }
        return None

    def _try_get_image(self, query: str):
        """Try Pexels then Unsplash"""
        image = None
        try:
            image = self._get_pexels_image(query)
        except Exception as e:
            log_step("IMAGE_CURATOR", "TOOL:Image", f"Pexels failed: {str(e)} — trying Unsplash...")

        if not image:
            try:
                image = self._get_unsplash_image(query)
            except Exception as e:
                log_step("IMAGE_CURATOR", "TOOL:Image", f"Unsplash failed: {str(e)}")

        return image

    def _run(self, query: str) -> str:
        log_step("IMAGE_CURATOR", "TOOL:Image", f"Finding image for: {query}")

        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            log_step("IMAGE_CURATOR", "TOOL:Image", f"Attempt {attempt}/{MAX_RETRIES}...")

            image = self._try_get_image(query)

            if not image:
                log_step("IMAGE_CURATOR", "TOOL:Image", f"❌ Both sources failed on attempt {attempt}")
                time.sleep(2)
                continue

            # --- Save to temp file ---
            try:
                temp_path = f"temp_image_{int(time.time())}_{uuid.uuid4().hex[:8]}.jpg"
                with open(temp_path, "wb") as f:
                    f.write(image["bytes"])

                # Validate file
                if not os.path.exists(temp_path):
                    log_step("IMAGE_CURATOR", "TOOL:Image", "❌ File failed to save — retrying...")
                    continue

                file_size = os.path.getsize(temp_path)
                if file_size < 1000:
                    log_step("IMAGE_CURATOR", "TOOL:Image", f"❌ File too small ({file_size} bytes) — retrying...")
                    os.remove(temp_path)
                    continue

                log_step("IMAGE_CURATOR", "TOOL:Image",
                    f"✅ Image saved: {temp_path} | Size: {file_size} bytes | Source: {image['source']} | Credit: {image['credit']}")
                return f"TEMP_IMAGE_PATH:{temp_path}"

            except Exception as e:
                log_step("IMAGE_CURATOR", "TOOL:Image", f"❌ Error saving image: {str(e)} — retrying...")
                time.sleep(2)
                continue

        # All retries exhausted
        log_step("IMAGE_CURATOR", "TOOL:Image", f"❌ All {MAX_RETRIES} attempts failed")
        return "NO_IMAGE"


class FacebookPostTool(BaseTool):
    name: str = "Facebook Post"
    description: str = "Post a message with an image to Facebook Page. Input format: TEMP_IMAGE_PATH:filename.jpg|||POST_CAPTION"
    current_topic: str = ""

    def clean_caption(self, text):
        # Fix literal \n to real newlines
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

    def _post_with_image(self, temp_path: str, caption: str):
        """Upload image file and post to Facebook"""
        with open(temp_path, "rb") as img_file:
            safe_caption = caption.encode('utf-16', 'surrogatepass').decode('utf-16')
            response = requests.post(
                f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos",
                params={"access_token": FACEBOOK_PAGE_TOKEN},
                data={"caption": safe_caption.encode('utf-8', 'surrogatepass'), "published": True},
                files={"source": ("image.jpg", img_file, "image/jpeg")}
            )
        return response

    def _post_text_only(self, caption: str):
        """Post text only when no image available"""
        safe_caption = caption.encode('utf-16', 'surrogatepass').decode('utf-16')
        response = requests.post(
            f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/feed",
            params={"access_token": FACEBOOK_PAGE_TOKEN},
            json={"message": safe_caption, "published": True}
        )
        return response

    def _run(self, input: str) -> str:
        log_step("PUBLISHER", "TOOL:Facebook", "Preparing to post...")
        log_step("PUBLISHER", "DEBUG", f"Raw input received: {input[:200]}")

        try:
            parts = input.split("|||")
            if len(parts) != 2:
                log_step("PUBLISHER", "TOOL:Facebook", "ERROR: Invalid input format")
                return "Invalid input format. Use: TEMP_IMAGE_PATH:filename.jpg|||POST_CAPTION"

            image_url = parts[0].strip()
            caption = self.clean_caption(parts[1].strip())

            log_step("PUBLISHER", "TOOL:Facebook", f"Page ID: {FACEBOOK_PAGE_ID}")
            log_step("PUBLISHER", "TOOL:Facebook", f"Image source: {image_url[:60]}...")
            log_step("PUBLISHER", "TOOL:Facebook", f"Caption preview: {caption[:80]}...")

            # --------------------------------------------------------
            # Case 1: Temp image file from ImageTool
            # --------------------------------------------------------
            if image_url.startswith("TEMP_IMAGE_PATH:"):
                temp_path = image_url.replace("TEMP_IMAGE_PATH:", "").strip()
                log_step("PUBLISHER", "TOOL:Facebook", f"Looking for temp file: {temp_path}")

                # If file not found — retry ImageTool up to 3 times
                if not os.path.exists(temp_path):
                    log_step("PUBLISHER", "TOOL:Facebook", "⚠️ Temp file not found — retrying ImageTool...")

                    image_tool = ImageTool()
                    MAX_IMAGE_RETRIES = 3
                    new_temp_path = None

                    for retry in range(1, MAX_IMAGE_RETRIES + 1):
                        log_step("PUBLISHER", "TOOL:Facebook", f"Image retry {retry}/{MAX_IMAGE_RETRIES}...")
                        new_result = image_tool._run(self.current_topic or "nature")

                        if new_result.startswith("TEMP_IMAGE_PATH:"):
                            new_temp_path = new_result.replace("TEMP_IMAGE_PATH:", "").strip()
                            log_step("PUBLISHER", "TOOL:Facebook", f"✅ Got new image on retry {retry}: {new_temp_path}")
                            break
                        else:
                            log_step("PUBLISHER", "TOOL:Facebook", f"❌ Retry {retry} failed")
                            time.sleep(2)

                    if new_temp_path:
                        temp_path = new_temp_path
                    else:
                        # All retries failed — post text only
                        log_step("PUBLISHER", "TOOL:Facebook", "❌ All image retries failed — posting text only")
                        response = self._post_text_only(caption)
                        result = response.json()
                        if "id" in result:
                            log_step("PUBLISHER", "TOOL:Facebook", f"Posted text only! Post ID: {result['id']} ✅")
                            return f"Successfully posted (text only)! Post ID: {result['id']}"
                        else:
                            log_step("PUBLISHER", "TOOL:Facebook", f"FAILED: {result}")
                            return f"Facebook post failed: {result}"

                # Upload image and post
                log_step("PUBLISHER", "TOOL:Facebook", f"Uploading image: {temp_path}")
                response = self._post_with_image(temp_path, caption)

                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    log_step("PUBLISHER", "TOOL:Facebook", f"Temp file cleaned up ✅")

            # --------------------------------------------------------
            # Case 2: No image available
            # --------------------------------------------------------
            elif image_url == "NO_IMAGE":
                log_step("PUBLISHER", "TOOL:Facebook", "No image — posting text only")
                response = self._post_text_only(caption)

            # --------------------------------------------------------
            # Case 3: Direct URL fallback
            # --------------------------------------------------------
            else:
                log_step("PUBLISHER", "TOOL:Facebook", "Using direct image URL")
                safe_caption = caption.encode('utf-16', 'surrogatepass').decode('utf-16')
                response = requests.post(
                    f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/photos",
                    params={"access_token": FACEBOOK_PAGE_TOKEN},
                    json={"url": image_url, "caption": safe_caption, "published": True}
                )

            # --------------------------------------------------------
            # Check result
            # --------------------------------------------------------
            result = response.json()
            if "id" in result:
                log_step("PUBLISHER", "TOOL:Facebook", f"Posted successfully! Post ID: {result['id']} ✅")
                return f"Successfully posted! Post ID: {result['id']}"
            else:
                log_step("PUBLISHER", "TOOL:Facebook", f"FAILED: {result}")
                return f"Facebook post failed: {result}"

        except Exception as e:
            log_step("PUBLISHER", "TOOL:Facebook", f"ERROR: {str(e)}")
            return f"Error posting to Facebook: {str(e)}"


# ============================================================
# INITIALIZE TOOLS
# ============================================================
web_search_tool = WebSearchTool()
image_tool = ImageTool()
facebook_tool = FacebookPostTool()

# ============================================================
# DEFINE AGENTS
# ============================================================
log_step("SYSTEM", "STARTUP", "Setting up agents...")

researcher = Agent(
    role="Researcher",
    goal="Find the latest and most interesting information about the given topic",
    backstory="""You are a curious, enthusiastic researcher with a talent for finding 
    the most jaw-dropping, surprising, and fascinating facts about any topic. 
    You love uncovering hidden gems, unexpected connections, and mind-blowing 
    recent developments that most people don't know about yet.""",
    tools=[web_search_tool],
    llm=model,
    verbose=True
)

writer = Agent(
    role="Social Media Writer",
    goal="Write a vibrant, whimsical, and lively Facebook post that stops people mid-scroll",
    backstory="""You are a wildly creative social media writer with a cosmic, whimsical personality. 
    Your writing style is energetic, playful, and full of life — like a mix between a 
    stand-up comedian and a passionate professor. 
    You use vivid language, unexpected metaphors, and genuine enthusiasm.
    You LOVE using emojis expressively and naturally throughout the text.
    Your posts feel alive, warm, and human — never corporate or flat.
    Posts are 100-150 words. Always end with a fun engaging question.
    NEVER write in a boring, flat, or generic way. Make every word count!
    Example tone: "Hold on to your seats because this blew MY mind! 🤯✨"
    """,
    llm=model,
    verbose=True
)

hashtag_agent = Agent(
    role="Hashtag Specialist",
    goal="Add perfectly curated trending hashtags and a category that matches the post energy",
    backstory="""You are a social media hashtag wizard who knows exactly which tags 
    will reach the RIGHT audience and boost engagement. You match the energy of the post —
    if it's cosmic and whimsical, your hashtags reflect that vibe too!
    You always add exactly 8-10 hashtags — a mix of broad popular ones and 
    niche specific ones for maximum reach.
    You add a fun category label at the top like: ✨ Category: Mind-Blowing Science
    Make the category label itself exciting, not just generic words.
    IMPORTANT: You NEVER rewrite the original post content. You only ADD the category 
    at the beginning and hashtags at the end.""",
    llm=model,
    verbose=True
)

image_agent = Agent(
    role="Image Curator",
    goal="Find the most visually stunning and relevant image that matches the post's energy",
    backstory="""You are a visual storyteller who knows that the RIGHT image can make 
    a post go viral. You search for images that are not just relevant but also 
    visually striking, colorful, and emotionally engaging. 
    You think about what image would make someone stop scrolling and say WOW.""",
    tools=[image_tool],
    llm=model,
    verbose=True
)

poster = Agent(
    role="Facebook Publisher",
    goal="Combine the caption, hashtags and image and publish the perfect post to Facebook",
    backstory="""You are the final gatekeeper of quality. You make sure the post 
    looks perfect before publishing. You combine the image path and caption carefully,
    always using the exact format required.""",
    tools=[facebook_tool],
    llm=model,
    verbose=True
)

log_step("SYSTEM", "STARTUP", "All 5 agents ready!")

# ============================================================
# READ TOPICS
# ============================================================
TOPICS_FILE = "topics.txt"
if not os.path.exists(TOPICS_FILE):
    log_step("SYSTEM", "STARTUP", "ERROR: topics.txt not found!")
    print("❌ Please create a topics.txt file with one topic per line.")
    exit()

with open(TOPICS_FILE, "r") as f:
    topics = [line.strip() for line in f.readlines() if line.strip()]

if not topics:
    print("❌ topics.txt is empty! Add some topics.")
    exit()

log_step("SYSTEM", "STARTUP", f"Found {len(topics)} topic(s): {topics}")

# ============================================================
# PROCESS EACH TOPIC
# ============================================================
for index, topic in enumerate(topics, start=1):
    log_step("SYSTEM", f"TOPIC {index}/{len(topics)}", f"Starting: '{topic}'")
    print(f"\n🚀 Processing topic {index}/{len(topics)}: {topic}\n")

    # Pass current topic to facebook_tool for image retry fallback
    facebook_tool.current_topic = topic

    research_task = Task(
        description=f"""Research this topic and find the most surprising, fascinating, 
        and mind-blowing facts about it: {topic}
        Focus on: recent news, unexpected facts, wow moments, human stories.""",
        expected_output="A rich collection of fascinating, surprising facts and recent news about the topic.",
        agent=researcher,
        callback=lambda output: log_step("RESEARCHER", "STEP:1 DONE", "Research complete ✅")
    )

    writing_task = Task(
        description=f"""Using the research, write a VIBRANT, WHIMSICAL, LIVELY Facebook post about: {topic}
        IMPORTANT RULES:
        - Write with ENERGY and ENTHUSIASM — make it feel alive!
        - Use emojis expressively throughout (not just at the end)
        - Use vivid, colorful language and unexpected comparisons
        - 100-150 words maximum
        - End with a fun, engaging question that sparks conversation
        - Do NOT include hashtags (another agent handles that)
        - NEVER be flat, generic, or corporate sounding
        - Make the reader feel something — excitement, curiosity, wonder!""",
        expected_output="A vibrant, whimsical, lively Facebook post caption bursting with personality.",
        agent=writer,
        callback=lambda output: log_step("WRITER", "STEP:2 DONE", "Post written ✅")
    )

    hashtag_task = Task(
        description=f"""You will receive a written Facebook post. 
        YOUR ONLY JOB is to:
        1. Add ONE category label at the very TOP like: ✨ Category: Mind-Blowing Science
        2. Add 8-10 hashtags at the very BOTTOM
        
        STRICT RULES:
        - DO NOT rewrite the post
        - DO NOT change any words in the post
        - DO NOT repeat the post content
        - ONLY add the category label at top and hashtags at bottom
        - Return format must be EXACTLY:
        
        [CATEGORY LABEL HERE]
        
        [ORIGINAL POST UNCHANGED HERE]
        
        [HASHTAGS HERE]
        
        Nothing else. No extra text. No repetition.""",
        expected_output="Category label at top + original post unchanged in middle + hashtags at bottom.",
        agent=hashtag_agent,
        callback=lambda output: log_step("HASHTAG_SPECIALIST", "STEP:3 DONE", "Hashtags added ✅")
    )

    image_task = Task(
        description=f"""Search for the most visually stunning image for this topic: {topic}
        Think about what image would make someone STOP scrolling.
        Return the TEMP_IMAGE_PATH value exactly as returned by the tool.""",
        expected_output="A TEMP_IMAGE_PATH value pointing to the downloaded image file.",
        agent=image_agent,
        callback=lambda output: log_step("IMAGE_CURATOR", "STEP:4 DONE", "Image found ✅")
    )

    posting_task = Task(
        description=f"""You have two pieces of information from previous tasks:
        1. The IMAGE PATH from the Image Curator agent (starts with TEMP_IMAGE_PATH:)
        2. The POST CAPTION from the Hashtag Specialist agent

        Call the Facebook Post tool with this EXACT format:
        [THE ACTUAL TEMP_IMAGE_PATH VALUE]|||[THE ACTUAL POST CAPTION]

        IMPORTANT RULES:
        - Use the ACTUAL TEMP_IMAGE_PATH value — NOT the words 'IMAGE_URL' or 'TEMP_IMAGE_PATH' as placeholders
        - Copy the exact path string from Image Curator output
        - Do NOT substitute with placeholder text
        - Do NOT call the tool more than once
        - Always use the lastest ACTUAL TEMP_IMAGE_PATH VALUE and lastest ACTUAL POST CAPTION""",
        expected_output="Confirmation that the post was published to Facebook with Post ID.",
        agent=poster,
        callback=lambda output: log_step("PUBLISHER", "STEP:5 DONE", "Publishing complete ✅")
    )

    crew = Crew(
        agents=[researcher, writer, hashtag_agent, image_agent, poster],
        tasks=[research_task, writing_task, hashtag_task, image_task, posting_task],
        process=Process.sequential,
        verbose=True
    )

    log_step("SYSTEM", f"TOPIC {index}", "Crew kickoff starting...")
    start_time = time.time()
    result = crew.kickoff()
    elapsed = round(time.time() - start_time, 2)

    log_step("SYSTEM", f"TOPIC {index}", f"Completed in {elapsed} seconds ✅")
    print(f"\n✅ Done! Topic: '{topic}' completed in {elapsed} seconds")
    print(f"📋 Log saved to: {log_filename}\n")

    if len(topics) > 1:
        log_step("SYSTEM", "DELAY", "Waiting 5 seconds before next topic...")
        time.sleep(5)

log_step("SYSTEM", "FINISHED", "All topics processed!")
print("\n🎉 All topics processed and posted!")