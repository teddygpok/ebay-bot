import os, time, requests, logging, re
from xml.etree import ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
EBAY_APP_ID = os.environ.get("EBAY_APP_ID")
CHECK_INTERVAL = 120

PATTERNS = [
    "dp 47", "dp47", "018", "18/", "232", "102", "097", "97/",
    "039", "39/", "107", "003", "03/", "3/", "218", "087", "87/",
    "105", "064", "64/", "069", "69/", "128", "010", "10/", "sl",
    "016", "16/", "026", "26/", "009", "9/"
]

def is_valid(title):
    t = title.lower()
    if "rayquaza" not in t:
        return False
    return any(p in t for p in PATTERNS)

def fetch_items():
    try:
        r = requests.get(
            "https://svcs.ebay.com/services/search/FindingService/v1",
            params={
                "OPERATION-NAME": "findItemsByKeywords",
                "SERVICE-VERSION": "1.0.0",
                "SECURITY-APPNAME": EBAY_APP_ID,
                "RESPONSE-DATA-FORMAT": "XML",
                "keywords": "rayquaza carte pokemon",
                "paginationInput.entriesPerPage": "20",
                "sortOrder": "StartTimeNewest",
            },
            timeout=15,
        )
        logging.info(f"eBay status: {r.status_code}")
        root = ET.fromstring(r.content)
        ns = "http://www.ebay.com/marketplace/search/v1/services"
        items = []
        for item in root.iter(f"{{{ns}}}item"):
            title = item.findtext(f"{{{ns}}}title", "")
            price_el = item.find(f".//{{{ns}}}currentPrice")
            price = price_el.text if price_el is not None else "?"
            url = item.findtext(f"{{{ns}}}viewItemURL", "")
            item_id = item.findtext(f"{{{ns}}}itemId", "")
            photo = item.findtext(f"{{{ns}}}galleryURL", "")
            items.append({"id": item_id, "title": title, "price": price, "url": url, "photo": photo})
        logging.info(f"{len(items)} articles trouvés")
        return items
    except Exception as e:
        logging.error(f"Erreur: {e}")
        return []

def notify(item):
    text = f"{item['title']}\nPrix : {item['price']} EUR\n\n{item['url']}"
    if item.get("photo"):
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json={"chat_id": TELEGRAM_CHAT_ID, "photo": item["photo"], "caption": text}, timeout=10)
    else:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)

def main():
    logging.info("Bot eBay démarré !")
    notified = set()
    first_run = True

    while True:
        items = fetch_items()
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
