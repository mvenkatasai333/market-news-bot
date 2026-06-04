import os
import xml.etree.ElementTree as ET
import time
import random
import requests
from bs4 import BeautifulSoup

# Reads your secure Webhook from GitHub Secrets
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# FIX: Updated the main business feed link and optimized search strings
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
    # Strip the publication tag from the end first (e.g., " - Yahoo Finance")
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    
    # Check if the title is a perfect duplication separated by a space
    half_len = len(title) // 2
    if len(title) % 2 == 0 or len(title) % 2 == 1:
        first_half = title[:half_len].strip()
        second_half = title[half_len:].strip()
        if first_half == second_half:
            return first_half
            
    return title

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
                raw_title = item.find("title").text if item.find("title") is not None else "Market Update"
                link = item.find("link").text if item.find("link") is not None else "#"
                source = item.find("source").text if item.find("source") is not None else "Financial Portal"
                
                # Apply text cleaners
                title = clean_duplicate_headline(raw_title)
                
                # Output sleek format without huge bloated descriptions
                message += f"🔹 **[{title}]({link})**\n↳ *Source: {source}*\n\n"
        
        time.sleep(1.5)
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
        print("Success! Sent clean morning briefing to Discord.")
    except Exception as e:
        print(f"Failed to push message to Discord: {e}")

if __name__ == "__main__":
    briefing_text = build_discord_briefing()
    send_to_discord(briefing_text)
