import os
import xml.etree.ElementTree as ET
import time
import random
import requests
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

TRENDS_FEEDS = {
    "🔥 MAIN MARKET EVENTS": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    "📊 MACRO ECONOMY & FED": "https://news.google.com/rss/search?q=(inflation+OR+interest+rates+OR+fed+rate)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "💻 TECH, SEMIS & AI": "https://news.google.com/rss/search?q=(nasdaq+OR+nvidia+OR+ai+stocks)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "🪙 CRYPTO & ASSETS": "https://news.google.com/rss/search?q=(bitcoin+OR+crypto+regulation)+when:12h&hl=en-US&gl=US&ceid=US:en"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
]

def clean_html_tags(text):
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text()

def clean_duplicate_headline(title):
    """Fixes the Google News bug where phrases repeat back-to-back"""
    if not title:
        return ""
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    # FIX: Only deduplicate if length is even AND both halves truly match
    if len(title) % 2 == 0:
        half_len = len(title) // 2
        first_half = title[:half_len].strip()
        second_half = title[half_len:].strip()
        if first_half == second_half:
            return first_half
    return title

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
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        except Exception as e:
            print(f"Error reading feed (attempt {attempt+1}): {e}")
        time.sleep(2)
    return None

def delete_old_message(message_id: str):
    """Deletes yesterday's Discord message using stored message ID"""
    if not message_id or not DISCORD_WEBHOOK_URL:
        return
    delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{message_id}"
    try:
        resp = requests.delete(delete_url, timeout=10)
        if resp.status_code == 204:
            print(f"Deleted old message: {message_id}")
        else:
            print(f"Could not delete message: {resp.status_code}")
    except Exception as e:
        print(f"Delete failed: {e}")

def send_to_discord(content: str) -> str | None:
    """Sends message and returns the message ID for future deletion"""
    if not DISCORD_WEBHOOK_URL:
        print("Error: Missing Discord Webhook URL.")
        return None

    # Split long messages instead of truncating
    chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
    message_id = None

    for i, chunk in enumerate(chunks):
        payload = {
            "content": chunk,
            "username": "Alpha Terminal Bot",
        }
        try:
            # ?wait=true makes Discord return the message object with its ID
            resp = requests.post(
                DISCORD_WEBHOOK_URL + "?wait=true",
                json=payload,
                timeout=10
            )
            if i == 0 and resp.status_code == 200:
                message_id = resp.json().get("id")
            print(f"Sent chunk {i+1}/{len(chunks)}")
        except Exception as e:
            print(f"Failed to push chunk {i+1}: {e}")

    return message_id

def build_discord_briefing():
    message = "## 🌍 **MORNING MULTI-PORTAL INTELLIGENCE**\n"
    message += "*Fresh overnight updates processed at 7:00 AM EST*\n"
    message += "━" * 25 + "\n\n"

    for section_name, url in TRENDS_FEEDS.items():
        root = fetch_feed_data(url)
        if root is None:
            message += f"### {section_name}\n⚠️ *Feed unavailable — try again later.*\n\n"
            continue

        items = root.findall(".//item")[:2]
        if items:
            message += f"### {section_name}\n"
            for item in items:
                raw_title = item.find("title").text if item.find("title") is not None else "Market Update"
                link = item.find("link").text if item.find("link") is not None else "#"
                source = item.find("source").text if item.find("source") is not None else "Financial Portal"
                title = clean_duplicate_headline(raw_title)
                message += f"🔹 **[{title}]({link})**\n↳ *Source: {source}*\n\n"

        time.sleep(1.5)

    return message

if __name__ == "__main__":
    # Load stored message ID from environment (set as GitHub secret/var)
    old_message_id = os.getenv("LAST_MESSAGE_ID")

    # Delete yesterday's message first
    if old_message_id:
        delete_old_message(old_message_id)

    # Build and send today's briefing
    briefing_text = build_discord_briefing()
    new_message_id = send_to_discord(briefing_text)

    if new_message_id:
        print(f"NEW_MESSAGE_ID={new_message_id}")  # GitHub Actions can capture this
