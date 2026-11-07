"""Weekly: re-read the Singapore-Batam ferry timetable from batam.co.id into data.js.

batam.co.id reads each operator's official timetable daily. This script copies, per route:
departure point, first and last daily sailing, number of sailings, and the last daily ferry back
from each Batam terminal. If the page cannot be read or looks wrong, data.js is left unchanged.
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.js"
SOURCE = "https://batam.co.id/transportasi/panduan-feri-batam-singapura-lima-pelabuhan/"
SG = ("HarbourFront", "Tanah Merah")
BATAM = ("Batam Centre", "Sekupang", "Harbour Bay", "Nongsapura", "Waterfront City", "Gold Coast Bengkong")
OPERATORS = {"Batamfast": "BatamFast", "Majestic": "Majestic Fast Ferry", "Sindo Ferry": "Sindo Ferry", "Horizon": "Horizon Fast Ferry"}
TERMINAL_NAMES = {"Nongsapura": "Nongsa Pura"}
QUALIFIERS = {"hari kerja": "weekdays", "akhir pekan & libur": "weekends and holidays"}
MONTHS = {m: i + 1 for i, m in enumerate(["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])}
PLACE = "|".join(SG + BATAM)
OPERATOR = "|".join(OPERATORS)
ROUTE = re.compile(
    rf"({PLACE}) → ({PLACE}) ({OPERATOR})((?: · [a-z &]+)?) ((?:\d{{2}}:\d{{2}}(?: \([^)]*\))? ?)+)"
)
LAST = re.compile(rf"({'|'.join(BATAM)}) → ({'|'.join(SG)})((?: [a-z &]+)?) ({OPERATOR}) (\d{{2}}:\d{{2}})")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (batam-uncle-bot)"})
    with urllib.request.urlopen(request, timeout=40) as response:
        html = response.read().decode("utf-8", errors="replace")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def read_date(page):
    match = re.search(r"terakhir (\d{1,2}) ([A-Z][a-z]+) (\d{4})", page)
    if match and match.group(2) in MONTHS:
        return datetime.date(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1))).isoformat()
    return datetime.date.today().isoformat()


def parse(page):
    start = page.find("Rute & operator Jam berangkat")
    end = page.find("Kapal terakhir dari Batam ke Singapura", start)
    block = page[start:end] if start >= 0 and end > start else ""
    outbound, inbound, seen = [], [], set()
    for origin, dest, operator, qualifier, times_text in ROUTE.findall(block):
        key = (origin, dest, operator, qualifier.strip(" ·"))
        if key in seen:
            continue
        seen.add(key)
        all_times = re.findall(r"\d{2}:\d{2}", times_text)
        daily = re.findall(r"(\d{2}:\d{2})(?! \()", times_text)
        row = {"operator": OPERATORS[operator], "first": all_times[0], "sailings": len(all_times)}
        if daily:
            row["last_daily"] = daily[-1]
        else:
            row["days"] = "Saturday and Sunday only" if "Sabtu" in times_text else "some days only"
            row["last_any"] = all_times[-1]
        q = qualifier.strip(" ·")
        if q:
            row["days"] = QUALIFIERS.get(q, q)
        if origin in SG:
            row.update({"sg": origin, "batam": TERMINAL_NAMES.get(dest, dest)})
            row.pop("last_any", None)
            outbound.append(row)
        else:
            row.update({"from": TERMINAL_NAMES.get(origin, origin), "to": dest})
            inbound.append(row)
    last_start = page.find("Kapal terakhir dari Batam ke Singapura")
    last_end = page.find("Kapal terakhir yang berlayar setiap hari", last_start)
    last_block = page[last_start:last_end] if last_start >= 0 and last_end > last_start else ""
    last_daily = []
    for origin, dest, qualifier, operator, time_text in LAST.findall(last_block):
        row = {"from": TERMINAL_NAMES.get(origin, origin), "to": dest, "operator": OPERATORS[operator], "time": time_text}
        q = qualifier.strip()
        if q:
            row["days"] = QUALIFIERS.get(q, q)
        last_daily.append(row)
    # terminals with no daily sailing back: use the last sailing on the days it runs
    covered = {r["from"] for r in last_daily}
    for row in inbound:
        if row["from"] not in covered and "last_any" in row:
            last_daily.append({"from": row["from"], "to": row["to"], "operator": row["operator"], "time": row["last_any"], "days": row["days"]})
            covered.add(row["from"])
    return outbound, last_daily


def sane(outbound, last_daily):
    if len(outbound) < 8 or len(last_daily) < 6:
        return f"too few rows (routes {len(outbound)}, last ferries {len(last_daily)})"
    for row in outbound + last_daily:
        for field in ("first", "last_daily", "time"):
            value = row.get(field)
            if value and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
                return f"bad time {value}"
    if {r["batam"] for r in outbound} - {r["from"] for r in last_daily}:
        return "a terminal has departures but no ferry back"
    return ""


def main():
    source_text = DATA.read_text(encoding="utf-8")
    prefix = source_text[:source_text.index("{")]
    suffix = source_text[source_text.rindex("}") + 1:]
    data = json.loads(source_text[source_text.index("{"):source_text.rindex("}") + 1])
    try:
        page = fetch(SOURCE)
    except Exception as error:
        print(f"timetable: could not read source ({error}); data unchanged")
        return 0
    outbound, last_daily = parse(page)
    problem = sane(outbound, last_daily)
    if problem:
        print(f"timetable: source looks wrong ({problem}); data unchanged")
        return 0
    as_of = read_date(page)
    data.setdefault("routes", {}).update({"source": SOURCE, "as_of": as_of, "list": outbound})
    data["routes"].setdefault("note_en", "Departures from Singapore to Batam, Singapore time (SGT), read from each operator's official timetable.")
    data.setdefault("return_ferries", {}).update({"source": SOURCE, "as_of": as_of, "last": last_daily})
    data["return_ferries"].setdefault("note_en", "Last daily sailing from Batam to Singapore, Batam time (WIB). Arrive at the terminal about 1 hour before.")
    for ferry in data.get("ferries", []):
        own = [r for r in outbound if r["operator"] == ferry["operator"]]
        if not own:
            continue
        ferry["batam"] = list(dict.fromkeys(r["batam"] for r in own))
        ferry["sg"] = list(dict.fromkeys(r["sg"] for r in own))
        lasts = [r["last_daily"] for r in own if r.get("last_daily")]
        ferry["first_last_from_sg"] = f"{min(r['first'] for r in own)} / {max(lasts) if lasts else '-'}"
        ferry["routes_source"] = SOURCE
    new_text = prefix + json.dumps(data, ensure_ascii=False, indent=1) + suffix
    if new_text != source_text:
        DATA.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"timetable: updated from {SOURCE} ({as_of}): {len(outbound)} routes, {len(last_daily)} last ferries back")
    else:
        print("timetable: no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
