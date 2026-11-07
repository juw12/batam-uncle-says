"""Build files that depend on partners.json and data.js (runs in GitHub Actions after partners_check.py).

Writes: partners.js (read by the app), driver-prices/ and ferry/ pages in English and Chinese (zh/). Bumps the service worker VERSION when
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


def page(title, description, canonical, body, **options):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from site_template import page as template_page
    return template_page(title, description, canonical.replace(SITE, ""), body, **options)


def zh_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.year}年{d.month}月{d.day}日"


def both(path):
    return {"en": path, "zh": "zh/" + path}


def operator_message():
    return "Hi, I found you on Batam Uncle Says. I would like a quote for a Batam day trip. Date: , People: , Ferry arrival time: "


def driver_page(partners, lang="en"):
    zh = lang == "zh"
    active = [op for op in partners["operators"] if op["status"] == "active"]
    cards = []
    for op in active:
        rows = "".join(
            f"<tr><td>{esc(p['label'])}</td><td class=\"num\">S${p['sgd']}</td></tr>" for p in op["prices"]
        ) or ("<tr><td>当前价格请看其网站</td><td></td></tr>" if zh else "<tr><td>See their website for current prices</td><td></td></tr>")
        if zh:
            lang_names = {"English": "英语", "Chinese": "华语"}
            langs = f" · 语言:{esc('、'.join(lang_names.get(x, x) for x in op['languages']))}" if op.get("languages") else ""
            cards.append(f"""<div class="card">
  <h2>{esc(op['name'])}</h2>
  <table>{rows}</table>
  <p class="meta"><span lang="en">{esc(op['price_note'])}</span>{langs}。{zh_date(op['checked'])}核查。车型和价格说明为运营方网站原文。</p>
  <a class="btn" href="https://wa.me/{op['whatsapp']}?text={quote(operator_message())}" rel="nofollow noopener">WhatsApp 联系</a><a class="btn ghost" href="{esc(op['website'])}" rel="nofollow noopener">他们的网站</a>
</div>""")
            continue
        langs = f" · Languages: {esc(', '.join(op['languages']))}" if op.get("languages") else ""
        wa = f"https://wa.me/{op['whatsapp']}?text={quote(operator_message())}"
        cards.append(f"""<div class="card">
  <h2>{esc(op['name'])}</h2>
  <table>{rows}</table>
  <p class="meta">{esc(op['price_note'])}{langs}. Checked {fmt_date(op['checked'])}.</p>
  <a class="btn" href="{wa}" rel="nofollow noopener">Message on WhatsApp</a><a class="btn ghost" href="{esc(op['website'])}" rel="nofollow noopener">Their website</a>
</div>""")
    charter = partners["charter"]
    if zh:
        body = f"""<h1>巴淡包车司机价格(新加坡出发)</h1>
<p class="lede">巴淡包一辆车连英语司机一整天,MPV 通常 S${charter['mpv_sgd'][0]}–{charter['mpv_sgd'][1]},面包车 S${charter['van_sgd'][0]}–{charter['van_sgd'][1]},依据巴淡运营方公布的价格。以下司机在自己网站上公布价格和 WhatsApp 号码,每周重新核查。</p>
{''.join(cards)}
<div class="card">
  <h2>按船班规划一天</h2>
  <p>Batam Uncle Says 会根据你的船班时间排出行程,并填进发给司机的 WhatsApp 讯息里。</p>
  <a class="btn" href="../../?lang=zh#guide">在应用里打开司机页面</a><a class="btn ghost" href="../../?lang=zh#plan">规划我的一天</a>
</div>
<p class="meta">巴淡持牌导游持有市旅游局发的导游证(KTPP)(<a href="{esc(partners['licence_source'])}" rel="nofollow noopener">规定</a>)。预订导游时可要求出示。页面更新于 {zh_date(partners['updated'])}。</p>"""
        return page(
            "巴淡包车司机价格(新加坡出发,每周核查)",
            f"巴淡全天包车连英语司机 S${charter['mpv_sgd'][0]} 起。巴淡司机自己公布的价格和 WhatsApp 联系方式,每周重新核查。",
            SITE + "zh/driver-prices/",
            body,
            root="../../",
            crumbs=[("司机", SITE + "zh/driver-prices/")],
            lang="zh",
            alternates=both("driver-prices/"),
        )
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
        alternates=both("driver-prices/"),
    )


def ferry_page(data, partners, lang="en"):
    zh = lang == "zh"
    rows = []
    for f in data["ferries"]:
        fare = f"S${f['return_all_in_sgd']}" if f.get("return_all_in_sgd") else ("见备注" if zh else "See note")
        note_text = (f.get("fare_note_zh") or f.get("fare_note")) if zh else f.get("fare_note")
        note = f" · {esc(note_text)}" if not f.get("return_all_in_sgd") and note_text else ""
        if zh:
            rows.append(
                f"<tr><td><a href=\"{esc(f['url'])}\" rel=\"nofollow noopener\">{esc(f['operator'])}</a><br>"
                f"<span class=\"meta\">{esc(' / '.join(f['sg']))} 往 {esc('、'.join(f['batam']))} · {esc(f['minutes'])} 分钟 · 新加坡首/末班 {esc(f['first_last_from_sg'])}{note}</span></td>"
                f"<td class=\"num\">{fare}</td></tr>"
            )
            continue
        rows.append(
            f"<tr><td><a href=\"{esc(f['url'])}\" rel=\"nofollow noopener\">{esc(f['operator'])}</a><br>"
            f"<span class=\"meta\">{esc(' / '.join(f['sg']))} to {esc(', '.join(f['batam']))} · {esc(f['minutes'])} min · first/last from SG {esc(f['first_last_from_sg'])}{note}</span></td>"
            f"<td class=\"num\">{fare}</td></tr>"
        )
    terminal_names = []
    for f in data["ferries"]:
        for t in f["batam"]:
            if t not in terminal_names:
                terminal_names.append(t)
    terminal_links = "".join(
        f'<li><a href="../terminal/{re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")}/">{esc(t)}</a></li>' for t in terminal_names
    )
    booking = partners["ferry_booking"]["easybook"] + partners["affiliates"].get("easybook_query", "")
    sources = sorted({f["source"] for f in data["ferries"]})
    source_links = ' · '.join(f'<a href="{esc(s)}" rel="nofollow noopener">{esc(s.split("/")[2])}</a>' for s in sources)
    if zh:
        body = f"""<h1>新加坡往巴淡渡轮:船公司、票价和码头</h1>
<p class="lede">渡轮从 HarbourFront 和 Tanah Merah 出发,船程约 50 至 70 分钟。下表来回票价在船公司有公布时为含税费价格。</p>
<div class="card"><table><tr><th>船公司和航线</th><th class="num">来回含税费</th></tr>{''.join(rows)}</table>
<p class="meta">票价来自公开资料,未在柜台核实。请在船公司官网确认。来源:{source_links}</p>
<a class="btn" href="{esc(booking)}" rel="nofollow noopener sponsored">网上比较并预订船票</a></div>
<div class="card"><h2>巴淡码头</h2><ul class="list">{terminal_links}</ul><a class="btn ghost" href="../day-trip/">一日游攻略</a></div>
<div class="card">
  <h2>按船班规划一天</h2>
  <p>输入去程和回程船班时间,得到带“几点该动身”倒计时的行程,还有价格核对和入境规定。可离线使用。</p>
  <a class="btn" href="../../?lang=zh#plan">规划我的一天</a><a class="btn ghost" href="../../?lang=zh#ferry">在应用里看渡轮</a>
</div>"""
        return page(
            "新加坡往巴淡渡轮:船公司、票价和码头",
            "比较新加坡往巴淡的渡轮:BatamFast、Majestic、Sindo 等。含税费来回票价、码头、首末班船和一日游规划。",
            SITE + "zh/ferry/",
            body,
            root="../../",
            crumbs=[("渡轮", SITE + "zh/ferry/")],
            lang="zh",
            alternates=both("ferry/"),
        )
    body = f"""<h1>Singapore to Batam ferry: operators, fares and terminals</h1>
<p class="lede">Ferries leave from HarbourFront and Tanah Merah and take about 50 to 70 minutes. Return fares below are all-in where the operator lists them.</p>
<div class="card"><table><tr><th>Operator and route</th><th class="num">Return, all-in</th></tr>{''.join(rows)}</table>
<p class="meta">Fares from published sources, not checked at the counter. Confirm on the operator's site. Sources: {source_links}</p>
<a class="btn" href="{esc(booking)}" rel="nofollow noopener sponsored">Compare and book tickets online</a></div>
<div class="card"><h2>Batam terminals</h2><ul class="list">{terminal_links}</ul><a class="btn ghost" href="../day-trip/">Day trip guide</a></div>
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
        alternates=both("ferry/"),
    )


def main():
    partners = json.loads((ROOT / "partners.json").read_text(encoding="utf-8"))
    data = load_data_js()
    js = "/* Generated from partners.json by tools/partners_build.py. Edit the JSON, not this file. */\nwindow.BUS_PARTNERS = " + json.dumps(partners, ensure_ascii=False, indent=1) + ";\n"
    js_changed = write_if_changed(ROOT / "partners.js", js)
    write_if_changed(ROOT / "driver-prices" / "index.html", driver_page(partners))
    write_if_changed(ROOT / "ferry" / "index.html", ferry_page(data, partners))
    write_if_changed(ROOT / "zh" / "driver-prices" / "index.html", driver_page(partners, "zh"))
    write_if_changed(ROOT / "zh" / "ferry" / "index.html", ferry_page(data, partners, "zh"))
    # sitemap.xml, robots.txt and llms.txt are written by tools/seo_build.py
    if js_changed:
        sw_path = ROOT / "sw.js"
        sw = sw_path.read_text(encoding="utf-8")
        sw = re.sub(r'const VERSION = "([^"]+)";', f'const VERSION = "bus-{datetime.date.today().isoformat()}-p{datetime.datetime.now().strftime("%H%M")}";', sw, count=1)
        sw_path.write_text(sw, encoding="utf-8", newline="\n")
        print("bumped sw.js VERSION")


if __name__ == "__main__":
    main()
