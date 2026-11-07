"""Tell Bing, Yandex, Seznam and Naver (IndexNow) about every page in sitemap.xml."""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = "b7c4e1f09a3d4c6e8f2a5b1d7e9c3f60"
SITE = "https://juw12.github.io/batam-uncle-says/"

urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
payload = json.dumps({
    "host": "juw12.github.io",
    "key": KEY,
    "keyLocation": SITE + KEY + ".txt",
    "urlList": urls,
}).encode()
request = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=payload,
    headers={"Content-Type": "application/json; charset=utf-8"},
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        print("IndexNow", response.status, len(urls), "urls")
except Exception as error:
    print("IndexNow failed:", error)
