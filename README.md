# Social Media Content Crew (Agentic AI)

## 🚀 Project Overview

This project aims to build an agentic social media crew using CREW AI concepts and automation. It is designed to help creators and brands generate, manage, and publish social media content efficiently by leveraging intelligent agents and prompt workflows.

The repository currently includes:
- `agents/` - Individual agent implementations for various tasks
- `config/` - Configuration settings
- `crews/` - Crew definitions for multi-agent workflows
- `data/` - Data files for content generation
- `logs/` - Runtime logs and status tracking
- `temp_image/` - Temporary image storage
- `tools/` - Utility tools for integrations
- `utils/` - Helper utilities
- `requirements.txt` - Python dependencies

## 🧠 Goals

- Generate social media post ideas (text, images, captions)
- Maintain consistent brand voice across platforms
- Automate post scheduling and publishing
- Track performance and adapt to audience feedback

## 🛠️ Setup

1. Clone the repository.
2. Create a Python virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure API keys in `config/settings.py`:
- Facebook/Meta API key
- Pexels API key

Ensure credentials are stored securely and not committed to source control.

## ▶️ Usage
### Social Crew
Generate engaging social media content and post to Facebook Feed.

**How to use:**
1. Add topics to `data/topics.txt` (one topic per line)
2. Run the crew:
   ```bash
   python crews/social_crew.py
   ```
3. The crew will:
   - **Research** each topic and gather fascinating facts
   - **Write** a vibrant, energetic Facebook post (100-150 words)
   - **Generate hashtags** (8-10) and categorize the post
   - **Post** to your Facebook Feed

**Output:** Check `logs/` for execution details and verify posts on your Facebook page.

### Affirmation Crew
Create warm, uplifting affirmation content with custom images and post to Facebook Stories & Feed.

**How to use:**
1. Add affirmations to `data/affirmations.txt` (one affirmation per line)
2. Run the crew:
   ```bash
   python crews/affirmation_crew.py
   ```
3. The crew will:
   - **Write** an expanded, warm affirmation message (2-3 sentences)
   - **Create** a visually appealing image with Pillow
   - **Publish** to both Facebook Story (MyDay) and Feed

**Output:** Check `logs/` for execution details and see posts on your Facebook page.

## 📱 Social Media Channels

Follow and interact with the crew's managed Facebook page:
- **Facebook:** [Visit the Page](https://www.facebook.com/profile.php?id=61578545202188)

## 🧩 Project Structure

- `agents/`: Individual agent implementations
  - `hashtag_agent.py`: Handles hashtag generation
  - `image_agent.py`: Manages image-related tasks
  - `publisher.py`: Handles publishing to social media
  - `researcher.py`: Conducts research for content
  - `writer.py`: Generates written content
- `config/`: Configuration files
  - `settings.py`: Application settings and API keys
- `crews/`: Crew definitions for multi-agent workflows
  - `affirmation_crew.py`: Crew for affirmation content generation
  - `social_crew.py`: Crew for social media content creation
- `data/`: Data files for content generation
  - `affirmations.txt`: Affirmation content seeds
  - `topics.txt`: Topic lists for posts
- `logs/`: Execution logs and audit trail
- `temp_image/`: Temporary image storage
- `tools/`: Utility tools for integrations
  - `affirmation_image.py`: Image tools for affirmations
  - `facebook.py`: Facebook integration
  - `image_tool.py`: General image tools
  - `web_search.py`: Web search functionality
- `utils/`: Helper utilities
  - `helpers.py`: Helper functions
- `requirements.txt`: Python dependencies

## 🔐 Security

- Do not commit API tokens in `config/settings.py`.
- Ensure `.gitignore` excludes sensitive files and `logs/`.

## ✨ Next Steps

- Build CLI options for platform target and cadence.
- Add unit tests for key workflow functions.
- Expand agent capabilities for additional social media platforms.

## 📄 License

Add your license information here (e.g., MIT, Apache 2.0).