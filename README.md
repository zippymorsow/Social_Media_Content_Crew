# Social Media Content Crew (Agentic AI)

## 🚀 Project Overview

This project aims to build an agentic social media crew using CREW AI concepts and automation. It is designed to help creators and brands generate, manage, and publish social media content efficiently by leveraging intelligent agents and prompt workflows.

The repository currently includes:
- `chat.py` - Chat interaction and agent orchestration logic
- `crew.py` - Crew management and high-level agent coordination
- `social_crew.py` - Social media content creation and scheduling workflows
- `topics.txt` / `topics - copy.txt` - Topic seed lists for content generation
- `logs/` - Runtime logs and status tracking
- Tokens for FB/Pexels (private) in text files for API integrations

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

4. Configure API keys:
- `FB-token-the AI Content Crew.txt` (Facebook/Meta API key)
- `pexel token-the AI Content Crew.txt` (Pexels API key)

Ensure those credentials are stored securely and not committed to source control. Exclude text files with "token" in the filename from repository tracking (via `.gitignore`).

## ▶️ Usage

Run main scripts as needed:

```bash
python crew.py
python social_crew.py
python chat.py
```

Use `topics.txt` to provide topic ideas for content generation, and review generated output in `logs/`.

## 🧩 Project Structure

- `chat.py`: Prompt/response pipeline, agent routing.
- `crew.py`: Manager for agent workflows and task assignment.
- `social_crew.py`: Social media-specific routines (post composition, scheduling).
- `topics.txt`: Seed topic outlines for posts.
- `logs/`: Execution logs and audit trail.

## 🔐 Security

- Do not commit API tokens.
- Add `.gitignore` entries for token files and `logs/` if needed.

## ✨ Next Steps

- Add a consolidated settings/config file (e.g., `.env` or `config.json`).
- Build CLI options for platform target and cadence.
- Add unit tests for key workflow functions.

## 📄 License

Add your license information here (e.g., MIT, Apache 2.0).