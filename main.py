import os, time, requests, logging, re
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
CHECK_INTERVAL = 120

EBAY_URL = "https://www.ebay.fr/sch/i.html"
PARAMS = {
    "LH_ItemCondition": "",
    "LH_Time": "1",
    "_nkw": "rayquaza",
    "_sop": "10",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml",
}

PATTERNS = [
    r"\bdp\s*47\b",
    r"\b0?18\b",
    r"\b232\b",
    r"\b102\b",
    r"\b97\b",
    r"\b0?39\b",
    r"\b107\b",
]

def is_valid(title):
    t = title.lower()
    if "rayquaza" not in t:
        return False
    return any(re.search(p, t) for p in PATTERNS)

def fetch_items():
    try:
        r = requests.get(EBAY_URL, params=PARAMS, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for listing in soup.select(".s-item"):
            title_el = listing.select_one(".s-item__title")
            price_el = listing.select_one(".s-item__price")
            link_el = listing.select_one("a.s-item__link")
            img_el = listing.select_one(".s-item__image-img")
            if not title_el or not link_el:
                continue
            title = title_el.text.strip()
            if title == "Shop on eBay":
                continue
            items.append({
                "id": link_el["href"].split("?")[0],
                "title": title,
                "price": price_el.text.strip() if price_el else "?",
                "url": link_el["href"].split("?")[0],
                "photo": img_el["src"] if img_el else None,
            })
        return items
    except Exception as e:
        logging.error(f"Erreur fetch : {e}")
        return []

def notify(item):
    text = f"{item['title']}\nPrix : {item['price']}\n\n{item['url']}"
    if item.get("photo"):
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json={"chat_id": TELEGRAM_CHAT_ID, "photo": item["photo"], "caption": text},
            timeout=10
        )
    else:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10
        )

def main():
    logging.info("Bot eBay démarré !")
    notified = set()
    first_run = True

    while True:
        items = fetch_items()
        if not items:
            logging.info("Aucun article ou erreur.")
            time.sleep(300)
            continue

        valid = [i for i in items if is_valid(i["title"])]

        if first_run:
            for i in valid:
                notified.add(i["id"])
            first_run = False
            logging.info(f"{len(notified)} annonces existantes ignorées.")
        else:
            for item in valid:
                if item["id"] not in notified:
                    notify(item)
                    notified.add(item["id"])
                    logging.info(f"Notifié : {item['title']}")

        time.sleep(CHECK_INTERVAL)

main()
