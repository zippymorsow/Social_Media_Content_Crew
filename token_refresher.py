# refresh_token.py
import requests
import os
from dotenv import load_dotenv, set_key

load_dotenv()

APP_ID = os.getenv("FACEBOOK_APP_ID")
APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")
CURRENT_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")

response = requests.get(
    f"https://graph.facebook.com/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": CURRENT_TOKEN
    }
)

new_token = response.json().get("access_token")

if new_token:
    set_key(".env", "FACEBOOK_PAGE_TOKEN", new_token)
    print("Token refreshed successfully!")
else:
    print("Failed to refresh token")