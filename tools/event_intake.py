"""Add one event to data.js from the "Add an event to What's on" issue form.

The owner fills a short form on GitHub (name, dates, venue, source link). The workflow
.github/workflows/add-event.yml passes the form text in ISSUE_BODY and this script checks it
and writes the event into events.manual, which the daily bot never touches.

Nothing is guessed: a missing or odd field stops the event from being added, and the reason
is written to intake-result.md so the workflow can post it back on the issue.

Editing the same issue replaces its event instead of adding a second one.
To try it here: set ISSUE_BODY (and ISSUE_NUMBER), then python tools/event_intake.py
"""
import datetime
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from events_refresh import BATAM_TIME, DATA, PLACES

RESULT = Path("intake-result.md")
APP = "https://juw12.github.io/batam-uncle-says/#events"
BAZAAR_CHOICE = "Bazaar or food market"
MAX_DAYS_LONG = 120
MAX_DAYS_AHEAD = 730
# first three letters of the month in English and Indonesian
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7,
    "aug": 8, "agu": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12,
}
FIELD = re.compile(r"^### (.+?)\s*$", re.M)


def read_form(body):
    """Issue forms arrive as '### Label', a blank line, then the answer."""
    pieces = FIELD.split(body.replace("\r\n", "\n"))
    answers = {}
    for label, answer in zip(pieces[1::2], pieces[2::2]):
        answer = answer.strip()
        answers[label.strip().lower()] = "" if answer == "_No response_" else answer
    return answers


def one_line(text, limit):
    text = "".join(ch if unicodedata.category(ch)[0] != "C" else " " for ch in text)
    return re.sub(r"\s+", " ", text).strip()[:limit + 1]


def read_day(text):
    """2026-12-05, 5 Dec 2026, 5 Desember 2026 or 5/12/2026 (day first). None if unreadable."""
    text = text.strip()
    try:
        match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
        if match:
            return datetime.date(int(match[1]), int(match[2]), int(match[3]))
        match = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", text)
        if match:
            return datetime.date(int(match[3]), int(match[2]), int(match[1]))
        match = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3})[A-Za-z]*\.?,? (\d{4})", text)
        if match and match[2].lower() in MONTHS:
            return datetime.date(int(match[3]), MONTHS[match[2].lower()], int(match[1]))
    except ValueError:
        return None
    return None


def build(answers, today, issue):
    """Return (event, problems). The event is only usable when problems is empty."""
    problems = []

    def text(label, limit, required=True):
        value = one_line(answers.get(label, ""), limit)
        if required and not value:
            problems.append(f"**{label.capitalize()}** is empty.")
        if len(value) > limit:
            problems.append(f"**{label.capitalize()}** is longer than {limit} characters.")
        return value

    name = text("event name", 120)
    venue = text("venue", 120)
    source_label = text("source name", 60)
    note_en = text("note in english", 300, required=False)
    note_zh = text("note in chinese", 300, required=False)

    url = answers.get("source link", "").strip()
    host = urlparse(url).hostname or ""
    if not re.fullmatch(r"https?://[^\s<>\"'`]{4,500}", url) or "." not in host:
        problems.append("**Source link** must be one full web address starting with http:// or https://.")

    start = read_day(answers.get("start date", ""))
    end_text = answers.get("end date", "")
    end = read_day(end_text) if end_text else start
    if not start:
        problems.append("**Start date** could not be read. Write it like 2026-12-05 or 5 Dec 2026.")
    if end_text and not end:
        problems.append("**End date** could not be read. Write it like 2026-12-07, or leave it empty for a one-day event.")
    if start and end:
        if end < start:
            problems.append("**End date** is before the start date.")
        elif end < today:
            problems.append(f"The event already ended ({end.isoformat()}). The app only shows events that are on now or still to come.")
        elif (end - start).days > MAX_DAYS_LONG:
            problems.append(f"The event runs longer than {MAX_DAYS_LONG} days. Check the dates.")
        elif (start - today).days > MAX_DAYS_AHEAD:
            problems.append("**Start date** is more than two years away. Check the year.")
    if problems:
        return None, problems

    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:50].strip("-") or "event"
    event = {
        "id": f"manual-{slug}-{start.year}",
        "name": name,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "venue": venue,
        "confirmed": bool(re.search(r"- \[[xX]\]", answers.get("confirmed", ""))),
    }
    if answers.get("kind", "") == BAZAAR_CHOICE:
        event["kind"] = "bazaar"
    if note_en:
        event["note_en"] = note_en
    if note_zh:
        event["note_zh"] = note_zh
    event["sources"] = [{"label": source_label, "url": url}]
    for words, place_id in PLACES.items():
        if words in venue.lower():
            event["place_id"] = place_id
    if issue:
        event["issue"] = issue
    return event, []


def save(event):
    """Put the event in events.manual, replacing the one from the same form or with the same id."""
    source_text = DATA.read_text(encoding="utf-8")
    prefix = source_text[:source_text.index("{")]
    suffix = source_text[source_text.rindex("}") + 1:]
    data = json.loads(source_text[source_text.index("{"):source_text.rindex("}") + 1])
    manual = data.setdefault("events", {}).setdefault("manual", [])
    same = lambda e: e["id"] == event["id"] or (event.get("issue") and e.get("issue") == event["issue"])
    replaced = any(same(e) for e in manual)
    manual[:] = [e for e in manual if not same(e)] + [event]
    DATA.write_text(prefix + json.dumps(data, ensure_ascii=False, indent=1) + suffix, encoding="utf-8", newline="\n")
    return replaced


def main():
    answers = read_form(os.environ.get("ISSUE_BODY", ""))
    issue_text = os.environ.get("ISSUE_NUMBER", "")
    issue = int(issue_text) if issue_text.isdigit() else None
    today = datetime.datetime.now(BATAM_TIME).date()
    event, problems = build(answers, today, issue)
    if problems:
        lines = ["Not added yet. Fix these, then edit this issue and save, and the bot reads it again:", ""]
        lines += [f"- {problem}" for problem in problems]
    else:
        replaced = save(event)
        dates = event["start"] if event["start"] == event["end"] else f"{event['start']} to {event['end']}"
        lines = [
            f"{'Updated' if replaced else 'Added'}: **{event['name']}**, {dates}, {event['venue']}.",
            "",
            f"It shows in the app in a few minutes: {APP}",
            "",
            f"Shown as {'date confirmed by the organiser' if event['confirmed'] else 'date reported, not confirmed'}"
            f"{', under Bazaars & food' if event.get('kind') == 'bazaar' else ''}. Source: {event['sources'][0]['url']}",
            "",
            "To change it, edit this issue and save. It leaves the app by itself the day after it ends.",
        ]
    RESULT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"ok={'false' if problems else 'true'}\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
