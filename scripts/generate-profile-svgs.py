#!/usr/bin/env python3
"""
generate-profile-svgs.py
========================
Regenerates the animated, self-contained profile SVGs from GitHub's own public
data (no third-party services):

  assets/telemetry-stats.svg      — HUD stat panel (repos, stars, followers, langs)
  assets/contribution-matrix.svg  — animated contribution grid (last 53 weeks)

Usage:
  python3 scripts/generate-profile-svgs.py [username] [year]

Set GITHUB_TOKEN in the environment for a higher API rate limit (recommended
when run from GitHub Actions).
"""

import json
import os
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

USER = sys.argv[1] if len(sys.argv) > 1 else "Ezra5566"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

UA = "Mozilla/5.0 (compatible; profile-svg-generator/1.0)"


def http_get(url, headers=None, timeout=40):
    h = {"User-Agent": UA}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_user():
    return json.loads(http_get(f"https://api.github.com/users/{USER}"))


def fetch_repos():
    repos = []
    page = 1
    while True:
        batch = json.loads(
            http_get(
                f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&sort=updated"
            )
        )
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_contributions():
    html = http_get(f"https://github.com/users/{USER}/contributions", {"Accept": "text/html"})
    found = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="([0-4])"'
        r'|data-level="([0-4])"[^>]*data-date="(\d{4}-\d{2}-\d{2})"',
        html,
    )
    cells = {}
    for a, b, c, d in found:
        if a:
            cells[a] = int(b)
        else:
            cells[d] = int(c)
    m = re.search(r"(\d[\d,]*)\s+contributions\s+in the last year", html)
    total = int(m.group(1).replace(",", "")) if m else sum(cells.values())
    return cells, total


# ── helpers ──────────────────────────────────────────────────────────────

PURPLE = "#8b5cf6"
GRAY = "#6d7388"
LIGHT = "#9aa0b4"
WHITE = "#f4f4f8"
DIM = "#4b4b5e"
BG = "#0a0a12"
PANEL_BORDER = "#1d1d2b"
MONO = "ui-monospace,Menlo,Consolas,monospace"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def header_lines(title, width):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="340" viewBox="0 0 {width} 340" role="img" aria-label="{esc(title)}">',
        f"  <defs>",
        f'    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">',
        f'      <stop offset="0%" stop-color="#4c2e9e"/>',
        f'      <stop offset="100%" stop-color="#a78bfa"/>',
        f"    </linearGradient>",
        f'    <linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1">',
        f'      <stop offset="0%" stop-color="#a78bfa" stop-opacity="0"/>',
        f'      <stop offset="50%" stop-color="#a78bfa" stop-opacity="0.5"/>',
        f'      <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>',
        f"    </linearGradient>",
        f"  </defs>",
        f'  <rect width="{width}" height="340" rx="12" fill="{BG}" stroke="{PANEL_BORDER}"/>',
    ])


def footer_lines(width):
    now = datetime.now(timezone.utc)
    return "\n".join([
        f'  <text x="{width - 24}" y="326" text-anchor="end" font-family="{MONO}" font-size="9" fill="{DIM}" letter-spacing="1">SYNC {now.strftime("%m.%d.%Y")} · SRC GITHUB</text>',
        f'  <rect x="0" y="338" width="{width}" height="2" fill="{PURPLE}" opacity="0.7"/>',
        "</svg>",
    ])


def hud_corners(width, height=340):
    return "\n".join([
        f'  <g stroke="{PURPLE}" stroke-width="1.5" fill="none" opacity="0.7">',
        f'    <path d="M10 26 V10 H26"/>',
        f'    <path d="M{width - 26} 10 H{width - 10} V26"/>',
        f'    <path d="M{width - 10} {height - 26} V{height - 10} H{width - 26}"/>',
        f'    <path d="M26 {height - 10} H10 V{height - 26}"/>',
        f"  </g>",
    ])


def scan_sweep(width, height=340):
    return "\n".join([
        f'  <rect x="0" y="0" width="{width}" height="34" fill="url(#scanG)" opacity="0.5">',
        f'    <animate attributeName="y" values="0;{height}" dur="7s" repeatCount="indefinite"/>',
        f"  </rect>",
    ])


def rec_dot(width, y=26):
    return "\n".join([
        f'  <circle cx="{width - 24}" cy="{y}" r="3" fill="{PURPLE}">',
        f'    <animate attributeName="opacity" values="1;0.15;1" dur="1.5s" repeatCount="indefinite"/>',
        f"  </circle>",
    ])


# ── TELEMETRY ────────────────────────────────────────────────────────────

def build_telemetry(user, repos):
    langs = Counter(r.get("language") for r in repos if r.get("language"))
    total_repos = user.get("public_repos") or len(repos)
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    metrics = [
        ("PUBLIC REPOS", total_repos),
        ("TOTAL STARS", stars),
        ("FOLLOWERS", user.get("followers", 0)),
        ("FOLLOWING", user.get("following", 0)),
    ]
    since = (user.get("created_at") or "")[:4] or "—"
    width = 560
    out = [header_lines("Ezra5566 live telemetry snapshot", width), hud_corners(width), rec_dot(width)]
    out.append(f'  <text x="24" y="34" font-family="{MONO}" font-size="12" fill="{PURPLE}" letter-spacing="2">// TELEMETRY · LIVE_SNAPSHOT</text>')

    max_val = max((m[1] for m in metrics), default=1) or 1
    y = 66
    for i, (label, val) in enumerate(metrics):
        bar_w = max(4, int(248 * val / max_val))
        out.extend([
            f'  <text x="24" y="{y}" font-family="{MONO}" font-size="11" fill="{GRAY}" letter-spacing="1">{esc(label)}</text>',
            f'  <text x="158" y="{y}" text-anchor="end" font-family="{MONO}" font-size="14" fill="{WHITE}">{val}</text>',
            f'  <rect x="184" y="{y - 10}" width="250" height="7" rx="3.5" fill="#16161f"/>',
            f'  <rect x="184" y="{y - 10}" width="{bar_w}" height="7" rx="3.5" fill="url(#bar)">',
            f'    <animate attributeName="width" from="0" to="{bar_w}" dur="0.9s" begin="{0.5 + i * 0.22}s" fill="freeze"/>',
            f"  </rect>",
        ])
        y += 26

    out.append(f'  <line x1="24" y1="174" x2="{width - 24}" y2="174" stroke="{PANEL_BORDER}"/>')
    out.append(f'  <text x="24" y="200" font-family="{MONO}" font-size="12" fill="{PURPLE}" letter-spacing="2">// LANG.SCAN</text>')

    lang_rows = [(name, cnt) for name, cnt in langs.most_common(5)]
    max_lang = max((c for _, c in lang_rows), default=1) or 1
    y = 224
    for i, (name, cnt) in enumerate(lang_rows):
        pct = round(cnt / max(total_repos, 1) * 100)
        bar_w = max(4, int(300 * cnt / max_lang))
        out.extend([
            f'  <text x="24" y="{y}" font-family="{MONO}" font-size="11" fill="{GRAY}" letter-spacing="1">{esc(name.upper()[:12])}</text>',
            f'  <text x="158" y="{y}" text-anchor="end" font-family="{MONO}" font-size="12" fill="{WHITE}">{pct}%</text>',
            f'  <rect x="184" y="{y - 9}" width="300" height="5" rx="2.5" fill="#16161f"/>',
            f'  <rect x="184" y="{y - 9}" width="{bar_w}" height="5" rx="2.5" fill="{PURPLE}">',
            f'    <animate attributeName="width" from="0" to="{bar_w}" dur="0.8s" begin="{1.6 + i * 0.18}s" fill="freeze"/>',
            f"  </rect>",
        ])
        y += 22

    out.append(f'  <text x="24" y="326" font-family="{MONO}" font-size="9" fill="{DIM}" letter-spacing="1">SINCE {since} · {total_repos} REPOS SCANNED</text>')
    out.append(scan_sweep(width))
    out.append(footer_lines(width))
    return "\n".join(out)


# ── CONTRIBUTION MATRIX ─────────────────────────────────────────────────

def build_matrix(cells, total):
    if not cells:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="780" height="208" viewBox="0 0 780 208">'
            '<rect width="780" height="208" rx="12" fill="#0a0a12" stroke="#1d1d2b"/>'
            '<text x="24" y="30" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="12" fill="#8b5cf6" letter-spacing="2">// CONTRIBUTION_MATRIX</text>'
            '<text x="756" y="30" text-anchor="end" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="13" fill="#6d7388">NO_DATA</text>'
            '</svg>'
        )
    first = min(datetime.strptime(d, "%Y-%m-%d") for d in cells)
    # anchor to the Sunday before the first date
    anchor = first - timedelta(days=first.weekday() + 1)
    # build week columns
    weeks = []
    cur = anchor
    while any((cur + timedelta(days=i)).strftime("%Y-%m-%d") in cells for i in range(7)) or not weeks:
        col = []
        for i in range(7):
            d = (cur + timedelta(days=i)).strftime("%Y-%m-%d")
            col.append((d, cells.get(d, 0)))
        weeks.append(col)
        cur += timedelta(days=7)
        if len(weeks) > 60:
            break

    width = 780
    now = datetime.now(timezone.utc)
    cell, gap, grid_y = 11, 3, 60
    col_w = cell + gap
    n_cols = len(weeks)
    grid_w = n_cols * col_w - gap
    x0 = (width - grid_w) // 2
    height = 208
    levels = ["#16161f", "#2e2150", "#4c2e9e", "#7c4dff", "#a78bfa"]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Contribution matrix — {total} contributions in the last year">',
        f'  <defs>',
        f'    <linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1">',
        f'      <stop offset="0%" stop-color="#a78bfa" stop-opacity="0"/>',
        f'      <stop offset="50%" stop-color="#a78bfa" stop-opacity="0.5"/>',
        f'      <stop offset="100%" stop-color="#a78bfa" stop-opacity="0"/>',
        f'    </linearGradient>',
        f'  </defs>',
        f'  <rect width="{width}" height="{height}" rx="12" fill="{BG}" stroke="{PANEL_BORDER}"/>',
        f'  <text x="24" y="30" font-family="{MONO}" font-size="12" fill="{PURPLE}" letter-spacing="2">// CONTRIBUTION_MATRIX</text>',
        f'  <text x="{width - 24}" y="30" text-anchor="end" font-family="{MONO}" font-size="13" fill="{WHITE}">{total} <tspan fill="{PURPLE}">CONTRIB</tspan></text>',
    ]
    # scan sweep behind grid
    out.append(
        f'  <rect x="{x0}" y="{grid_y - 4}" width="{grid_w}" height="30" fill="url(#scanG)" opacity="0.45">'
        f'<animate attributeName="y" values="{grid_y - 4};{grid_y + 7 * (cell + gap) + 6}" dur="6s" repeatCount="indefinite"/></rect>'
    )

    month_label_x = {}
    month_dates = {}
    for c, col in enumerate(weeks):
        for i, (d, _) in enumerate(col):
            if d and d.endswith("-01"):
                month_label_x[c] = x0 + c * col_w
                month_dates[c] = d
                break

    out.append(f'  <g font-family="{MONO}" font-size="9" fill="{LIGHT}">')
    for c, x in month_label_x.items():
        month = datetime.strptime(month_dates[c], "%Y-%m-%d").strftime("%b").upper()
        out.append(f'    <text x="{x}" y="48">{month}</text>')
    out.append("  </g>")

    # weekday labels (Mon / Wed / Fri)
    for label, row in (("MON", 1), ("WED", 3), ("FRI", 5)):
        out.append(
            f'  <text x="{x0 - 10}" y="{grid_y + row * (cell + gap) + cell - 1}" text-anchor="end" font-family="{MONO}" font-size="8" fill="{DIM}">{label}</text>'
        )

    cells_svg = []
    for c, col in enumerate(weeks):
        for r, (d, lvl) in enumerate(col):
            if not d:
                continue
            x = x0 + c * col_w
            y = grid_y + r * (cell + gap)
            begin = round(0.5 + c * 0.045 + r * 0.012, 2)
            cells_svg.append(
                f'    <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{levels[lvl]}" opacity="0">'
                f'<animate attributeName="opacity" values="0;1" dur="0.35s" begin="{begin}s" fill="freeze"/></rect>'
            )
    out.append("  <g>\n" + "\n".join(cells_svg) + "\n  </g>")

    # legend
    lx = x0
    out.append(f'  <text x="{lx}" y="{height - 34}" font-family="{MONO}" font-size="9" fill="{DIM}">LESS</text>')
    for i, col in enumerate(levels):
        out.append(
            f'  <rect x="{lx + 30 + i * 17}" y="{height - 40}" width="10" height="10" rx="2" fill="{col}" opacity="0.85"/>'
        )
    out.append(f'  <text x="{lx + 30 + 5 * 17}" y="{height - 34}" font-family="{MONO}" font-size="9" fill="{DIM}">MORE</text>')
    out.append(f'  <text x="{width - 24}" y="{height - 34}" text-anchor="end" font-family="{MONO}" font-size="9" fill="{DIM}" letter-spacing="1">{n_cols} WKS · SYNC {now.strftime("%m.%d.%Y")}</text>')
    out.append(f'  <rect x="0" y="{height - 2}" width="{width}" height="2" fill="{PURPLE}" opacity="0.7"/>')
    out.append("</svg>")
    return "\n".join(out)


# ── main ─────────────────────────────────────────────────────────────────

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets = os.path.join(root, "assets")
    os.makedirs(assets, exist_ok=True)

    try:
        user = fetch_user()
        repos = fetch_repos()
        cells, total = fetch_contributions()
    except Exception as e:  # keep last good SVGs on failure
        print(f"[generate-profile-svgs] fetch failed, keeping existing SVGs: {e}", file=sys.stderr)
        sys.exit(1)

    with open(os.path.join(assets, "telemetry-stats.svg"), "w") as f:
        f.write(build_telemetry(user, repos))
    with open(os.path.join(assets, "contribution-matrix.svg"), "w") as f:
        f.write(build_matrix(cells, total))
    print(f"[generate-profile-svgs] regenerated SVGs for {USER}: {len(repos)} repos, {total} contributions")


if __name__ == "__main__":
    main()
