"""Shared HTML template for the static search pages (driver prices, ferry, prices, entry rules, money, places)."""
import html
import json
from urllib.parse import quote

SITE = "https://juw12.github.io/batam-uncle-says/"
OG_IMAGE = SITE + "img/hero-barelang.jpg"

NAV = [
    ("driver-prices/", "Drivers"),
    ("ferry/", "Ferry"),
    ("prices/", "Prices"),
    ("entry-rules/", "Entry rules"),
    ("money/", "Money"),
    ("places/", "Places"),
]


def esc(value):
    return html.escape(str(value), quote=True)


def page(title, description, path, body, root="../", crumbs=None):
    """Render a static page. path is relative to SITE (e.g. 'prices/'); root is the relative way back to SITE."""
    canonical = SITE + path
    share_text = quote(f"{title}\n{canonical}")
    nav = "".join(
        f'<a href="{root}{href}"{" aria-current=\"page\"" if href == path else ""}>{label}</a>' for href, label in NAV
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
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
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
<header><a class="brand" href="{root}">Batam Uncle Says</a><nav aria-label="Guides">{nav}</nav></header>
<main>
{body}
<p><a class="btn ghost" href="https://wa.me/?text={share_text}" rel="nofollow noopener">Share on WhatsApp</a><a class="btn ghost" href="{root}">Open the trip planner</a></p>
</main>
<footer>Independent guide for day trips from Singapore. Not affiliated with any operator or venue listed. Prices and rules change; confirm with the operator before you travel.</footer>
</body>
</html>
"""
