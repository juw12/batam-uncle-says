"""Build files that depend on partners.json and data.js (runs in GitHub Actions after partners_check.py).

Writes: partners.js (read by the app), driver-prices/index.html and ferry/index.html. Bumps the service worker VERSION when
partners.js changes so installed copies pick up the new list.
"""
import datetime
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://juw12.github.io/batam-uncle-says/"


def esc(value):
    return html.escape(str(value), quote=True)


def fmt_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


def write_if_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != content:
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")
        return True
    return False


def load_data_js():
    text = (ROOT / "data.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


def page(title, description, canonical, body):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from site_template import page as template_page
    return template_page(title, description, canonical.replace(SITE, ""), body)


def operator_message():
    return "Hi, I found you on Batam Uncle Says. I would like a quote for a Batam day trip. Date: , People: , Ferry arrival time: "


def driver_page(partners):
    active = [op for op in partners["operators"] if op["status"] == "active"]
    cards = []
    for op in active:
        rows = "".join(
            f"<tr><td>{esc(p['label'])}</td><td class=\"num\">S${p['sgd']}</td></tr>" for p in op["prices"]
        ) or "<tr><td>See their website for current prices</td><td></td></tr>"
        langs = f" · Languages: {esc(', '.join(op['languages']))}" if op.get("languages") else ""
        wa = f"https://wa.me/{op['whatsapp']}?text={quote(operator_message())}"
        cards.append(f"""<div class="card">
  <h2>{esc(op['name'])}</h2>
  <table>{rows}</table>
  <p class="meta">{esc(op['price_note'])}{langs}. Checked {fmt_date(op['checked'])}.</p>
  <a class="btn" href="{wa}" rel="nofollow noopener">Message on WhatsApp</a><a class="btn ghost" href="{esc(op['website'])}" rel="nofollow noopener">Their website</a>
</div>""")
    charter = partners["charter"]
    body = f"""<h1>Batam private driver prices from Singapore</h1>
<p class="lede">A car with an English-speaking driver for a full day in Batam usually costs S${charter['mpv_sgd'][0]}–{charter['mpv_sgd'][1]} for an MPV and S${charter['van_sgd'][0]}–{charter['van_sgd'][1]} for a van, based on prices Batam operators publish. Below are drivers who list their prices and WhatsApp number on their own website, re-checked every week.</p>
{''.join(cards)}
<div class="card">
  <h2>Plan the day around your ferry</h2>
  <p>Batam Uncle Says builds a timed plan from your ferry times and fills it into your WhatsApp message to the driver.</p>
  <a class="btn" href="../#guide">Open the driver page in the app</a><a class="btn ghost" href="../#plan">Plan my day</a>
</div>
<p class="meta">Licensed guides in Batam hold a guide card (KTPP) from the city tourism office (<a href="{esc(partners['licence_source'])}" rel="nofollow noopener">rule</a>). Ask to see it if you book a guide. Page updated {fmt_date(partners['updated'])}.</p>"""
    return page(
        "Batam private driver prices from Singapore (checked weekly)",
        f"Full-day car and English-speaking driver in Batam from S${charter['mpv_sgd'][0]}. Published prices and WhatsApp contacts of Batam drivers, re-checked every week.",
        SITE + "driver-prices/",
        body,
    )


def ferry_page(data, partners):
    rows = []
    for f in data["ferries"]:
        fare = f"S${f['return_all_in_sgd']}" if f.get("return_all_in_sgd") else "See note"
        note = f" · {esc(f['fare_note'])}" if not f.get("return_all_in_sgd") and f.get("fare_note") else ""
        rows.append(
            f"<tr><td><a href=\"{esc(f['url'])}\" rel=\"nofollow noopener\">{esc(f['operator'])}</a><br>"
            f"<span class=\"meta\">{esc(' / '.join(f['sg']))} to {esc(', '.join(f['batam']))} · {esc(f['minutes'])} min · first/last from SG {esc(f['first_last_from_sg'])}{note}</span></td>"
            f"<td class=\"num\">{fare}</td></tr>"
        )
    booking = partners["ferry_booking"]["easybook"] + partners["affiliates"].get("easybook_query", "")
    sources = sorted({f["source"] for f in data["ferries"]})
    body = f"""<h1>Singapore to Batam ferry: operators, fares and terminals</h1>
<p class="lede">Ferries leave from HarbourFront and Tanah Merah and take about 50 to 70 minutes. Return fares below are all-in where the operator lists them.</p>
<div class="card"><table><tr><th>Operator and route</th><th class="num">Return, all-in</th></tr>{''.join(rows)}</table>
<p class="meta">Fares from published sources, not checked at the counter. Confirm on the operator's site. Sources: {' · '.join(f'<a href="{esc(s)}" rel="nofollow noopener">{esc(s.split("/")[2])}</a>' for s in sources)}</p>
<a class="btn" href="{esc(booking)}" rel="nofollow noopener sponsored">Compare and book tickets online</a></div>
<div class="card">
  <h2>Plan your day around the ferry</h2>
  <p>Enter your arrival and return ferry times and get a timed plan with a leave-by countdown, a price check and entry rules. Works offline.</p>
  <a class="btn" href="../#plan">Plan my day</a><a class="btn ghost" href="../#ferry">Ferry details in the app</a>
</div>"""
    return page(
        "Singapore to Batam ferry: operators, fares and terminals",
        "Compare Singapore to Batam ferries: BatamFast, Majestic, Sindo and more. All-in return fares, terminals, first and last ferries, and a day planner.",
        SITE + "ferry/",
        body,
    )


def main():
    partners = json.loads((ROOT / "partners.json").read_text(encoding="utf-8"))
    data = load_data_js()
    js = "/* Generated from partners.json by tools/partners_build.py. Edit the JSON, not this file. */\nwindow.BUS_PARTNERS = " + json.dumps(partners, ensure_ascii=False, indent=1) + ";\n"
    js_changed = write_if_changed(ROOT / "partners.js", js)
    write_if_changed(ROOT / "driver-prices" / "index.html", driver_page(partners))
    write_if_changed(ROOT / "ferry" / "index.html", ferry_page(data, partners))
    # sitemap.xml, robots.txt and llms.txt are written by tools/seo_build.py
    if js_changed:
        sw_path = ROOT / "sw.js"
        sw = sw_path.read_text(encoding="utf-8")
        sw = re.sub(r'const VERSION = "([^"]+)";', f'const VERSION = "bus-{datetime.date.today().isoformat()}-p{datetime.datetime.now().strftime("%H%M")}";', sw, count=1)
        sw_path.write_text(sw, encoding="utf-8", newline="\n")
        print("bumped sw.js VERSION")


if __name__ == "__main__":
    main()
