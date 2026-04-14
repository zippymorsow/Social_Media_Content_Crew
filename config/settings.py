import os
import logging
import time
from dotenv import load_dotenv
from crewai import LLM

# --- Load .env ---
# load_dotenv()
# TO — always find .env relative to this file's location
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# --- Facebook ---
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

# --- Pexels ---
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# --- Ollama Model ---
MODEL = LLM(model="ollama/llama3.1", base_url="http://localhost:11434")

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TEMP_IMAGE_DIR = os.path.join(BASE_DIR, "temp_image")
DATA_DIR = os.path.join(BASE_DIR, "data")

# --- Ensure directories exist ---
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# --- Logging ---
def setup_logger(name: str) -> logging.Logger:
    log_filename = os.path.join(LOGS_DIR, f"{name}_{time.strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)

def log_step(logger, agent_name: str, step: str, message: str):
    logger.info(f"[{agent_name}] [{step}] {message}")
