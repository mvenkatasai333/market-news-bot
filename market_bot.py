import os
import xml.etree.ElementTree as ET
import time
import random
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
LAST_MESSAGE_ID = os.getenv("LAST_MESSAGE_ID")

TRENDS_FEEDS = {
    "🔥 MAIN MARKET EVENTS": "https://news.google.com/rss/search?q=(stock+market+OR+S%26P500+OR+wall+street)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "📊 MACRO ECONOMY & FED": "https://news.google.com/rss/search?q=(inflation+OR+interest+rates+OR+fed+rate)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "💻 TECH, SEMIS & AI": "https://news.google.com/rss/search?q=(nasdaq+OR+nvidia+OR+ai+stocks)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "🪙 CRYPTO & ASSETS": "https://news.google.com/rss/search?q=(bitcoin+OR+crypto+regulation)+when:12h&hl=en-US&gl=US&ceid=US:en"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
]

def clean_title(title):
    if not title:
        return "Market Update"
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    words = title.split()
    half = len(words) // 2
    if half > 0 and words[:half] == words[half:]:
        title = " ".join(words[:half])
    return title.strip()

def extract_real_url(item):
    """Pull real article URL from inside the description HTML"""
    description_html = item.findtext("description") or ""
    if description_html:
        try:
            soup = BeautifulSoup(description_html, "html.parser")
            for a in reversed(soup.find_all("a", href=True)):
                href = a["href"]
                if "news.google.com" not in href and href.startswith("http"):
                    return href
        except Exception:
            pass
    # fallback
    return item.findtext("link") or "#"

def fetch_feed_data(url, retries=2):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://news.google.com/"
    }
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return ET.fromstring(response.content)
            print(f"HTTP {response.status_code} on attempt {attempt+1}")
        except Exception as e:
            print(f"Error on attempt {attempt+1}: {e}")
        time.sleep(2)
    return None

def delete_old_message(message_id):
    if not message_id or not DISCORD_WEBHOOK_URL:
        return
    try:
        resp = requests.delete(f"{DISCORD_WEBHOOK_URL}/messages/{message_id}", timeout=10)
        print(f"Delete status: {resp.status_code}")
    except Exception as e:
        print(f"Delete failed: {e}")

def send_to_discord(content):
    if not DISCORD_WEBHOOK_URL:
        print("Error: Missing Discord Webhook URL.")
        return None

    chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
