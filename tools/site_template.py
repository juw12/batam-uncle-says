"""Shared HTML template for the static search pages (driver prices, ferry, prices, entry rules, money, places)."""
import html
import json
from urllib.parse import quote

SITE = "https://juw12.github.io/batam-uncle-says/"
OG_IMAGE = SITE + "img/hero-barelang.jpg"


def tip_links():
    """The owner's payment links from partners.json: https only, allowed hosts only, max 3."""
    from pathlib import Path
    from urllib.parse import urlparse
    try:
        money = json.loads((Path(__file__).resolve().parents[1] / "partners.json").read_text(encoding="utf-8")).get("money", {})
    except Exception:
        return []
    hosts = money.get("allowed_hosts", [])
    found = []
    for link in money.get("links", []) + [{"label": "", "url": money.get("tip_url", "")}]:
        url = link.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.hostname in hosts and url not in [u for _, u in found]:
            found.append((link.get("label") or parsed.hostname.replace("www.", ""), url))
    return found[:3]

NAV = [
    ("day-trip/", "Day trip"),
    ("driver-prices/", "Drivers"),
    ("ferry/", "Ferry"),
    ("prices/", "Prices"),
    ("entry-rules/", "Entry rules"),
    ("money/", "Money"),
    ("places/", "Places"),
]
NAV_ZH = [
    ("zh/day-trip/", "一日游"),
    ("zh/driver-prices/", "司机"),
    ("zh/ferry/", "渡轮"),
    ("zh/prices/", "价格"),
    ("zh/entry-rules/", "入境规定"),
    ("zh/money/", "换钱"),
    ("zh/places/", "去哪里"),
]
UI = {
    "en": {
        "html_lang": "en",
        "og_locale": "en_SG",
        "share": "Share on WhatsApp",
        "planner": "Open the trip planner",
        "planner_query": "",
        "support_one": "Support Batam Uncle Says",
        "support_via": "Support via ",
        "switch": "English",
        "footer": "Independent guide for day trips from Singapore. Not affiliated with any operator or venue listed. Prices and rules change; confirm with the operator before you travel.",
    },
    "zh": {
        "html_lang": "zh-Hans",
        "og_locale": "zh_SG",
        "share": "分享到 WhatsApp",
        "planner": "打开行程规划",
        "planner_query": "?lang=zh",
        "support_one": "支持 Batam Uncle Says",
        "support_via": "支持:",
        "switch": "中文",
        "footer": "面向新加坡一日游旅客的独立指南,与任何渡轮公司、场所无关联。价格和规定会变,出行前请向运营方核实。",
    },
}
HREFLANG = {"en": "en", "zh": "zh-Hans"}


def esc(value):
    return html.escape(str(value), quote=True)


def page(title, description, path, body, root="../", crumbs=None, lang="en", alternates=None):
    """Render a static page. path is relative to SITE (e.g. 'prices/'); root is the relative way back to SITE.

    lang is "en" or "zh". alternates maps each language to its path for the same page (hreflang links and the
    language switch); pass it on every language version of a page.
    """
    ui = UI[lang]
    canonical = SITE + path
    links = tip_links()
    support = "".join(
        f'<a class="btn" href="{esc(url)}" rel="noopener">{esc(ui["support_one"] if len(links) == 1 else ui["support_via"] + label)}</a>'
        for label, url in links
    )
    share_text = quote(f"{title}\n{canonical}")
    nav = "".join(
        f'<a href="{root}{href}"{" aria-current=\"page\"" if href == path else ""}>{label}</a>'
        for href, label in (NAV_ZH if lang == "zh" else NAV)
    )
    hreflang = ""
    switch = ""
    if alternates:
        hreflang = "".join(
            f'\n<link rel="alternate" hreflang="{HREFLANG[code]}" href="{SITE}{alt_path}">' for code, alt_path in alternates.items()
        ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE}{alternates["en"]}">'
        switch = "".join(
            f'<a class="lang" href="{root}{alt_path}" hreflang="{HREFLANG[code]}" lang="{HREFLANG[code]}">{UI[code]["switch"]}</a>'
            for code, alt_path in alternates.items()
            if code != lang
        )
    crumb_items = [("Batam Uncle Says", SITE)] + (crumbs or [(title, canonical)])
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url} for i, (name, url) in enumerate(crumb_items)
        ],
    }
    return f"""<!doctype html>
<html lang="{ui['html_lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">{hreflang}
<meta property="og:type" content="article">
<meta property="og:locale" content="{ui['og_locale']}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{OG_IMAGE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b2a40">
<link rel="icon" href="{root}icons/icon-192.png">
<script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>
<style>
  @font-face {{ font-family: Inter; src: url({root}fonts/inter-latin.woff2) format("woff2"); font-weight: 100 900; font-display: swap; }}
  :root {{ --ink: #14212b; --ink-2: #3d4b56; --ink-3: #66737d; --line: #e3e7ea; --bg: #f5f6f7; --accent: #0b5d7a; --deep: #0b2a40; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: Inter, system-ui, sans-serif; color: var(--ink); background: var(--bg); line-height: 1.55; }}
  html[lang^=zh] body {{ font-family: Inter, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", system-ui, sans-serif; line-height: 1.7; }}
  header .top {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
  header .lang {{ color: #fff; text-decoration: none; font-size: 14px; border: 1px solid #44617a; border-radius: 8px; padding: 3px 10px; }}
  header {{ background: var(--deep); color: #fff; padding: 12px 18px 0; }}
  header .brand {{ color: #fff; text-decoration: none; font-weight: 600; font-size: 16px; }}
  header nav {{ display: flex; gap: 16px; overflow-x: auto; padding: 10px 0 12px; scrollbar-width: none; }}
  header nav a {{ color: #c9d6df; text-decoration: none; font-size: 14px; white-space: nowrap; }}
  header nav a[aria-current] {{ color: #fff; font-weight: 600; }}
  main {{ max-width: 760px; margin: 0 auto; padding: 22px 18px 40px; }}
  h1 {{ font-size: 28px; line-height: 1.2; margin: 6px 0 10px; letter-spacing: -0.01em; }}
  h2 {{ font-size: 19px; margin: 0 0 8px; }}
  .lede {{ color: var(--ink-2); font-size: 16px; margin: 0 0 18px; }}
  .card {{ background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 18px; margin-bottom: 12px; }}
  .card img {{ width: 100%; height: auto; border-radius: 10px; display: block; margin-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14.5px; }}
  td, th {{ text-align: left; padding: 9px 0; border-bottom: 1px solid var(--line); vertical-align: top; }}
  td.num, th.num {{ text-align: right; white-space: nowrap; font-weight: 600; padding-left: 10px; }}
  tr:last-child td {{ border-bottom: 0; }}
  table.facts td:first-child {{ white-space: nowrap; padding-right: 14px; }}
  ul.list {{ margin: 0; padding-left: 20px; }}
  ul.list li {{ margin: 8px 0; }}
  .meta {{ font-size: 13px; color: var(--ink-3); }}
  .btn {{ display: inline-block; margin: 10px 10px 0 0; padding: 10px 16px; border-radius: 10px; background: var(--accent); color: #fff; text-decoration: none; font-weight: 600; font-size: 14.5px; }}
  .btn.ghost {{ background: #fff; color: var(--accent); border: 1px solid #c9d2d8; }}
  a {{ color: var(--accent); }}
  footer {{ max-width: 760px; margin: 0 auto; padding: 0 18px 40px; font-size: 13px; color: var(--ink-3); }}
</style>
</head>
<body>
<header><div class="top"><a class="brand" href="{root}{ui['planner_query']}">Batam Uncle Says</a>{switch}</div><nav aria-label="Guides">{nav}</nav></header>
<main>
{body}
<p><a class="btn ghost" href="https://wa.me/?text={share_text}" rel="nofollow noopener">{ui['share']}</a><a class="btn ghost" href="{root}{ui['planner_query']}">{ui['planner']}</a>{support}</p>
</main>
<footer>{ui['footer']}</footer>
</body>
</html>
"""
