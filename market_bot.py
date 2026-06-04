import os
import xml.etree.ElementTree as ET
import time
import random
import requests
from bs4 import BeautifulSoup

# Reads your secure Webhook from GitHub Secrets
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# Your 4 exact target feeds optimized with 'when:12h' for freshness
TRENDS_FEEDS = {
    "🔥 MAIN MARKET EVENTS": "https://news.google.com/rss/sections/CAAqBggKMHJjR1NoTldvRERRb0pChG9JRE93YlhCd01UUXoF?hl=en-US&gl=US&ceid=US:en",
    "📊 MACRO ECONOMY & FED": "https://news.google.com/rss/search?q=(inflation+OR+interest+rates+OR+powell+OR+economy)+when:12h&hl=en-US&gl=US&ceid=US:en",
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

def fetch_feed_data(url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://news.google.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return ET.fromstring(response.content)
    except Exception as e:
        print(f"Error reading feed: {e}")
    return None

def build_discord_briefing():
    message = "## 🌍 **MORNING MULTI-PORTAL INTELLIGENCE**\n"
    message += "*Fresh overnight updates processed at 7:00 AM EST*\n"
    message += "━" * 25 + "\n\n"
    
    for section_name, url in TRENDS_FEEDS.items():
        root = fetch_feed_data(url)
        if root is None:
            continue
            
        items = root.findall(".//item")[:2]
        if items:
            message += f"### {section_name}\n"
            for item in items:
                title = item.find("title").text
                link = item.find("link").text
                source = item.find("source").text if item.find("source") is not None else "Financial Portal"
                description = clean_html_tags(item.find("description").text)
                
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                
                short_desc = description[:120] + "..." if len(description) > 120 else description
                message += f"🔹 **[{title}]({link})**\n*{short_desc}*\n↳ *Source: {source}*\n\n"
        
        time.sleep(2.0)
    return message

def send_to_discord(content):
    if not DISCORD_WEBHOOK_URL:
        print("Error: Missing Discord Webhook URL.")
        return

    payload = {
        "content": content,
        "username": "Alpha Terminal Bot",
        "avatar_url": "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=100&auto=format&fit=crop"
    }
    
    if len(content) > 2000:
        payload["content"] = content[:1950] + "\n...[Briefing truncated]"

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        print("Success! Sent morning briefing to Discord.")
    except Exception as e:
        print(f"Failed to push message to Discord: {e}")

if __name__ == "__main__":
    briefing_text = build_discord_briefing()
    send_to_discord(briefing_text)
