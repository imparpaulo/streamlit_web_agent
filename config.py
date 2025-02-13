import os
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = "https://n8n-a48r.onrender.com/webhook/api/agent/web-search/v1"
AUTH_HEADER = os.getenv("AUTH_HEADER", "")  # Load from environment variable
