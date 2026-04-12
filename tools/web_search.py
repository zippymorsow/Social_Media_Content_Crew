from crewai.tools import BaseTool
from ddgs import DDGS
from config.settings import setup_logger, log_step

logger = setup_logger("web_search")

class WebSearchTool(BaseTool):
    name: str = "Web Search"
    description: str = "Search the web for current information about a topic."

    def _run(self, query: str) -> str:
        log_step(logger, "RESEARCHER", "TOOL:WebSearch", f"Searching: {query}")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                if not results:
                    log_step(logger, "RESEARCHER", "TOOL:WebSearch", "No results found")
                    return "No results found"
                output = ""
                for r in results:
                    output += f"Title: {r['title']}\nSummary: {r['body']}\n\n"
                log_step(logger, "RESEARCHER", "TOOL:WebSearch", f"Found {len(results)} results ✅")
                return output
        except Exception as e:
            log_step(logger, "RESEARCHER", "TOOL:WebSearch", f"FAILED: {str(e)}")
            return f"Search failed: {str(e)}"
