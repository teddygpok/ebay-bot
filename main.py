import os, time, requests, logging, re
from xml.etree import ElementTree

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
EBAY_APP_ID = os.environ.get("EBAY_APP_ID")
CHECK_INTERVAL = 120

PATTERNS = [
    r"\bdp\s*47\b", r"\b0?18\b", r"\b232\b", r"\b102\b",
    r"\b97\b", r"\b0?39\b", r"\b107\b", r"\b0{0,2}3\b",
    r"\b218\b", r"\b87\b", r"\b105\b", r"\b64\b",
    r"\b69\b", r"\b128\b", r"\b10\b", r"\bsl\b",
    r"\b16\b", r"\b26\b", r"\b9\b",
]

NS = "http://www.ebay.com/marketplace/search/v1/services"

def fetch_items():
    try:
        r = requests.get(
            "https://svcs.ebay.com/services/search/FindingService/v1",
            params={
                "OPERATION-NAME": "findItemsByKeywords",
                "SERVICE-VERSION": "1.0.0",
                "SECURITY-APPNAME": EBAY_APP_ID,
                "RESPONSE-DATA-FORMAT": "XML",
                "REST-PAYLOAD": "",
                "keywords": "rayquaza carte pokemon",
                "paginationInput.entriesPerPage": "20",
                "sortOrder": "StartTimeNewest",
                "itemFilter(0).name": "ListingType",
                "itemFilter(0).value": "FixedPrice",
            },
            timeout=15,
        )
        root = ElementTree.fromstring(r.content)
        items = []
        for item in root.iter(f"{{{NS}}}item"):
            title = item.findtext(f"{{{NS}}}title", "")
            price_el = item.find(f".//{{{NS}}}currentPrice")
            price = price_el.text if price_el is not None else "?"
            currency = price_el.get("currencyId", "EUR") if price_el is not None else "EUR"
            url = item.findtext(f"{{{NS}}}viewItemURL", "")
            item_id = item.findtext(f"{{{NS}}}itemId", "")
            photo = item.findtext(f"{{{NS}}}galleryURL", "")
            items.append({
                "id": item_id,
                "title": title,
                "price": price,
                "currency": currency,
                "url": url,
                "photo": photo,
            })
        return items
    except Exception as e:
        logging.error(f"Erreur fetch : {e}")
        return []

def is_valid(item):
    title = item.get("title", "").lower()
    if "rayquaza" not in title:
        return False
    return any(re.search(p, title) for p in PATTERNS)

def notify(item):
    title = item.get("title", "?")
    price = item.get("price", "?")
    currency = item.get("currency", "EUR")
    url = item.get("url", "")
    photo = item.get("photo", "")
    text = f"{title}\nPrix : {price} {currency}\n\n{url}"

    if photo:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
            json={"chat_id": TELEGRAM_CHAT_ID, "photo": photo, "caption": text},
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
