from crewai import Agent
from config.settings import MODEL
from tools.facebook import FacebookPostTool, FacebookAffirmationTool

def create_publisher(facebook_tool: FacebookPostTool) -> Agent:
    return Agent(
        role="Facebook Publisher",
        goal="Combine the caption, hashtags and image and publish the perfect post to Facebook",
        backstory="""You are the final gatekeeper of quality. You make sure the post 
        looks perfect before publishing. You combine the image path and caption carefully,
        always using the exact format required. You call the tool ONLY ONCE.""",
        tools=[facebook_tool],
        llm=MODEL,
        verbose=True
    )

def create_affirmation_publisher() -> Agent:
    return Agent(
        role="Affirmation Publisher",
        goal="Publish the affirmation image to Facebook Story (MyDay) and Feed",
        backstory="""You are responsible for publishing affirmation content to both 
        Facebook Story (MyDay) and the Page Feed. You always use the exact 
        TEMP_IMAGE_PATH value from the Image Creator and the caption from the 
        Affirmation Writer. You call the tool ONLY ONCE.""",
        tools=[FacebookAffirmationTool()],
        llm=MODEL,
        verbose=True
    )
