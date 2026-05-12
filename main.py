import os, time, requests, logging, re, base64

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
EBAY_APP_ID = os.environ.get("EBAY_APP_ID")
EBAY_CERT_ID = os.environ.get("EBAY_CERT_ID")
CHECK_INTERVAL = 120

PATTERNS = [
    r"\bdp\s*47\b",
    r"\b0?18\b",
    r"\b232\b",
    r"\b102\b",
    r"\b97\b",
    r"\b0?39\b",
    r"\b107\b",
    r"\b0{0,2}3\b",
    r"\b218\b",
    r"\b87\b",
    r"\b105\b",
    r"\b64\b",
    r"\b69\b",
    r"\b128\b",
    r"\b10\b",
    r"\bsl\b",
    r"\b16\b",
    r"\b26\b",
    r"\b9\b",
]

def get_token():
    credentials = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
    try:
        r = requests.post(
            "https://api.ebay.com/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
            timeout=10,
        )
        logging.info(f"Status eBay : {r.status_code}")
        logging.info(f"Réponse eBay : {r.text[:300]}")
        return r.json().get("access_token")
    except Exception as e:
        logging.error(f"Erreur token : {e}")
        return None

def is_valid(title):
    t = title.lower()
    if "rayquaza" not in t:
        return False
    return any(re.search(p, t) for p in PATTERNS)

def fetch_items(token):
    try:
        r = requests.get(
            "https://api.ebay.com/buy/browse/v1/item_summary/search",
            headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_FR"},
            params={"q": "rayquaza carte", "sort": "newlyListed", "limit": 20},
            timeout=15,
        )
        data = r.json()
        return data.get("itemSummaries", [])
    except Exception as e:
        logging.error(f"Erreur fetch : {e}")
        return []

def notify(item):
    title = item.get("title", "?")
    price = item.get("price", {}).get("value", "?")
    currency = item.get("price", {}).get("currency", "EUR")
    url = item.get("itemWebUrl", "?")
    photo = item.get("image", {}).get("imageUrl", None)
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
    token = get_token()
    if not token:
        logging.error("Impossible d'obtenir le token eBay !")
        return

    notified = set()
    first_run = True

    while True:
        items = fetch_items(token)
        if not items:
            logging.info("Aucun article ou erreur.")
            time.sleep(300)
            continue

        valid = [i for i in items if is_valid(i.get("title", ""))]

        if first_run:
            for i in valid:
                notified.add(i["itemId"])
            first_run = False
            logging.info(f"{len(notified)} annonces existantes ignorées.")
        else:
            for item in valid:
                if item["itemId"] not in notified:
                    notify(item)
                    notified.add(item["itemId"])
                    logging.info(f"Notifié : {item.get('title')}")

        time.sleep(CHECK_INTERVAL)

main()
