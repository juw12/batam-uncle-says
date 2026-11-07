"""Build search pages from data.js, photos.js and partners.json (runs weekly in GitHub Actions).

Writes: prices/, entry-rules/, money/, places/, area/<area>/, day-trip/, terminal/<terminal>/ pages (day-trip and terminal also in Chinese under zh/), sitemap.xml, robots.txt, llms.txt.
Everything comes from the app's own sourced data; nothing is invented here.
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_template import SITE, esc, page  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CATEGORY = {"eat": "Food", "spa": "Massage and spa", "shop": "Shopping", "play": "Things to do", "stay": "Hotels and resorts"}


def load_js_object(path, name):
    text = path.read_text(encoding="utf-8")
    start = text.index(name)
    brace = text.index("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[brace:i + 1])
    raise ValueError(name)


def write_if_changed(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != content:
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT)}")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fmt_date(iso, lang="en"):
    d = datetime.date.fromisoformat(iso)
    if lang == "zh":
        return f"{d.year}年{d.month}月{d.day}日"
    return f"{d.day} {d.strftime('%b %Y')}"


def idr(n):
    return "Rp " + f"{n:,.0f}".replace(",", ".")


def source_link(url):
    return f'<a href="{esc(url)}" rel="nofollow noopener">{esc(url.split("/")[2].replace("www.", ""))}</a>'


def prices_page(data, partners):
    rate = data["rules"]["fx_mid_market_sgd_idr"]
    rows = []
    sources = set()
    for p in data["prices"]:
        if p.get("low") is None:
            continue
        if p["currency"] == "IDR":
            main = f"{idr(p['low'])} – {idr(p['high']).replace('Rp ', '')}"
            other = f"about S${p['low'] / rate:,.0f} – {p['high'] / rate:,.0f}"
        else:
            main = f"S${p['low']} – {p['high']}"
            other = f"about {idr(p['low'] * rate)} – {idr(p['high'] * rate).replace('Rp ', '')}"
        rows.append(f"<tr><td>{esc(p['en'])}<br><span class=\"meta\">{other}</span></td><td class=\"num\">{main}</td></tr>")
        if p.get("source"):
            sources.add(p["source"])
    charter = partners["charter"]
    rows.append(
        f"<tr><td>Car with English-speaking driver, full day (MPV)<br><span class=\"meta\">see <a href=\"../driver-prices/\">driver prices</a></span></td>"
        f"<td class=\"num\">S${charter['mpv_sgd'][0]} – {charter['mpv_sgd'][1]}</td></tr>"
    )
    body = f"""<h1>How much things cost in Batam (SGD and rupiah)</h1>
<p class="lede">Typical price ranges for the things Singapore day-trippers pay for most, so you can tell if a quote is fair. Converted at the mid-market rate of S$1 = {idr(rate)} ({fmt_date(data['rules']['fx_date'])}, {source_link(data['rules']['fx_source'])}).</p>
<div class="card"><table><tr><th>Item</th><th class="num">Usual range</th></tr>{''.join(rows)}</table>
<p class="meta">{esc(data['rules'].get('fx_terminal_penalty', ''))}. Ranges from published guides, not yet checked in person. Sources: {' · '.join(source_link(s) for s in sorted(sources))}</p></div>
<div class="card"><h2>Check a quote before you pay</h2><p>Type the price a shop or driver quoted you and the app tells you if it is low, fair or high, in both currencies.</p>
<a class="btn" href="../#price">Check a price</a><a class="btn ghost" href="../#money">Currency converter</a></div>"""
    return page(
        "Batam prices in SGD and rupiah: massage, seafood, Grab, hotels",
        f"What things cost in Batam for Singapore visitors: massage, seafood dinner, Grab, meals, hotels and a driver for the day, in rupiah and SGD at S$1 = {idr(rate)}.",
        "prices/",
        body,
    )


def entry_page(data):
    items = "".join(f"<li>{esc(e['en'])} <span class=\"meta\">({source_link(e['source'])})</span></li>" for e in data["rules"]["entry"])
    body = f"""<h1>Singapore to Batam entry rules: passport, arrival cards, duty-free</h1>
<p class="lede">What Singapore residents need for a Batam day trip, in both directions. {esc(data['rules']['timezone_note'])}.</p>
<div class="card"><ul class="list">{items}</ul></div>
<div class="card"><h2>Tick it off before you leave</h2><p>The app has a checklist for both terminals that remembers what you have done.</p>
<a class="btn" href="../#check">Open the checklist</a><a class="btn ghost" href="../ferry/">Ferry operators and fares</a></div>"""
    return page(
        "Singapore to Batam entry rules: passport, arrival card, duty-free (day trip)",
        "Batam day trip from Singapore: visa-free stay, passport validity, All Indonesia arrival card, SG Arrival Card on the way back, and duty-free limits for short trips.",
        "entry-rules/",
        body,
    )


def money_page(data):
    rate = data["rules"]["fx_mid_market_sgd_idr"]
    tips = "".join(f"<li>{esc(t['en'])} <span class=\"meta\">({source_link(t['source'])})</span></li>" for t in data["rules"]["money_tips"])
    examples = "".join(f"<tr><td>S${s}</td><td class=\"num\">{idr(s * rate)}</td></tr>" for s in (10, 20, 50, 100, 200))
    body = f"""<h1>Money in Batam: exchange rate, cash and paying by QR</h1>
<p class="lede">Mid-market rate on {fmt_date(data['rules']['fx_date'])}: S$1 = {idr(rate)} ({source_link(data['rules']['fx_source'])}). {esc(data['rules'].get('fx_terminal_penalty', ''))}.</p>
<div class="card"><table><tr><th>Singapore dollars</th><th class="num">Rupiah, mid-market</th></tr>{examples}</table></div>
<div class="card"><h2>Tips</h2><ul class="list">{tips}</ul></div>
<div class="card"><h2>Convert any amount</h2><p>The converter in the app works offline and lets you set the rate the money changer gives you.</p>
<a class="btn" href="../#money">Open the converter</a><a class="btn ghost" href="../prices/">Typical prices</a></div>"""
    return page(
        f"Batam exchange rate and money tips: S$1 = {idr(rate)}",
        "Money for a Batam day trip: today's SGD to rupiah rate, how much worse terminal counters are, licensed money changers, cash vs QRIS, Grab and Gojek.",
        "money/",
        body,
    )


def place_card(place, photos, place_photos, root):
    key = place_photos.get(place["id"])
    img = ""
    if key and key in photos:
        p = photos[key]
        img = (f'<img src="{root}{esc(p["src"])}" width="{p["w"]}" height="{p["h"]}" alt="{esc(p["en"])}" loading="lazy">'
               f'<p class="meta">Photo: {esc(p["author"])}, <a href="{esc(p["page"])}" rel="nofollow noopener">{esc(p["license"])}</a></p>')
    source = f" · Source: {source_link(place['source'])}" if place.get("source") else ""
    return f"""<div class="card">{img}
  <h2>{esc(place['name'])}</h2>
  <p>{esc(place['note_en'])}</p>
  <p class="meta">{CATEGORY.get(place['category'], place['category'])} · {esc(place['area'])}{source} · Not yet visited in person; check opening hours.</p>
  <a class="btn ghost" href="{root}?place={esc(place['id'])}#places">Open in the app</a>
</div>"""


def area_pages(data, photos, place_photos):
    areas = {}
    for place in data["places"]:
        areas.setdefault(place["area"], []).append(place)
    out = {}
    for area, places in sorted(areas.items()):
        cats = sorted({CATEGORY.get(p["category"], p["category"]).lower() for p in places})
        body = f"""<h1>{esc(area)}, Batam: {', '.join(cats)}</h1>
<p class="lede">{len(places)} places in {esc(area)} that Singapore day-trippers look for, from published guides. Plan them around your ferry times in the app.</p>
{''.join(place_card(p, photos, place_photos, '../../') for p in places)}
<div class="card"><h2>Getting there</h2><p>Book a car with an English-speaking driver, or plan a Grab route around your ferry.</p>
<a class="btn" href="../../driver-prices/">Driver prices</a><a class="btn ghost" href="../../#plan">Plan my day</a></div>"""
        path = f"area/{slug(area)}/"
        out[path] = page(
            f"{area}, Batam: {', '.join(cats)} for a day trip from Singapore",
            f"{len(places)} places in {area}, Batam for Singapore visitors: " + ", ".join(p["name"] for p in places[:5]) + ".",
            path,
            body,
            root="../../",
            crumbs=[("Places", SITE + "places/"), (area, SITE + path)],
        )
    return areas, out


def places_index(areas):
    blocks = []
    for area, places in sorted(areas.items()):
        items = "".join(f"<li>{esc(p['name'])} <span class=\"meta\">({CATEGORY.get(p['category'], p['category'])})</span></li>" for p in places)
        blocks.append(f'<div class="card"><h2><a href="../area/{slug(area)}/">{esc(area)}</a></h2><ul class="list">{items}</ul></div>')
    total = sum(len(v) for v in areas.values())
    body = f"""<h1>Things to do in Batam, by area</h1>
<p class="lede">{total} restaurants, spas, malls, sights and hotels across {len(areas)} areas of Batam, from published guides.</p>
{''.join(blocks)}"""
    return page(
        "Things to do in Batam by area: food, spas, malls, sights, hotels",
        f"{total} places in Batam for Singapore day-trippers, grouped by area: Nagoya, Harbour Bay, Batam Centre, Nongsa, Barelang and more.",
        "places/",
        body,
    )


TERMINAL_AREA = {"Nongsa Pura": "Nongsa", "Gold Coast Bengkong": "Bengkong"}


DAYS_ZH = {"weekends and holidays": "周末及公休日", "Saturday and Sunday only": "仅周六、周日", "weekdays": "平日"}
CATEGORY_ZH = {"eat": "美食", "spa": "按摩与 Spa", "shop": "购物", "play": "景点与活动", "stay": "酒店与度假村"}


def category(cat, lang="en"):
    return (CATEGORY_ZH if lang == "zh" else CATEGORY).get(cat, cat)


def category_word(cat, lang="en"):
    """Category as a word inside a sentence: lower-case in English, unchanged in Chinese."""
    return category(cat, lang) if lang == "zh" else category(cat).lower()


def localized(obj, key, lang):
    """obj[key] in English; obj[key + '_zh'] (or obj['zh'] when key is 'en') in Chinese, falling back to English."""
    if lang == "zh":
        return obj.get("zh" if key == "en" else f"{key}_zh") or obj[key]
    return obj[key]


def days_text(days, lang="en"):
    return DAYS_ZH.get(days, days) if lang == "zh" else days


def ferry_fare(ferry, lang="en"):
    if ferry.get("return_all_in_sgd"):
        return f"S${ferry['return_all_in_sgd']}"
    if ferry.get("return_all_in_est_sgd"):
        return f"{'约 ' if lang == 'zh' else 'about '}S${ferry['return_all_in_est_sgd']}"
    return "见备注" if lang == "zh" else "See note"


def last_back(data, terminal):
    """Last sailings from a Batam terminal to Singapore, latest first."""
    rows = [r for r in data.get("return_ferries", {}).get("last", []) if r["from"] == terminal]
    return sorted(rows, key=lambda r: r["time"], reverse=True)


def last_back_text(row, lang="en"):
    if lang == "zh":
        days = f"({days_text(row['days'], lang)})" if row.get("days") else ""
        return f"{row['time']} {row['operator']} 往 {row['to']}{days}"
    days = f", {row['days']}" if row.get("days") else ""
    return f"{row['time']} {row['operator']} to {row['to']}{days}"


def ferry_note(ferry, lang="en"):
    if not ferry.get("return_all_in_sgd") and ferry.get("fare_note"):
        return f" · {esc(localized(ferry, 'fare_note', lang))}"
    return ""


def terminals(data):
    """Batam terminal name -> list of ferries that serve it, in data order."""
    out = {}
    for ferry in data["ferries"]:
        for terminal in ferry["batam"]:
            out.setdefault(terminal, []).append(ferry)
    return out


def booking_url(partners):
    return partners["ferry_booking"]["easybook"] + partners["affiliates"].get("easybook_query", "")


def as_of(data, lang="en"):
    """Date of the newest dataset shown on a page (timetables or exchange rate)."""
    dates = [data["rules"]["fx_date"], data.get("routes", {}).get("as_of", ""), data.get("return_ferries", {}).get("as_of", "")]
    return fmt_date(max(d for d in dates if d), lang)


def zh_path(path):
    return "zh/" + path


def terminal_facts(data, terminal, ferries, lang):
    """Numbers and sentences shared by the English and Chinese terminal pages (same data, same rules)."""
    zh = lang == "zh"
    rate = data["rules"]["fx_mid_market_sgd_idr"]
    area = TERMINAL_AREA.get(terminal, terminal)
    terminal_routes = [r for r in data.get("routes", {}).get("list", []) if r["batam"] == terminal]
    facts = {
        "area": area,
        "nearby": [p for p in data["places"] if p["area"] == area],
        "sg_sides": sorted({r["sg"] for r in terminal_routes}) or sorted({s for f in ferries for s in f["sg"]}),
        "minutes": [int(n) for f in ferries for n in f["minutes"].split("-")],
        "operator_names": ", ".join(f["operator"] for f in ferries),
    }
    facts["firsts"] = sorted(r["first"] for r in terminal_routes) or sorted(f["first_last_from_sg"].split(" / ")[0] for f in ferries)
    facts["lasts"] = sorted(r["last_daily"] for r in terminal_routes if r.get("last_daily")) or facts["firsts"]

    fares = [(f.get("return_all_in_sgd") or f.get("return_all_in_est_sgd"), bool(f.get("return_all_in_sgd")), f["operator"]) for f in ferries]
    fares = [x for x in fares if x[0]]
    if not fares:
        fare_fact = "见下方各船公司的票价备注" if zh else "see each operator's fare note below"
    elif len({x[0] for x in fares}) == 1:
        names = esc(("、" if zh else ", ").join(x[2] for x in fares))
        fare_fact = f"<strong>S${fares[0][0]}</strong> 来回,含税费({names})" if zh else f"<strong>S${fares[0][0]}</strong> return, all-in ({names})"
    else:
        low_value = min(x[0] for x in fares)
        high_value = max(x[0] for x in fares)
        sep = "、" if zh else ", "
        low_names = esc(sep.join(x[2] for x in fares if x[0] == low_value))
        high_names = esc(sep.join(x[2] for x in fares if x[0] == high_value))
        high_exact = all(x[1] for x in fares if x[0] == high_value)
        if zh:
            fare_fact = (
                f"<strong>S${low_value}</strong>({low_names})至 <strong>{'' if high_exact else '约 '}S${high_value}</strong>({high_names}),来回含税费"
            )
        else:
            fare_fact = (
                f"<strong>S${low_value}</strong> ({low_names}) to <strong>{'' if high_exact else 'about '}S${high_value}</strong> ({high_names}) return, all-in"
            )
    facts["fare_fact"] = fare_fact

    def route_lines(f):
        lines = []
        for r in terminal_routes:
            if r["operator"] != f["operator"]:
                continue
            if zh:
                last = f",末班 {r['last_daily']}" if r.get("last_daily") else ""
                days = f"({esc(days_text(r['days'], lang))})" if r.get("days") else ""
                lines.append(f"{esc(r['sg'])} 出发:首班 {r['first']}{last},共 {r['sailings']} 班{days}")
            else:
                last = f"last {r['last_daily']}" if r.get("last_daily") else ""
                days = f" ({r['days']})" if r.get("days") else ""
                lines.append(f"from {esc(r['sg'])}: first {r['first']}{', ' + last if last else ''}, {r['sailings']} sailings{esc(days)}")
        if lines:
            return "<br>".join(lines)
        return f"{esc(' / '.join(f['sg']))} 出发" if zh else f"from {esc(' / '.join(f['sg']))}"

    minutes_word = "分钟" if zh else "min"
    facts["operator_rows"] = "".join(
        f"<tr><td><a href=\"{esc(f['url'])}\" rel=\"nofollow noopener\">{esc(f['operator'])}</a> <span class=\"meta\">· {esc(f['minutes'])} {minutes_word}</span><br>"
        f"<span class=\"meta\">{route_lines(f)}{ferry_note(f, lang)}</span></td>"
        f"<td class=\"num\">{ferry_fare(f, lang)}</td></tr>"
        for f in ferries
    )
    facts["sources"] = sorted({f["source"] for f in ferries} | ({data['routes']['source']} if terminal_routes else set()))

    extras = []
    for price in data["prices"]:
        if terminal.lower() in price["en"].lower() and price.get("low") is not None:
            if zh:
                extras.append(
                    f"<li>{esc(localized(price, 'en', lang))}:<strong>{idr(price['low'])} – {idr(price['high']).replace('Rp ', '')}</strong>"
                    f"(约 S${price['low'] / rate:,.0f} – {price['high'] / rate:,.0f})<span class=\"meta\">({source_link(price['source'])})</span></li>"
                )
            else:
                extras.append(
                    f"<li>{esc(price['en'])}: <strong>{idr(price['low'])} – {idr(price['high']).replace('Rp ', '')}</strong> "
                    f"(about S${price['low'] / rate:,.0f} – {price['high'] / rate:,.0f}) <span class=\"meta\">({source_link(price['source'])})</span></li>"
                )
    queue = data["rules"].get("queue_warning", {})
    if queue and terminal.lower() in queue["en"].lower():
        if zh:
            extras.append(f"<li>{esc(localized(queue, 'en', lang))}<span class=\"meta\">({source_link(queue['source'])})</span></li>")
        else:
            extras.append(f"<li>{esc(queue['en'])} <span class=\"meta\">({source_link(queue['source'])})</span></li>")
    end = "。" if zh else "."
    extras.append(f"<li>{esc(localized(data['rules'], 'fx_terminal_penalty', lang))}{end}</li>")
    extras.append(f"<li>{esc(localized(data['rules'], 'timezone_note', lang))}{end}</li>")
    facts["extras"] = "".join(extras)

    returns = last_back(data, terminal)
    facts["returns"] = returns
    daily = [r for r in returns if not r.get("days")]
    if daily:
        if zh:
            facts["last_fact"] = f"<strong>{daily[0]['time']}</strong> 巴淡时间({esc(daily[0]['operator'])} 往 {esc(daily[0]['to'])})"
        else:
            facts["last_fact"] = f"<strong>{daily[0]['time']}</strong> Batam time ({esc(daily[0]['operator'])} to {esc(daily[0]['to'])})"
    elif returns:
        facts["last_fact"] = (
            f"没有每日回程班次;{esc(last_back_text(returns[0], lang))}" if zh else f"No daily sailing back; {esc(last_back_text(returns[0]))}"
        )
    else:
        facts["last_fact"] = "请向船公司查询" if zh else "Check with the operator"
    facts["return_items"] = "".join(f"<li>{esc(last_back_text(r, lang))}</li>" for r in returns)
    return facts


def terminal_pages(data, photos, place_photos, partners):
    out = {}
    for terminal, ferries in terminals(data).items():
        path = f"terminal/{slug(terminal)}/"
        alternates = {"en": path, "zh": zh_path(path)}
        for lang in ("en", "zh"):
            out[alternates[lang]] = terminal_page(data, partners, terminal, ferries, lang, alternates)
    return out


def terminal_page(data, partners, terminal, ferries, lang, alternates):
    f = terminal_facts(data, terminal, ferries, lang)
    minutes = f["minutes"]
    area = f["area"]
    rf = data.get("return_ferries", {})
    if lang == "en":
        nearby_html = ""
        if f["nearby"]:
            items = "".join(f"<li>{esc(p['name'])} <span class=\"meta\">({category(p['category'])})</span></li>" for p in f["nearby"])
            nearby_html = (
                f'<div class="card"><h2>Near the terminal: {esc(area)}</h2><ul class="list">{items}</ul>'
                f'<p class="meta">From published guides, not visited in person.</p>'
                f'<a class="btn" href="../../area/{slug(area)}/">See all of {esc(area)}</a></div>'
            )
        returns_card = ""
        if f["returns"]:
            returns_card = (
                f'<div class="card"><h2>Last ferries back to Singapore</h2><ul class="list">{f["return_items"]}</ul>'
                f'<p class="meta">Batam time (WIB). {esc(rf["note_en"].split(". ", 1)[1])} Source for both: {source_link(rf["source"])}, as of {fmt_date(rf["as_of"])}; check on the day.</p>'
                f'<a class="btn" href="../../#plan">Plan my day around the return ferry</a></div>'
            )
        body = f"""<h1>{esc(terminal)} ferry terminal, Batam: ferries from Singapore</h1>
<div class="card"><table>
<tr><td>Ferries from</td><td>{esc(' and '.join(f['sg_sides']))}</td></tr>
<tr><td>Operators</td><td>{esc(f['operator_names'])}</td></tr>
<tr><td>Crossing</td><td><strong>{min(minutes)} – {max(minutes)} min</strong></td></tr>
<tr><td>From Singapore</td><td>first <strong>{f['firsts'][0]}</strong>, last <strong>{f['lasts'][-1]}</strong> (Singapore time)</td></tr>
<tr><td>Fare</td><td>{f['fare_fact']}</td></tr>
<tr><td>Last ferry back</td><td>{f['last_fact']}</td></tr>
</table>
<p class="meta">{esc(data['rules']['timezone_note'])}. Published times and fares as of {as_of(data)}, not checked at the counter.</p>
<a class="btn" href="{esc(booking_url(partners))}" rel="nofollow noopener sponsored">Compare and book tickets</a></div>
<div class="card"><h2>Operators to {esc(terminal)}</h2><table><tr><th>Operator</th><th class="num">Return, all-in</th></tr>{f['operator_rows']}</table>
<p class="meta">Confirm times on the operator's site (linked above). Sources: {' · '.join(source_link(s) for s in f['sources'])}</p>
<a class="btn ghost" href="../../ferry/">Compare all terminals</a></div>
{returns_card}
<div class="card"><h2>Good to know at {esc(terminal)}</h2><ul class="list">{f['extras']}</ul>
<a class="btn" href="../../money/">Exchange rate and money tips</a></div>
{nearby_html}
<div class="card"><h2>Getting around from {esc(terminal)}</h2><p>Message a driver directly on WhatsApp with your ferry time, or plan the day around your return ferry.</p>
<a class="btn" href="../../driver-prices/">WhatsApp a driver</a><a class="btn ghost" href="../../#plan">Plan my day</a></div>"""
        return page(
            f"{terminal} ferry terminal, Batam: ferries from Singapore, times, fares",
            f"Ferries from Singapore to {terminal}, Batam: {f['operator_names']}. {min(minutes)}-{max(minutes)} min crossing, first {f['firsts'][0]}, last {f['lasts'][-1]}, last ferry back, fares and what is nearby.",
            alternates["en"],
            body,
            root="../../",
            crumbs=[("Ferry", SITE + "ferry/"), (f"{terminal} terminal", SITE + alternates["en"])],
            alternates=alternates,
        )

    root = "../../../"
    nearby_html = ""
    if f["nearby"]:
        items = "".join(f"<li>{esc(p['name'])}<span class=\"meta\">({category(p['category'], 'zh')})</span></li>" for p in f["nearby"])
        nearby_html = (
            f'<div class="card"><h2>码头附近:{esc(area)}</h2><ul class="list">{items}</ul>'
            f'<p class="meta">资料来自公开指南,未实地走访。</p>'
            f'<a class="btn" href="{root}area/{slug(area)}/">查看 {esc(area)} 全部地点(英文页)</a></div>'
        )
    returns_card = ""
    if f["returns"]:
        returns_card = (
            f'<div class="card"><h2>回新加坡的末班船</h2><ul class="list">{f["return_items"]}</ul>'
            f'<p class="meta">巴淡时间(WIB)。{esc(rf["note_zh"].split("。", 1)[1])}两项来源:{source_link(rf["source"])},截至 {fmt_date(rf["as_of"], "zh")};出发当天请再核实。</p>'
            f'<a class="btn" href="{root}?lang=zh#plan">按回程船班规划我的一天</a></div>'
        )
    operators_zh = esc(f["operator_names"].replace(", ", "、"))
    body = f"""<h1>巴淡 {esc(terminal)} 码头:新加坡渡轮班次和票价</h1>
<div class="card"><table class="facts">
<tr><td>出发码头</td><td>{esc(' 和 '.join(f['sg_sides']))}</td></tr>
<tr><td>船公司</td><td>{operators_zh}</td></tr>
<tr><td>船程</td><td><strong>{min(minutes)} – {max(minutes)} 分钟</strong></td></tr>
<tr><td>出发时间</td><td>首班 <strong>{f['firsts'][0]}</strong>,末班 <strong>{f['lasts'][-1]}</strong>(新加坡时间)</td></tr>
<tr><td>票价</td><td>{f['fare_fact']}</td></tr>
<tr><td>回程末班</td><td>{f['last_fact']}</td></tr>
</table>
<p class="meta">{esc(data['rules']['timezone_note_zh'])}。班次和票价为截至 {as_of(data, 'zh')} 的公开资料,未在柜台核实。</p>
<a class="btn" href="{esc(booking_url(partners))}" rel="nofollow noopener sponsored">比较并预订船票</a></div>
<div class="card"><h2>往 {esc(terminal)} 的船公司</h2><table><tr><th>船公司</th><th class="num">来回含税费</th></tr>{f['operator_rows']}</table>
<p class="meta">请在船公司官网(上方链接)核实班次。来源:{' · '.join(source_link(s) for s in f['sources'])}</p>
<a class="btn ghost" href="{root}ferry/">比较所有码头(英文页)</a></div>
{returns_card}
<div class="card"><h2>{esc(terminal)} 实用信息</h2><ul class="list">{f['extras']}</ul>
<a class="btn" href="{root}money/">汇率和换钱提示(英文页)</a></div>
{nearby_html}
<div class="card"><h2>从 {esc(terminal)} 出发怎么走</h2><p>直接用 WhatsApp 联系司机,告诉他你的船班时间;或按回程船班规划一天。</p>
<a class="btn" href="{root}driver-prices/">WhatsApp 联系司机</a><a class="btn ghost" href="{root}?lang=zh#plan">规划我的一天</a></div>"""
    return page(
        f"巴淡 {terminal} 码头:新加坡渡轮班次、票价、回程末班",
        f"新加坡往巴淡 {terminal} 码头的渡轮:{f['operator_names'].replace(', ', '、')}。船程 {min(minutes)}-{max(minutes)} 分钟,首班 {f['firsts'][0]},末班 {f['lasts'][-1]};回程末班、票价和附近去处。",
        alternates["zh"],
        body,
        root=root,
        crumbs=[("一日游", SITE + "zh/day-trip/"), (f"{terminal} 码头", SITE + alternates["zh"])],
        lang="zh",
        alternates=alternates,
    )


BUDGET_ITEMS = (
    ("Grab, terminal to Nagoya and back", "Grab:码头往返 Nagoya", "grab-bc-nagoya", 2),
    ("Local lunch", "本地午餐", "local-meal", 1),
    ("Full-body massage", "全身按摩", "massage", 1),
    ("Seafood dinner", "海鲜晚餐", "seafood", 1),
)


def day_trip_budget(data):
    """Example-day lines (en label, zh label, low, high, source), rounded per line so the shown lines add up to the total."""
    rate = data["rules"]["fx_mid_market_sgd_idr"]
    prices = {p["id"]: p for p in data["prices"]}
    cheapest = min((f for f in data["ferries"] if f.get("return_all_in_sgd")), key=lambda f: f["return_all_in_sgd"])
    lines = [(
        "Ferry, return all-in (cheapest listed)",
        "渡轮来回含税费(所列最便宜)",
        cheapest["return_all_in_sgd"],
        cheapest["return_all_in_sgd"],
        cheapest["source"],
    )]
    for label_en, label_zh, price_id, times in BUDGET_ITEMS:
        if price_id in prices:
            p = prices[price_id]
            per_sgd = 1 if p["currency"] == "SGD" else rate
            lines.append((label_en, label_zh, p["low"] * times / per_sgd, p["high"] * times / per_sgd, p["source"]))
    return cheapest, [(en, zh, round(low), round(high), source) for en, zh, low, high, source in lines]


def day_trip_pages(data, partners, areas):
    alternates = {"en": "day-trip/", "zh": zh_path("day-trip/")}
    return {alternates[lang]: day_trip_page(data, partners, areas, lang, alternates) for lang in ("en", "zh")}


def day_trip_page(data, partners, areas, lang="en", alternates=None):
    zh = lang == "zh"
    rate = data["rules"]["fx_mid_market_sgd_idr"]
    ferries = data["ferries"]
    minutes = [int(n) for f in ferries for n in f["minutes"].split("-")]
    firsts = sorted(f["first_last_from_sg"].split(" / ")[0] for f in ferries)
    lasts = sorted(f["first_last_from_sg"].split(" / ")[1] for f in ferries)
    fastest = min(ferries, key=lambda f: int(f["minutes"].split("-")[0]))
    cheapest, budget_lines = day_trip_budget(data)
    total_low = sum(line[2] for line in budget_lines)
    total_high = sum(line[3] for line in budget_lines)
    total_text = f"S${total_low:,.0f} – {total_high:,.0f}"
    budget_rows = "".join(
        f"<tr><td>{esc(label_zh if zh else label_en)}<br><span class=\"meta\">{source_link(source)}</span></td>"
        f"<td class=\"num\">S${low}{'' if low == high else f' – {high}'}</td></tr>"
        for label_en, label_zh, low, high, source in budget_lines
    )
    list_sep = "、" if zh else ", "

    def near(t):
        cats = sorted({category_word(p["category"], lang) for p in areas.get(TERMINAL_AREA.get(t, t), [])})
        if not cats:
            return ""
        return f"<br><span class=\"meta\">{'附近:' if zh else 'near: '}{list_sep.join(cats)}</span>"

    terminal_rows = "".join(
        f"<tr><td><a href=\"../terminal/{slug(t)}/\">{esc(t)}</a>{near(t)}</td><td>{esc(list_sep.join(f['operator'] for f in fs))}</td></tr>"
        for t, fs in terminals(data).items()
    )
    rules = data["rules"]
    if zh:
        entry = "".join(f"<li>{esc(localized(e, 'en', lang))}<span class=\"meta\">({source_link(e['source'])})</span></li>" for e in rules["entry"])
        tips = "".join(f"<li>{esc(localized(t, 'en', lang))}<span class=\"meta\">({source_link(t['source'])})</span></li>" for t in rules["money_tips"][:3])
    else:
        entry = "".join(f"<li>{esc(e['en'])} <span class=\"meta\">({source_link(e['source'])})</span></li>" for e in rules["entry"])
        tips = "".join(f"<li>{esc(t['en'])} <span class=\"meta\">({source_link(t['source'])})</span></li>" for t in rules["money_tips"][:3])
    root = "../../" if zh else "../"
    terminal_areas = {TERMINAL_AREA.get(t, t): t for t in terminals(data)}
    here = (lambda t: f" 码头在此区") if zh else (lambda t: " ferry terminal here")
    area_items = "".join(
        f"<li><a href=\"{root}area/{slug(a)}/\">{esc(a)}</a>"
        + (f" <span class=\"meta\">· {esc(terminal_areas[a])}{here(a)}</span>" if a in terminal_areas else "")
        + f"<br><span class=\"meta\">{list_sep.join(sorted({category_word(p['category'], lang) for p in ps}))}</span></li>"
        for a, ps in sorted(areas.items())
    )
    queue = rules.get("queue_warning", {})
    entry_rules = rules["entry"]
    rf = data.get("return_ferries", {})
    daily_last = [r for r in rf.get("last", []) if not r.get("days")]
    latest_back = max(daily_last, key=lambda r: r["time"]) if daily_last else None
    if not latest_back:
        latest_text = ""
    elif zh:
        latest_text = f";回程末班 <strong>{latest_back['time']}</strong> 巴淡时间,从 {esc(latest_back['from'])} 出发"
    else:
        latest_text = f"; last ferry back <strong>{latest_back['time']}</strong> Batam time from {esc(latest_back['from'])}"
    return_rows = []
    for t in terminals(data):
        rows = last_back(data, t)
        daily = [r for r in rows if not r.get("days")]
        if daily:
            joiner = "往" if zh else "to"
            cell = f"<strong>{daily[0]['time']}</strong> {esc(daily[0]['operator'])} {joiner} {esc(daily[0]['to'])}"
        elif rows:
            cell = f"没有每日班次;{esc(last_back_text(rows[0], lang))}" if zh else f"No daily sailing; {esc(last_back_text(rows[0]))}"
        else:
            cell = "请向船公司查询" if zh else "Check with the operator"
        return_rows.append(f"<tr><td><a href=\"../terminal/{slug(t)}/\">{esc(t)}</a></td><td>{cell}</td></tr>")
    fare_sources = ' · '.join(source_link(s) for s in sorted({f['source'] for f in ferries}))
    charter = partners['charter']['mpv_sgd']
    if not zh:
        body = f"""<h1>Batam day trip from Singapore: ferry, cost, rules and what to do</h1>
<div class="card"><table>
<tr><td>How</td><td>Ferry from HarbourFront or Tanah Merah to one of {len(terminals(data))} Batam terminals</td></tr>
<tr><td>How long</td><td><strong>{min(minutes)} – {max(minutes)} min</strong> each way ({esc(fastest['operator'])} to {esc(', '.join(fastest['batam']))} is quickest); from Singapore between <strong>{firsts[0]}</strong> and <strong>{lasts[-1]}</strong> (varies by terminal){latest_text}</td></tr>
<tr><td>How much</td><td><strong>{total_text}</strong> per person for an example day, ferry from <strong>S${cheapest['return_all_in_sgd']}</strong></td></tr>
<tr><td>Watch out</td><td><ul class="list"><li>{esc(rules['timezone_note'])}</li><li>{esc(entry_rules[2]['en'])}</li><li>{esc(entry_rules[3]['en'])}</li><li>{esc(queue.get('en', ''))}</li></ul></td></tr>
</table>
<p class="meta">Sources: ferry times {source_link(data['routes']['source'])}; fares {fare_sources}; return times {source_link(rf['source'])}; rate {source_link(rules['fx_source'])}; queue {source_link(queue['source'])}. As of {as_of(data)}, not checked in person.</p>
<a class="btn" href="{esc(booking_url(partners))}" rel="nofollow noopener sponsored">Compare and book ferry tickets</a><a class="btn ghost" href="../#plan">Plan my day</a></div>
<div class="card" id="before"><h2>1. Before you go</h2><ul class="list">{entry}</ul><a class="btn" href="../#check">Open the checklist</a></div>
<div class="card"><h2>2. Pick a ferry and terminal</h2><table><tr><th>Batam terminal</th><th>Operators</th></tr>{terminal_rows}</table>
<a class="btn" href="../ferry/">Compare fares and times</a></div>
<div class="card"><h2>3. What a day costs</h2><p>Example day per person at S$1 = {idr(rate)} (mid-market, {fmt_date(rules['fx_date'])}, {source_link(rules['fx_source'])}).</p>
<table><tr><th>Item</th><th class="num">SGD</th></tr>{budget_rows}<tr><td><strong>Total</strong></td><td class="num"><strong>{total_text}</strong></td></tr></table>
<p class="meta">Ranges from published guides, not checked in person. A car with driver for the day is S${charter[0]} – {charter[1]} per car instead of Grab (drivers' own published prices, <a href=\"../driver-prices/\">checked weekly</a>).</p>
<a class="btn" href="../#price">Check a quote in the app</a></div>
<div class="card"><h2>4. Money</h2><ul class="list">{tips}</ul><a class="btn" href="../#money">Open the currency converter</a></div>
<div class="card"><h2>5. Where to go</h2><ul class="list">{area_items}</ul><a class="btn" href="../places/">See places by area</a><a class="btn ghost" href="../driver-prices/">WhatsApp a driver for the day</a></div>
<div class="card"><h2>6. Getting home</h2>
<table><tr><th>From</th><th>Last daily ferry back (Batam time)</th></tr>{''.join(return_rows)}</table>
<p class="meta">{esc(rf.get('note_en', ''))} Source for both: {source_link(rf['source'])}, as of {fmt_date(rf['as_of'])}; check on the day.</p>
<ul class="list">
<li>{esc(queue.get('en', ''))} <span class="meta">({source_link(queue['source'])})</span></li>
<li>SG Arrival Card and duty-free limits: see <a href="#before">Before you go</a>.</li></ul>
<p>The planner counts back from your return ferry and tells you when to leave, with a queue buffer.</p>
<a class="btn" href="../#plan">Plan my day around the return ferry</a></div>"""
        return page(
            "Batam day trip from Singapore: ferry, cost, entry rules, what to do",
            f"Plan a Batam day trip from Singapore: {min(minutes)}-{max(minutes)} min ferry from {firsts[0]}, an example day at S${total_low:,.0f}-{total_high:,.0f} per person, entry rules, money and places by area.",
            "day-trip/",
            body,
            crumbs=[("Batam day trip", SITE + "day-trip/")],
            alternates=alternates,
        )

    app = f"{root}?lang=zh"
    body = f"""<h1>新加坡去巴淡一日游:渡轮、花费、入境规定和去哪里</h1>
<div class="card"><table class="facts">
<tr><td>怎么去</td><td>从 HarbourFront 或 Tanah Merah 坐渡轮,到巴淡 {len(terminals(data))} 个码头之一</td></tr>
<tr><td>多久</td><td>单程 <strong>{min(minutes)} – {max(minutes)} 分钟</strong>(最快:{esc(fastest['operator'])} 往 {esc('、'.join(fastest['batam']))});新加坡出发时间在 <strong>{firsts[0]}</strong> 至 <strong>{lasts[-1]}</strong> 之间(各码头不同){latest_text}</td></tr>
<tr><td>多少钱</td><td>示例一日每人 <strong>{total_text}</strong>,渡轮 <strong>S${cheapest['return_all_in_sgd']}</strong> 起</td></tr>
<tr><td>注意</td><td><ul class="list"><li>{esc(rules['timezone_note_zh'])}</li><li>{esc(localized(entry_rules[2], 'en', lang))}</li><li>{esc(localized(entry_rules[3], 'en', lang))}</li><li>{esc(localized(queue, 'en', lang))}</li></ul></td></tr>
</table>
<p class="meta">来源:船班 {source_link(data['routes']['source'])};票价 {fare_sources};回程时间 {source_link(rf['source'])};汇率 {source_link(rules['fx_source'])};排队 {source_link(queue['source'])}。截至 {as_of(data, 'zh')},未实地核实。</p>
<a class="btn" href="{esc(booking_url(partners))}" rel="nofollow noopener sponsored">比较并预订船票</a><a class="btn ghost" href="{app}#plan">规划我的一天</a></div>
<div class="card" id="before"><h2>1. 出发前</h2><ul class="list">{entry}</ul><a class="btn" href="{app}#check">打开出行清单</a></div>
<div class="card"><h2>2. 选渡轮和码头</h2><table><tr><th>巴淡码头</th><th>船公司</th></tr>{terminal_rows}</table>
<a class="btn" href="{root}ferry/">比较票价和班次(英文页)</a></div>
<div class="card"><h2>3. 一天花多少钱</h2><p>示例一日每人花费,按 S$1 = {idr(rate)} 换算(市场中间价,{fmt_date(rules['fx_date'], 'zh')},{source_link(rules['fx_source'])})。</p>
<table><tr><th>项目</th><th class="num">新币</th></tr>{budget_rows}<tr><td><strong>合计</strong></td><td class="num"><strong>{total_text}</strong></td></tr></table>
<p class="meta">价格区间来自公开指南,未实地核实。不坐 Grab 的话,包车连司机一天每车 S${charter[0]} – {charter[1]}(司机自己公布的价格,<a href=\"{root}driver-prices/\">每周核查</a>)。</p>
<a class="btn" href="{app}#price">在应用里核对报价</a></div>
<div class="card"><h2>4. 换钱</h2><ul class="list">{tips}</ul><a class="btn" href="{app}#money">打开汇率换算</a></div>
<div class="card"><h2>5. 去哪里</h2><ul class="list">{area_items}</ul><a class="btn" href="{root}places/">按地区看地点(英文页)</a><a class="btn ghost" href="{root}driver-prices/">WhatsApp 包车司机</a></div>
<div class="card"><h2>6. 回程</h2>
<table><tr><th>出发码头</th><th>每日回程末班(巴淡时间)</th></tr>{''.join(return_rows)}</table>
<p class="meta">{esc(rf.get('note_zh', ''))}两项来源:{source_link(rf['source'])},截至 {fmt_date(rf['as_of'], 'zh')};出发当天请再核实。</p>
<ul class="list">
<li>{esc(localized(queue, 'en', lang))}<span class="meta">({source_link(queue['source'])})</span></li>
<li>SG Arrival Card 和免税额:见<a href="#before">出发前</a>。</li></ul>
<p>行程规划会从你的回程船班倒推,告诉你几点该动身,并预留排队时间。</p>
<a class="btn" href="{app}#plan">按回程船班规划我的一天</a></div>"""
    return page(
        "新加坡去巴淡一日游:渡轮、花费、入境规定、去哪里",
        f"新加坡去巴淡一日游攻略:渡轮 {min(minutes)}-{max(minutes)} 分钟,{firsts[0]} 起有船;示例一日每人 S${total_low:,.0f}-{total_high:,.0f};入境规定、换钱和各区去处。",
        alternates["zh"],
        body,
        root=root,
        crumbs=[("一日游", SITE + alternates["zh"])],
        lang="zh",
        alternates=alternates,
    )


def main():
    data = load_js_object(ROOT / "data.js", "window.BUS_DATA")
    photos = load_js_object(ROOT / "photos.js", "window.BUS_PHOTOS")
    place_photos = load_js_object(ROOT / "photos.js", "window.BUS_PLACE_PHOTOS")
    partners = json.loads((ROOT / "partners.json").read_text(encoding="utf-8"))

    pages = {
        "prices/": prices_page(data, partners),
        "entry-rules/": entry_page(data),
        "money/": money_page(data),
    }
    areas, area_html = area_pages(data, photos, place_photos)
    pages["places/"] = places_index(areas)
    pages.update(area_html)
    pages.update(day_trip_pages(data, partners, areas))
    pages.update(terminal_pages(data, photos, place_photos, partners))
    for path, content in pages.items():
        write_if_changed(ROOT / path / "index.html", content)

    all_paths = ["", "driver-prices/", "ferry/"] + list(pages)
    today = partners.get("updated", datetime.date.today().isoformat())
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{SITE}{p}</loc><lastmod>{today}</lastmod></url>\n" for p in all_paths
    ) + "</urlset>\n"
    write_if_changed(ROOT / "sitemap.xml", sitemap)
    write_if_changed(ROOT / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
    llms = [
        "# Batam Uncle Says",
        "",
        "> Free mobile web app for Singapore residents planning a Batam day trip: ferry-timed day planner, price checker in SGD and rupiah, entry rules for both directions, Indonesian phrase cards, and direct WhatsApp contact with Batam drivers who publish their prices. Works offline. Facts are sourced; places are not yet visited in person.",
        "",
        "## Pages",
        f"- [Trip planner app]({SITE}): plan a day around ferry times, leave-by countdown",
        f"- [Batam day trip guide]({SITE}day-trip/): ferry, example day cost, entry rules, where to go",
        f"- [Batam driver prices]({SITE}driver-prices/): drivers with published prices and WhatsApp, re-checked weekly",
        f"- [Singapore to Batam ferry]({SITE}ferry/): operators, all-in return fares, terminals",
        f"- [Batam prices]({SITE}prices/): massage, seafood, Grab, meals, hotels in SGD and rupiah",
        f"- [Entry rules]({SITE}entry-rules/): passport, arrival cards, duty-free",
        f"- [Money]({SITE}money/): exchange rate, money changers, QRIS",
        f"- [Places by area]({SITE}places/)",
    ] + [f"- [{area}]({SITE}area/{slug(area)}/)" for area in sorted(areas)] + [
        f"- [{t} ferry terminal]({SITE}terminal/{slug(t)}/)" for t in terminals(data)
    ] + [
        "",
        "## 中文 (Chinese)",
        f"- [新加坡去巴淡一日游]({SITE}zh/day-trip/): 渡轮、示例一日花费、入境规定、去哪里",
    ] + [
        f"- [巴淡 {t} 码头]({SITE}zh/terminal/{slug(t)}/)" for t in terminals(data)
    ]
    write_if_changed(ROOT / "llms.txt", "\n".join(llms) + "\n")
    print(f"pages: {len(all_paths)}")


if __name__ == "__main__":
    main()
