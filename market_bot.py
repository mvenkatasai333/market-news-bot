import os
import time
import requests

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
LAST_MESSAGE_ID = os.getenv("LAST_MESSAGE_ID")

FEEDS = {
    "🔥 MAIN MARKET EVENTS":  "https://news.google.com/rss/search?q=stock+market+S%26P500&hl=en-US&gl=US&ceid=US:en",
    "📊 MACRO ECONOMY & FED": "https://news.google.com/rss/search?q=inflation+federal+reserve+interest+rates&hl=en-US&gl=US&ceid=US:en",
    "💻 TECH, SEMIS & AI":    "https://news.google.com/rss/search?q=nvidia+nasdaq+artificial+intelligence+stocks&hl=en-US&gl=US&ceid=US:en",
    "🪙 CRYPTO & ASSETS":     "https://news.google.com/rss/search?q=bitcoin+cryptocurrency&hl=en-US&gl=US&ceid=US:en",
}

def get_headlines(url):
    """Fetch RSS and return list of (title, link, source) tuples"""
    import xml.etree.ElementTree as ET
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://news.google.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            print(f"HTTP {r.status_code} for {url}")
            return []

        root = ET.fromstring(r.content)
        results = []

        for item in root.findall(".//item")[:2]:
            # --- Title ---
            raw = item.findtext("title") or "Market Update"
            if " - " in raw:
                raw = raw.rsplit(" - ", 1)[0].strip()
            title = raw.strip()

            # --- Source name ---
            src_el = item.find("source")
            source = src_el.text.strip() if src_el is not None and src_el.text else "Source"

            # --- Real URL: parse from <description> HTML ---
            desc_html = item.findtext("description") or ""
            real_url = None
            if desc_html:
                soup = BeautifulSoup(desc_html, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http") and "news.google.com" not in href:
                        real_url = href
                        break  # take the FIRST non-google link

            if not real_url:
                # Last resort: source url attribute
                if src_el is not None:
                    real_url = src_el.get("url", "#")
                else:
                    real_url = "#"

            results.append((title, real_url, source))

        return results

    except Exception as e:
        print(f"Feed error: {e}")
        return []


def build_message():
    msg = "## 🌍 **ALPHA TERMINAL — MORNING BRIEFING**\n"
    msg += "*Market intelligence delivered at 7:00 AM EST*\n"
    msg += "━" * 28 + "\n\n"

    for section, url in FEEDS.items():
        headlines = get_headlines(url)
        msg += f"### {section}\n"
        if not headlines:
            msg += "⚠️ *No data available right now.*\n\n"
        else:
            for title, link, source in headlines:
                msg += f"🔹 **[{title}]({link})**\n"
                msg += f"↳ *{source}*\n\n"
        time.sleep(2)

    return msg


def delete_old_message():
    if not LAST_MESSAGE_ID or not DISCORD_WEBHOOK_URL:
        return
    try:
        r = requests.delete(f"{DISCORD_WEBHOOK_URL}/messages/{LAST_MESSAGE_ID}", timeout=10)
        print(f"Deleted old message — status {r.status_code}")
    except Exception as e:
        print(f"Delete failed: {e}")


def send_message(content):
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK secret is missing!")
        return None

    message_id = None
    # Split into chunks if over 2000 chars
    chunks = [content[i:i+1990] for i in range(0, len(content), 1990)]

    for i, chunk in enumerate(chunks):
        try:
            r = requests.post(
                DISCORD_WEBHOOK_URL + "?wait=true",
                json={"content": chunk, "username": "Alpha Terminal"},
                timeout=10
            )
            print(f"Chunk {i+1}/{len(chunks)} → HTTP {r.status_code}")
            if i == 0 and r.status_code == 200:
                message_id = r.json().get("id")
        except Exception as e:
            print(f"Send error: {e}")

    return message_id


if __name__ == "__main__":
    delete_old_message()
    briefing = build_message()
    print("\n--- PREVIEW ---")
    print(briefing[:500])
    print("--- END PREVIEW ---\n")
    new_id = send_message(briefing)
    if new_id:
        print(f"NEW_MESSAGE_ID={new_id}")
