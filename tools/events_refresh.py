"""Daily: re-read what's on in Batam into data.js (the "What's on" tab).

batam.co.id keeps an event calendar that is rebuilt several times a day and names the news
source behind every date. This script copies the events that are running now or still to come:
name, dates, venue, whether the date is confirmed, and the source links.

Fun runs come from indonesiamarathon.com, a run calendar that publishes a plain-text list
(llms-full.txt) and asks readers to cite it. Runs in Batam go into events.runs with distance,
fee and sign-up link. It is a directory and not the organiser, so runs are never marked confirmed.

Kept by hand in data.js and never touched here:
  events.manual  events we add ourselves (for example from a mall's own calendar)
  events.labels  English and Chinese names, keyed by event id
  events.hide    ids to leave out (duplicates of another entry)

If a source cannot be read or looks wrong, its part of data.js is left unchanged.
To run against saved copies: python tools/events_refresh.py saved.html [saved-runs.txt]
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
RUNS_SOURCE = "https://indonesiamarathon.com/llms-full.txt"
RUN_BLOCK = re.compile(r"^### (.+?)\n(.*?)(?=^##|\Z)", re.S | re.M)
RUN_FIELD = re.compile(r"^- ([^:\n]+): (.+)$", re.M)
RUN_IN_BATAM = re.compile(r"(?:^|, )Batam, Kepulauan Riau$")
MONTHS = ("januari", "februari", "maret", "april", "mei", "juni", "juli", "agustus", "september", "oktober", "november", "desember")
# fewer readable blocks than this means the run calendar changed its format
RUN_BLOCKS_EXPECTED = 20


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


def run_day(text):
    """'Minggu, 15 November 2026' -> '2026-11-15' ('' when it cannot be read)."""
    match = re.search(r"(\d{1,2}) (\w+) (\d{4})", text)
    if not match or match.group(2).lower() not in MONTHS:
        return ""
    month = MONTHS.index(match.group(2).lower()) + 1
    return f"{match.group(3)}-{month:02d}-{int(match.group(1)):02d}"


def parse_runs(text, today):
    """Returns (number of readable blocks in the whole calendar, upcoming runs in Batam)."""
    readable, runs = 0, []
    for name, body in RUN_BLOCK.findall(text):
        field = {key.strip(): value.strip() for key, value in RUN_FIELD.findall(body)}
        days = [run_day(piece) for piece in field.get("Tanggal", "").split("–")]
        url, where = field.get("URL", ""), field.get("Lokasi", "")
        if not (url and where and all(days)):
            continue
        readable += 1
        if not RUN_IN_BATAM.search(where) or days[-1] < today:
            continue
        fee_text = field.get("Biaya", "")
        # the fee list names the real distances (7.5K, 7.8K); the Jarak line rounds them
        lengths = sorted({float(n) for n in re.findall(r"\b(\d+(?:\.\d+)?)K\b", fee_text)})
        fees = [int(n.replace(".", "")) for n in re.findall(r"(?:Rp|IDR)\s?(\d[\d.]*\d)", fee_text)]
        run = {
            "id": "run-" + url.rstrip("/").rsplit("/", 1)[-1],
            "name": name.strip(),
            "start": days[0],
            "end": days[-1],
            "venue": re.sub(r"(, Batam)?, Kepulauan Riau$", "", where),
            "confirmed": False,
            "kind": "run",
            "sources": [{"label": "Indonesia Marathon", "url": url}],
        }
        if field.get("Jenis"):
            run["type"] = field["Jenis"]
        if lengths or field.get("Jarak"):
            run["distance"] = ", ".join(f"{n:g}K" for n in lengths) if lengths else field["Jarak"]
        if fees:
            run["fee_low"], run["fee_high"] = min(fees), max(fees)
        if field.get("Link pendaftaran resmi", "").startswith("https://"):
            run["signup"] = field["Link pendaftaran resmi"]
        runs.append(run)
    return readable, sorted(runs, key=lambda r: (r["start"], r["end"], r["id"]))


def runs_problem(readable, runs):
    if readable < RUN_BLOCKS_EXPECTED:
        return f"only {readable} readable runs in the whole calendar"
    for run in runs:
        if not run["name"] or not run["sources"][0]["url"].startswith("https://indonesiamarathon.com/event/"):
            return f"run {run['id']} has no name or an unexpected link"
        if run["start"] > run["end"]:
            return f"run {run['id']} ends before it starts"
    if len({r["id"] for r in runs}) != len(runs):
        return "duplicate run ids"
    return ""


def refresh_runs(block, today):
    """Updates block['runs'] from the run calendar. True when something changed."""
    try:
        text = Path(sys.argv[2]).read_text(encoding="utf-8") if len(sys.argv) > 2 else fetch(RUNS_SOURCE)
    except Exception as error:
        print(f"runs: could not read source ({error}); runs unchanged")
        return False
    readable, runs = parse_runs(text, today)
    problem = runs_problem(readable, runs)
    if problem:
        print(f"runs: source looks wrong ({problem}); runs unchanged")
        return False
    if block.get("runs") == runs and block.get("runs_source") == RUNS_SOURCE:
        print(f"runs: no change ({len(runs)} runs in Batam)")
        return False
    block.update({"runs_source": RUNS_SOURCE, "runs": runs})
    print(f"runs: updated from {RUNS_SOURCE}: {len(runs)} runs in Batam out of {readable}")
    return True


def refresh_events(block, today):
    """Updates block['list'] from batam.co.id. True when something changed."""
    try:
        page = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else fetch(SOURCE)
    except Exception as error:
        print(f"events: could not read source ({error}); events unchanged")
        return False
    events = parse(page, today)
    problem = sane(page, events)
    if problem:
        print(f"events: source looks wrong ({problem}); events unchanged")
        return False
    as_of = read_date(page, today)
    old_as_of = block.get("as_of", "")
    # commit only when the list itself changes, or weekly so the "read on" date never looks abandoned
    stale = not old_as_of or (datetime.date.fromisoformat(as_of) - datetime.date.fromisoformat(old_as_of)).days >= STALE_AFTER_DAYS
    if block.get("list") == events and block.get("source") == SOURCE and not stale:
        print(f"events: no change ({len(events)} events, read {as_of})")
        return False
    block.update({"source": SOURCE, "as_of": as_of, "list": events})
    unnamed = [e["id"] for e in events if e["id"] not in block["labels"]]
    print(f"events: updated from {SOURCE} ({as_of}): {len(events)} events" + (f"; no English/Chinese name yet for: {', '.join(unnamed)}" if unnamed else ""))
    return True


def main():
    source_text = DATA.read_text(encoding="utf-8")
    prefix = source_text[:source_text.index("{")]
    suffix = source_text[source_text.rindex("}") + 1:]
    data = json.loads(source_text[source_text.index("{"):source_text.rindex("}") + 1])
    today = datetime.datetime.now(BATAM_TIME).date().isoformat()
    block = data.setdefault("events", {})
    block.setdefault("note_en", "Read from batam.co.id, which names the news source behind every date. Dates can move, so check the source before you travel for an event.")
    block.setdefault("note_zh", "资料读取自 batam.co.id,每个日期都注明新闻来源。日期可能变动,专程前往前请先查看来源。")
    block.setdefault("manual", [])
    block.setdefault("hide", [])
    block.setdefault("labels", {})
    # each source is read on its own, so one being down never blocks the other
    events_changed = refresh_events(block, today)
    runs_changed = refresh_runs(block, today)
    if not (events_changed or runs_changed):
        return 0
    known = {e["id"] for key in ("list", "manual", "runs") for e in block.get(key, [])}
    block["labels"] = {event_id: label for event_id, label in block["labels"].items() if event_id in known}
    block["hide"] = [event_id for event_id in block["hide"] if event_id in known]
    DATA.write_text(prefix + json.dumps(data, ensure_ascii=False, indent=1) + suffix, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
