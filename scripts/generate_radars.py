#!/usr/bin/env python3
"""Generate two dark radar-chart SVGs for the profile README, from real
GitHub data (no made-up skill scores):

- assets/radar-langs.svg  — top languages by bytes across non-fork repos.
- assets/radar-focus.svg  — repos by category (mapping below).

Env vars:
  GITHUB_LOGIN - github username (required)
  GITHUB_TOKEN - token for the API (optional locally; the workflow passes
                 the default GITHUB_TOKEN)
"""
import math
import os
import sys

LOGIN = os.environ.get("GITHUB_LOGIN", "hymndavinci")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

# repo -> focus category. Anything unlisted falls back to "Tools".
FOCUS_MAP = {
    "portofolio": "Web Apps",
    "Kasir-Pintar": "Web Apps",
    "animestream": "Web Apps",
    "hymn": "Web Apps",
    "Exe": "Web Apps",
    "code-explainer": "Web Apps",
    "rpc-v2": "Discord",
    "selfbot-q": "Discord",
    "rpc": "Discord",
    "bot-telegram": "Discord",
    "landing-dahayu": "Landing Pages",
    "landing-page": "Landing Pages",
    "poertoe": "Landing Pages",
    "login-page": "Landing Pages",
    "hymn-router": "AI / LLM",
}

BG = "#0b1120"
GRID = "#2a3350"
LABEL = "#e8e8e8"
VALUE = "#5dc9f2"
ACCENT = "#e8384f"
POLY_FILL = "#5dc9f2"
POLY_STROKE = "#5dc9f2"


def radar_svg(title, subtitle, items, size=440):
    """items: list of (label, value 0-100, display string)."""
    n = len(items)
    cx, cy = size / 2, size / 2 + 12
    radius = size / 2 - 78
    cx = size / 2

    def pt(i, frac):
        ang = math.radians(-90 + i * (360 / n))
        r = radius * frac
        return (cx + r * math.cos(ang), cy + r * math.sin(ang))

    parts = []
    # rings
    for frac in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, frac) for i in range(n)))
        parts.append(f'<polygon points="{pts}" fill="none" stroke="{GRID}" stroke-width="1" />')
    # axis lines
    for i in range(n):
        x, y = pt(i, 1.0)
        parts.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x:.1f}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1" />')
    # data polygon
    data_pts = []
    for i, (_, v, _) in enumerate(items):
        data_pts.append(pt(i, v / 100.0))
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts)
    parts.append(f'<polygon points="{pts}" fill="{POLY_FILL}" fill-opacity="0.25" stroke="{POLY_STROKE}" stroke-width="2" stroke-linejoin="round" />')
    for x, y in data_pts:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ACCENT}" />')
    # labels
    for i, (label, _, disp) in enumerate(items):
        ang = math.radians(-90 + i * (360 / n))
        lx = cx + (radius + 16) * math.cos(ang)
        ly = cy + (radius + 16) * math.sin(ang)
        cos_a = math.cos(ang)
        anchor = "start" if cos_a > 0.3 else ("end" if cos_a < -0.3 else "middle")
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" class="lab">{label}</text>'
            f'<text x="{lx:.1f}" y="{ly + 15:.1f}" text-anchor="{anchor}" class="val">{disp}</text>'
        )

    body = "\n  ".join(parts)
    return f'''<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{size}" height="{size}" rx="10" fill="{BG}" />
  <text x="{cx:.0f}" y="30" text-anchor="middle" class="title">{title}</text>
  <text x="{cx:.0f}" y="50" text-anchor="middle" class="sub">{subtitle}</text>
  <style>
    .title {{ font-family: 'Courier New', monospace; font-size: 16px; font-weight: bold; fill: {ACCENT}; }}
    .sub {{ font-family: 'Courier New', monospace; font-size: 11px; fill: #7f8aa6; }}
    .lab {{ font-family: 'Courier New', monospace; font-size: 12px; font-weight: bold; fill: {LABEL}; }}
    .val {{ font-family: 'Courier New', monospace; font-size: 11px; fill: {VALUE}; }}
  </style>
  {body}
</svg>
'''


def fetch_data():
    import requests
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    repos = []
    url = f"https://api.github.com/users/{LOGIN}/repos?per_page=100&type=owner"
    while url:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        repos.extend(r.json())
        url = r.links.get("next", {}).get("url")
    totals = {}
    focus = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        cat = FOCUS_MAP.get(repo["name"], "Tools")
        focus[cat] = focus.get(cat, 0) + 1
        try:
            lr = requests.get(
                f"https://api.github.com/repos/{LOGIN}/{repo['name']}/languages",
                headers=headers, timeout=15)
            lr.raise_for_status()
            for lang, b in lr.json().items():
                totals[lang] = totals.get(lang, 0) + b
        except Exception as e:
            print(f"warning: languages for {repo['name']} failed: {e}", file=sys.stderr)
    return totals, focus


def main():
    totals, focus = fetch_data()
    total_bytes = sum(totals.values()) or 1
    top_langs = sorted(totals.items(), key=lambda kv: -kv[1])[:6]
    max_bytes = top_langs[0][1]
    lang_items = [
        (lang, round(b / max_bytes * 100), f"{b / total_bytes * 100:.0f}%")
        for lang, b in top_langs
    ]
    # order axes so big values are spread around the radar
    order = [0, 3, 1, 4, 2, 5] if len(lang_items) == 6 else list(range(len(lang_items)))
    lang_items = [lang_items[i] for i in order if i < len(lang_items)]

    cats = ["Web Apps", "Discord", "Landing Pages", "AI / LLM", "Tools"]
    max_count = max(focus.get(c, 0) for c in cats) or 1
    focus_items = [
        (c, round(focus.get(c, 0) / max_count * 100),
         f"{focus.get(c, 0)} repo" + ("s" if focus.get(c, 0) != 1 else ""))
        for c in cats
    ]

    os.makedirs("assets", exist_ok=True)
    with open("assets/radar-langs.svg", "w", encoding="utf-8") as f:
        f.write(radar_svg("languages", "share of code across public repos (bytes)",
                          lang_items))
    with open("assets/radar-focus.svg", "w", encoding="utf-8") as f:
        f.write(radar_svg("focus", "public repos by category",
                          focus_items))
    print("wrote assets/radar-langs.svg, assets/radar-focus.svg")
    print("langs:", lang_items)
    print("focus:", focus_items)


if __name__ == "__main__":
    main()
