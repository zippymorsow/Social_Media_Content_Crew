from crewai import Agent
from config.settings import MODEL
from tools.image_tool import ImageTool

def create_image_agent() -> Agent:
    return Agent(
        role="Image Curator",
        goal="Find the most visually stunning and relevant image that matches the post's energy",
        backstory="""You are a visual storyteller who knows that the RIGHT image can make 
        a post go viral. You search for images that are not just relevant but also 
        visually striking, colorful, and emotionally engaging. 
        You think about what image would make someone stop scrolling and say WOW.""",
        tools=[ImageTool()],
        llm=MODEL,
        verbose=True
    )
