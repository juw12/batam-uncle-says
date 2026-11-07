"""Weekly check of listed Batam drivers and guides (runs in GitHub Actions, no human needed).

For every listed operator: fetch their own website and confirm their WhatsApp number is still on it.
  - found      -> stays active, "checked" date updated
  - not found  -> fails += 1; after 2 failed weeks in a row the listing is paused (hidden in the app)
  - found again after a pause -> active again
For every candidate: if their website now shows a WhatsApp number, they are listed automatically
(prices are not copied, the card links to their website).
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "partners.json"
TODAY = datetime.date.today().isoformat()
UA = "Mozilla/5.0 (compatible; BatamUncleSaysCheck/1.0; +https://juw12.github.io/batam-uncle-says/)"
MAX_FAILS = 2


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")
    except Exception as error:
        print(f"  fetch failed: {url}: {error}")
        return None


def normalise(number):
    digits = re.sub(r"\D", "", number)
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits


def numbers_on_page(page):
    found = set()
    for match in re.findall(r"(?:wa\.me/|phone=)\+?(\d{9,15})", page):
        found.add(normalise(match))
    for match in re.findall(r"(?:\+62|\b62|\b08)[\d\s\-().]{7,18}\d", page):
        found.add(normalise(match))
    return found


def whatsapp_links(page):
    return [normalise(m) for m in re.findall(r"(?:wa\.me/|phone=)\+?(\d{9,15})", page) if normalise(m).startswith("62")]


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main():
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    changed = False

    for operator in data["operators"]:
        print(f"operator: {operator['name']}")
        page = fetch(operator["website"])
        ok = page is not None and operator["whatsapp"] in numbers_on_page(page)
        if ok:
            if operator["status"] != "active" or operator.get("fails"):
                print("  back to active")
            operator["status"] = "active"
            operator["fails"] = 0
            operator["checked"] = TODAY
            changed = True
        else:
            operator["fails"] = operator.get("fails", 0) + 1
            print(f"  number not found ({operator['fails']} in a row)")
            if operator["fails"] >= MAX_FAILS and operator["status"] == "active":
                operator["status"] = "paused"
                print("  paused")
            changed = True

    listed_sites = {op["website"].rstrip("/") for op in data["operators"]}
    remaining = []
    for candidate in data.get("candidates", []):
        if candidate["website"].rstrip("/") in listed_sites:
            continue
        print(f"candidate: {candidate['name']}")
        page = fetch(candidate["website"])
        links = whatsapp_links(page) if page else []
        if links:
            data["operators"].append({
                "id": slug(candidate["name"]),
                "name": candidate["name"],
                "website": candidate["website"],
                "whatsapp": links[0],
                "kind": "car",
                "languages": [],
                "prices": [],
                "price_note": "See their website for prices",
                "status": "active",
                "checked": TODAY,
                "fails": 0,
            })
            print(f"  listed with {links[0]}")
            changed = True
        else:
            remaining.append(candidate)
    data["candidates"] = remaining

    if changed:
        data["updated"] = TODAY
        DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    active = sum(op["status"] == "active" for op in data["operators"])
    print(f"active operators: {active}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
