"""Daily: re-read what's on in Batam from batam.co.id into data.js (the "What's on" tab).

batam.co.id keeps an event calendar that is rebuilt several times a day and names the news
source behind every date. This script copies the events that are running now or still to come:
name, dates, venue, whether the date is confirmed, and the source links.

Kept by hand in data.js and never touched here:
  events.manual  events we add ourselves (for example from a mall's own calendar)
  events.labels  English and Chinese names, keyed by event id
  events.hide    ids to leave out (duplicates of another entry)

If the page cannot be read or looks wrong, data.js is left unchanged.
For a dry run against a saved copy of the page: python tools/events_refresh.py saved.html
"""
import datetime
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.js"
SOURCE = "https://batam.co.id/event-batam/"
LIVE_STATES = ("Sedang berlangsung", "Akan datang")
# venue text -> place id in data.js, so the event card can open that place's map
PLACES = {"grand batam": "grand-batam", "mega mall": "mega-mall", "nagoya hill": "nagoya-hill"}
BATAM_TIME = datetime.timezone(datetime.timedelta(hours=7))
STALE_AFTER_DAYS = 6
ITEM = re.compile(r"<li class=\"?ev-item\"? id=\"?([^\" >]+)\"?>(.*?)</li>", re.S)
DATE = re.compile(r"<time datetime=\"?(\d{4}-\d{2}-\d{2})\"?>")
LINK = re.compile(r"<a href=\"?([^\" >]+)\"?[^>]*>(.*?)</a>", re.S)


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (batam-uncle-bot)"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read().decode("utf-8", errors="replace")


def clean(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def part(body, css_class):
    match = re.search(rf"<(\w+) class=\"?{css_class}\"?>(.*?)</\1>", body, re.S)
    return match.group(2) if match else ""


def read_date(page, today):
    match = re.search(r"Diperbarui:.{0,40}?<time datetime=\"?(\d{4}-\d{2}-\d{2})", page, re.S)
    return match.group(1) if match else today


def parse(page, today):
    events = []
    for event_id, body in ITEM.findall(page):
        meta = part(body, "ev-meta")
        state = clean(re.sub(r"</span>.*", "", meta, flags=re.S))
        dates = DATE.findall(meta)
        if state not in LIVE_STATES or not dates:
            continue
        start, end = dates[0], dates[-1]
        if end < today:
            continue
        tail = meta.rsplit("·", 1)[-1]
        venue = clean(tail) if "·" in meta and "<time" not in tail else "Batam"
        sources = [{"label": clean(label), "url": html.unescape(url)} for url, label in LINK.findall(part(body, "ev-src"))]
        event = {
            "id": event_id,
            "name": clean(part(body, "ev-nama")),
            "start": start,
            "end": end,
            "venue": venue,
            "confirmed": clean(part(body, "ev-kf")).startswith("Tanggal pasti"),
            "sources": sources[:3],
        }
        place = next((place_id for text, place_id in PLACES.items() if text in venue.lower()), "")
        if place:
            event["place_id"] = place
        events.append(event)
    return sorted(events, key=lambda e: (e["start"], e["end"], e["id"]))


def sane(page, events):
    if "ev-item" not in page or "ev-nama" not in page:
        return "the event list is missing from the page"
    for event in events:
        if not event["name"] or not event["sources"]:
            return f"event {event['id']} has no name or no source"
        for field in ("start", "end"):
            try:
                datetime.date.fromisoformat(event[field])
            except ValueError:
                return f"bad date {event[field]}"
        if event["start"] > event["end"]:
            return f"event {event['id']} ends before it starts"
        if any(not s["url"].startswith("https://") for s in event["sources"]):
            return f"event {event['id']} has a source that is not an https link"
    if len({e["id"] for e in events}) != len(events):
        return "duplicate event ids"
    return ""


def main():
    source_text = DATA.read_text(encoding="utf-8")
    prefix = source_text[:source_text.index("{")]
    suffix = source_text[source_text.rindex("}") + 1:]
    data = json.loads(source_text[source_text.index("{"):source_text.rindex("}") + 1])
    today = datetime.datetime.now(BATAM_TIME).date().isoformat()
    try:
        page = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else fetch(SOURCE)
    except Exception as error:
        print(f"events: could not read source ({error}); data unchanged")
        return 0
    events = parse(page, today)
    problem = sane(page, events)
    if problem:
        print(f"events: source looks wrong ({problem}); data unchanged")
        return 0
    block = data.setdefault("events", {})
    block.setdefault("note_en", "Read from batam.co.id, which names the news source behind every date. Dates can move, so check the source before you travel for an event.")
    block.setdefault("note_zh", "资料读取自 batam.co.id,每个日期都注明新闻来源。日期可能变动,专程前往前请先查看来源。")
    block.setdefault("manual", [])
    block.setdefault("hide", [])
    block.setdefault("labels", {})
    as_of = read_date(page, today)
    old_as_of = block.get("as_of", "")
    # commit only when the list itself changes, or weekly so the "read on" date never looks abandoned
    stale = not old_as_of or (datetime.date.fromisoformat(as_of) - datetime.date.fromisoformat(old_as_of)).days >= STALE_AFTER_DAYS
    if block.get("list") == events and block.get("source") == SOURCE and not stale:
        print(f"events: no change ({len(events)} events, read {as_of})")
        return 0
    block.update({"source": SOURCE, "as_of": as_of, "list": events})
    known = {e["id"] for e in events} | {e["id"] for e in block["manual"]}
    block["labels"] = {event_id: label for event_id, label in block["labels"].items() if event_id in known}
    block["hide"] = [event_id for event_id in block["hide"] if event_id in known]
    DATA.write_text(prefix + json.dumps(data, ensure_ascii=False, indent=1) + suffix, encoding="utf-8", newline="\n")
    unnamed = [e["id"] for e in events if e["id"] not in block["labels"]]
    print(f"events: updated from {SOURCE} ({as_of}): {len(events)} events" + (f"; no English/Chinese name yet for: {', '.join(unnamed)}" if unnamed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
