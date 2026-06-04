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
    """Remove source suffix and fix duplicates"""
    if not title:
        return "Market Update"
    # Remove ' - Source Name' from end
    if " - " in title:
        title = title.rsplit(" - ", 1)[0].strip()
    # Fix exact duplicate (e.g. "Headline Headline")
    words = title.split()
    half = len(words) // 2
    if half > 0 and words[:half] == words[half:]:
        title = " ".join(words[:half])
    return title.strip()

def extract_real_url_from_description(description_html):
    """
    THE KEY FIX: Google News hides the real article URL inside
    the <description> tag as an <a href="..."> pointing to the source.
    We parse that HTML and grab the LAST link (which is the article).
    """
    if not description_html:
        return None
    try:
        soup = BeautifulSoup(description_html, "html.parser")
        links = soup.find_all("a", href=True)
        for link in reversed(links):
            href = link["href"]
            # Skip Google News internal links
            if "news.google.com" not in href and href.startswith("http"):
                return href
    except Exception:
        pass
    return None

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
    message_id = None

    for i, chunk in enumerate(chunks):
        try:
            resp = requests.post(
                DISCORD_WEBHOOK_URL + "?wait=true",
                json={"content": chunk, "username": "Alpha Terminal Bot"},
                timeout=10
            )
            if i == 0 and resp.status_code == 200:
                message_id = resp.json().get("id")
            print(f"Sent chunk {i+1}/{len(chunks)} — status {resp.status_code}")
        except Exception as e:
            print(f"Failed chunk {i+1}: {e}")

    return message_id

def build_discord_briefing():
    message = "## 🌍 **MORNING MULTI-PORTAL INTELLIGENCE**\n"
    message += "*Fresh overnight updates — 7:00 AM EST*\n"
    message += "━" * 25 + "\n\n"

    for section_name, url in TRENDS_FEEDS.items():
        root = fetch_feed_data(url)
        if root is None:
            message += f"### {section_name}\n⚠️ *Feed unavailable.*\n\n"
            continue

        items = root.findall(".//item")[:2]

        if not items:
            message += f"### {section_name}\n⚠️ *No headlines found.*\n\n"
            continue

        message += f"### {section_name}\n"

        for item in items:
            # Clean title
            raw_title = item.findtext("title") or "Market Update"
            title = clean_title(raw_title)

            # Get source name
            source_el = item.find("source")
            source = source_el.text if source_el is not None else "Unknown"

            # THE FIX: pull real URL from description HTML
            description_html = item.findtext("description") or ""
            real_url = extract_real_url_from_description(description_html)

            # Fallback to google link if extraction fails
            if not real_url:
                real_url = item.findtext("link") or "#"

            message += f"🔹 **[{title}]({real_url})**\n↳ *{source}*\n\n"

        time.sleep(1.5)

    return message

if __name__ == "__main__":
    if LAST_MESSAGE_ID:
        delete_old_message(LAST_MESSAGE_ID)

    briefing_text = build_discord_briefing()
    new_message_id = send_to_discord(briefing_text)

    if new_message_id:
        print(f"NEW_MESSAGE_ID={new_message_id}")
