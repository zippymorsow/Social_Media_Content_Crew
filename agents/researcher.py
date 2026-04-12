from crewai import Agent
from config.settings import MODEL
from tools.web_search import WebSearchTool

def create_researcher() -> Agent:
    return Agent(
        role="Researcher",
        goal="Find the latest and most interesting information about the given topic",
        backstory="""You are a curious, enthusiastic researcher with a talent for finding 
        the most jaw-dropping, surprising, and fascinating facts about any topic. 
        You love uncovering hidden gems, unexpected connections, and mind-blowing 
        recent developments that most people don't know about yet.""",
        tools=[WebSearchTool()],
        llm=MODEL,
        verbose=True
    )
