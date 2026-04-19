import requests
from config.settings import FACEBOOK_PAGE_ID, FACEBOOK_PAGE_TOKEN, setup_logger, log_step

PAGE_ID = FACEBOOK_PAGE_ID
PAGE_TOKEN = FACEBOOK_PAGE_TOKEN

# --- STEP 1: Upload as Unpublished Photo ---
upload_url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/photos"
files = {'source': open('story_ready.jpg', 'rb')}
payload = {
    'access_token': PAGE_TOKEN,
    'published': 'false'
}

response = requests.post(upload_url, data=payload, files=files).json()
photo_id = response.get('id')

if photo_id:
    print(f"Photo uploaded successfully. ID: {photo_id}")
    
    # --- STEP 2: Publish to Story ---
    story_url = f"https://graph.facebook.com/v22.0/{PAGE_ID}/photo_stories"
    story_payload = {
        'access_token': PAGE_TOKEN,
        'photo_id': photo_id
    }
    
    publish_res = requests.post(story_url, data=story_payload).json()
    print("Publish Result:", publish_res)
else:
    print("Upload failed:", response)
