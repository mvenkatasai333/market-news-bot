import os
import time
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
LAST_MESSAGE_ID = os.getenv("LAST_MESSAGE_ID")

FEEDS = {
    "🔥 MAIN MARKET EVENTS":  "https://news.google.com/rss/search?q=stock+market+wall+street+dow+jones&hl=en-US&gl=US&ceid=US:en",
    "📊 MACRO ECONOMY & FED": "https://news.google.com/rss/search?q=inflation+federal+reserve+interest+rates&hl=en-US&gl=US&ceid=US:en",
    "💻 TECH, SEMIS & AI":    "https://news.google.com/rss/search?q=nvidia+nasdaq+artificial+intelligence&hl=en-US&gl=US&ceid=US:en",
    "🪙 CRYPTO & ASSETS":     "https://news.google.com/rss/search?q=bitcoin+cryptocurrency+crypto&hl=en-US&gl=US&ceid=US:en",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://news.google.com/",
}

def get_real_url(item):
    # Try extracting from description HTML first
    desc = item.findtext("description") or ""
    if desc:
        soup = BeautifulSoup(desc, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "news.google.com" not in href:
                return href
    # Fallback: source url attribute
    src = item.find("source")
    if src is not None and src.get("url"):
        return src.get("url")
    return None

def get_headlines(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"HTTP {r.status_code}")
            return []
        root = ET.fromstring(r.content)
        results = []
        for item in root.findall(".//item")[:2]:
            raw_title = item.findtext("title") or "Update"
            # Clean title — remove source suffix
            if " - " in raw_title:
                raw_title = raw_title.rsplit(" - ", 1)[0].strip()
            src_el = item.find("source")
            source = src_el.text.strip() if src_el is not None and src_el.text else "News"
            real_url = get_real_url(item)
            if real_url:
                results.append((raw_title, real_url, source))
        return results
    except Exception as e:
        print(f"Feed error: {e}")
        return []

def build_message():
    msg = "## 🌍 **ALPHA TERMINAL — MORNING BRIEFING**\n"
    msg += "*Market intelligence — 7:00 AM EST*\n"
    msg += "━" * 28 + "\n\n"
    for section, url in FEEDS.items():
        headlines = get_headlines(url)
        msg += f"### {section}\n"
        if not headlines:
            msg += "⚠️ *No headlines available.*\n\n"
        else:
            for title, link, source in headlines:
                msg += f"🔹 **[{title}]({link})**\n↳ *{source}*\n\n"
        time.sleep(2)
    return msg

def delete_old_message():
    if not LAST_MESSAGE_ID or not DISCORD_WEBHOOK_URL:
        return
    try:
        r = requests.delete(f"{DISCORD_WEBHOOK_URL}/messages/{LAST_MESSAGE_ID}", timeout=10)
        print(f"Deleted old message — {r.status_code}")
    except Exception as e:
        print(f"Delete failed: {e}")

def send_message(content):
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK missing!")
        return None
    chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]
    message_id = None
    for i, chunk in enumerate(chunks):
        try:
            r = requests.post(
                DISCORD_WEBHOOK_URL + "?wait=true",
                json={"content": chunk, "username": "Alpha Terminal"},
                timeout=10
            )
            print(f"Chunk {i+1}/{len(chunks)} — HTTP {r.status_code}")
            if i == 0 and r.status_code == 200:
                message_id = r.json().get("id")
        except Exception as e:
            print(f"Send error: {e}")
    return message_id

if __name__ == "__main__":
    delete_old_message()
    briefing = build_message()
    new_id = send_message(briefing)
    if new_id:
        print(f"NEW_MESSAGE_ID={new_id}")
