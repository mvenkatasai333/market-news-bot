import os
import xml.etree.ElementTree as ET
import time
import random
import requests

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
ID_FILE_PATH = "last_message_id.txt"

# FIX: Switched "MAIN MARKET EVENTS" to a highly reliable search-query format
TRENDS_FEEDS = {
    "🔥 MAIN MARKET EVENTS": "https://news.google.com/rss/search?q=(stock+market+OR+wall+street)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "📊 MACRO ECONOMY & FED": "https://news.google.com/rss/search?q=(inflation+OR+interest+rates+OR+fed+rate)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "💻 TECH, SEMIS & AI": "https://news.google.com/rss/search?q=(nasdaq+OR+nvidia+OR+ai+stocks)+when:12h&hl=en-US&gl=US&ceid=US:en",
    "🪙 CRYPTO & ASSETS": "https://news.google.com/rss/search?q=(bitcoin+OR+crypto+regulation)+when:12h&hl=en-US&gl=US&ceid=US:en"
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
]

def clean_duplicate_headline(title):
    if not title: return ""
    # Strip out the source from the title tail if present
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    
    # Address Google News back-to-back duplicate title bug
    half_len = len(title) // 2
    if title[:half_len].strip() == title[half_len:].strip():
        return title[:half_len].strip()
    return title

def fetch_feed_data(url):
    headers = {"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.9", "Referer": "https://news.google.com/"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200: return ET.fromstring(response.content)
    except: pass
    return None

def build_discord_briefing():
    message = "## 🌍 **MORNING MULTI-PORTAL INTELLIGENCE**\n"
    message += "*Fresh overnight updates processed at 7:00 AM EST*\n"
    message += "━" * 25 + "\n\n"
    
    for section_name, url in TRENDS_FEEDS.items():
        root = fetch_feed_data(url)
        if root is None: continue
        items = root.findall(".//item")[:2]
        if items:
            message += f"### {section_name}\n"
            for item in items:
                raw_title = item.find("title").text if item.find("title") is not None else "Market Update"
                link = item.find("link").text if item.find("link") is not None else "#"
                source = item.find("source").text if item.find("source") is not None else "Financial Portal"
                
                title = clean_duplicate_headline(raw_title)
                
                # FIX: Removed the description string entirely to eliminate HTML "Google News" bloat
                message += f"🔹 **[{title}]({link})**\n↳ *Source: {source}*\n\n"
        time.sleep(1.5)
    return message

def delete_old_message():
    if os.path.exists(ID_FILE_PATH) and DISCORD_WEBHOOK_URL:
        try:
            with open(ID_FILE_PATH, "r") as f:
                old_id = f.read().strip()
            if old_id:
                delete_url = f"{DISCORD_WEBHOOK_URL}/messages/{old_id}"
                res = requests.delete(delete_url, timeout=10)
                if res.status_code in [204, 200]:
                    print(f"Successfully vaporized yesterday's message (ID: {old_id})")
        except Exception as e:
            print(f"Error handling deletion: {e}")

def send_to_discord(content):
    if not DISCORD_WEBHOOK_URL: return
    target_url = f"{DISCORD_WEBHOOK_URL}?wait=true"
    payload = {
        "content": content,
        "username": "Alpha Terminal Bot",
        "avatar_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=100&auto=format&fit=crop"
    }
    try:
        response = requests.post(target_url, json=payload, timeout=10)
        if response.status_code in [200, 201]:
            new_id = response.json().get("id")
            if new_id:
                with open(ID_FILE_PATH, "w") as f:
                    f.write(str(new_id))
                print(f"Saved tracking entry: {new_id}")
    except Exception as e:
        print(f"Failed to push update: {e}")

if __name__ == "__main__":
    delete_old_message()
    briefing_text = build_discord_briefing()
    send_to_discord(briefing_text)
