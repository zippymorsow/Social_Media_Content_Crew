from crewai import Agent, Task, Crew, Process, LLM
from ddgs import DDGS
from crewai.tools import BaseTool
import logging
import time
import os

# --- Logging Setup ---
os.makedirs("logs", exist_ok=True)
log_filename = f"logs/crew_{time.strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename),   # save to file
        logging.StreamHandler()              # also print to terminal
    ]
)
logger = logging.getLogger(__name__)

# --- Model ---
logger.info("Initializing LLM model...")
model = LLM(model="ollama/llama3.1", base_url="http://localhost:11434")
logger.info("LLM model ready!")

# --- Web Search Tool ---
class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the web for current information. Input should be a search query."

    def _run(self, query: str) -> str:
        logger.info(f"[WebSearch] Searching for: {query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results:
                    logger.warning("[WebSearch] No results found")
                    return "No results found"
                output = ""
                for r in results:
                    output += f"Title: {r['title']}\n"
                    output += f"Summary: {r['body']}\n\n"
                logger.info(f"[WebSearch] Found {len(results)} results")
                return output
        except Exception as e:
            logger.error(f"[WebSearch] Failed: {str(e)}")
            return f"Search failed: {str(e)}"

web_search_tool = WebSearchTool()

# --- Define Agents ---
logger.info("Setting up agents...")

researcher = Agent(
    role="Researcher",
    goal="Find comprehensive and accurate information about the given topic",
    backstory="You are an expert researcher who finds detailed and reliable information from the web. You always search multiple angles of a topic.",
    tools=[web_search_tool],
    llm=model,
    verbose=True
)

writer = Agent(
    role="Report Writer",
    goal="Write a clear, structured and detailed report based on the research provided",
    backstory="You are a professional report writer who transforms raw research into well structured, easy to read reports with clear sections and key insights.",
    llm=model,
    verbose=True
)

editor = Agent(
    role="Editor",
    goal="Review and polish the report to make it professional and error free",
    backstory="You are a meticulous editor who ensures reports are clear, concise, well formatted and free of errors. You improve flow and readability.",
    llm=model,
    verbose=True
)

logger.info("All agents ready!")

# --- Get Topic from User ---
topic = input("\n📝 What topic should the crew research? ")
logger.info(f"Topic selected: {topic}")

# --- Define Tasks ---
research_task = Task(
    description=f"Research the following topic thoroughly: {topic}. Search for recent news, key facts, important people or companies involved, and any notable developments. Compile all findings.",
    expected_output="A comprehensive collection of facts, news, and information about the topic with sources.",
    agent=researcher
)

writing_task = Task(
    description=f"Using the research provided, write a detailed and well structured report about: {topic}. Include sections like Introduction, Key Facts, Recent Developments, and Conclusion.",
    expected_output="A full written report with clear sections and headings about the topic.",
    agent=writer
)

editing_task = Task(
    description="Review the written report, fix any errors, improve clarity and flow, and make it professional and polished. Output the final version of the report.",
    expected_output="A polished, professional, error-free final report ready for reading.",
    agent=editor
)

# --- Assemble the Crew ---
crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, writing_task, editing_task],
    process=Process.sequential,
    verbose=True
)

# --- Run the Crew ---
logger.info("Crew is starting...")
start_time = time.time()

print(f"\n🚀 Crew is starting research on: {topic}\n")
result = crew.kickoff()

end_time = time.time()
elapsed = round(end_time - start_time, 2)
logger.info(f"Crew finished in {elapsed} seconds")

# --- Save the Report ---
filename = topic.replace(" ", "_").lower() + "_report.txt"
with open(filename, "w") as f:
    f.write(str(result))

logger.info(f"Report saved to: {filename}")
logger.info(f"Log saved to: {log_filename}")

print(f"\n✅ Report saved to: {filename}")
print(f"📋 Log saved to: {log_filename}")
print(f"⏱️ Completed in: {elapsed} seconds")
print(f"\n📄 Final Report:\n")
print(result)