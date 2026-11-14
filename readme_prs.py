#!/usr/bin/env python3
"""Rewrite the weak READMEs across hymndavinci's repos, each as its own
merged PR (no review). Genuine improvements only: boilerplate templates,
one-liners, and a Python-wrapped README get replaced with real docs
written from each repo's actual contents.

Skipped deliberately: forks (freebuff2api-wokers, cloner-v2,
ALL-IN-ONE-Discord-Bot-, register), repos whose README is already good,
and bot-telegram (empty repo, nothing to describe, no base to PR from).
"""
import base64
import sys
import time

sys.path.insert(0, "/home/hatch/workspace/custom-connectors/custom.github/bin")
import github_push as gp

OWNER = "hymndavinci"
AUTHOR = {"name": "Muhammad Bintang Kurniawan", "email": "hymndavinci@gmail.com"}


def get_readme(repo):
    d = gp.api_request("GET", f"/repos/{OWNER}/{repo}/contents/README.md?ref=main")
    return base64.b64decode(d["content"]).decode("utf-8")


def make_pr(repo, branch, new_content, commit_msg, pr_title, pr_body):
    ref = gp.api_request("GET", f"/repos/{OWNER}/{repo}/git/ref/heads/main")
    base_sha = ref["object"]["sha"]
    commit = gp.api_request("GET", f"/repos/{OWNER}/{repo}/git/commits/{base_sha}")
    base_tree = commit["tree"]["sha"]
    gp.api_request("POST", f"/repos/{OWNER}/{repo}/git/refs",
                   {"ref": f"refs/heads/{branch}", "sha": base_sha})
    blob = gp.api_request("POST", f"/repos/{OWNER}/{repo}/git/blobs",
                          {"content": new_content, "encoding": "utf-8"})
    tree = gp.api_request("POST", f"/repos/{OWNER}/{repo}/git/trees",
                          {"base_tree": base_tree,
                           "tree": [{"path": "README.md", "mode": "100644",
                                     "type": "blob", "sha": blob["sha"]}]})
    new_commit = gp.api_request("POST", f"/repos/{OWNER}/{repo}/git/commits",
                                {"message": commit_msg, "tree": tree["sha"],
                                 "parents": [base_sha],
                                 "author": AUTHOR, "committer": AUTHOR})
    gp.api_request("PATCH", f"/repos/{OWNER}/{repo}/git/refs/heads/{branch}",
                   {"sha": new_commit["sha"]})
    pr = gp.api_request("POST", f"/repos/{OWNER}/{repo}/pulls",
                        {"title": pr_title, "head": branch, "base": "main",
                         "body": pr_body})
    print(f"  PR opened: {pr['html_url']} (#{pr['number']})", flush=True)
    merged = None
    for attempt in range(6):
        try:
            merged = gp.api_request(
                "PUT", f"/repos/{OWNER}/{repo}/pulls/{pr['number']}/merge",
                {"merge_method": "squash"})
            break
        except RuntimeError as e:
            if "405" in str(e) or "409" in str(e):
                print(f"  merge not ready, retry {attempt + 1}/6...", flush=True)
                time.sleep(4)
            else:
                raise
    if not merged or not merged.get("merged"):
        raise RuntimeError(f"merge failed for PR #{pr['number']}: {merged}")
    print(f"  merged: {merged.get('sha')}", flush=True)
    try:
        gp.api_request("DELETE", f"/repos/{OWNER}/{repo}/git/refs/heads/{branch}")
    except Exception:
        pass  # 204 empty body breaks the helper's JSON parser; delete succeeds
    print(f"  branch {branch} deleted", flush=True)
    return pr["number"]


JOBS = []

# --- Exe: default Vite template README -> real one.
# The app is a personal photo gallery; keep the README functional and
# neutral (no names, no personal framing).
JOBS.append(("Exe", """# Exe

Personal photo gallery web app — a gallery with favorites and memories
views, built as a single-page React app.

## Stack

- React 19 + TypeScript
- Vite 8
- Tailwind CSS 4
- lucide-react icons

## Run it

```bash
npm install
npm run dev
```

```bash
npm run build   # production build
npm run preview # preview the build
```
""", lambda c: c.startswith("# React + TypeScript + Vite"),
"docs: replace Vite template README with a real one"))

# --- hymn: 74-char credit line -> real README (keeps the credit).
JOBS.append(("hymn", """# hymn

Personal portfolio site built with Astro.

## Stack

- Astro 5
- React 18
- Tailwind CSS 3

## Run it

```bash
npm install
npm run dev
```

```bash
npm run build   # production build into dist/
npm run preview # preview the build
```

## Credits

Based on [Dan Chavez's portfolio](https://github.com/dnachavez/portfolio) template.
""", lambda c: "Dan Chavez" in c and len(c) < 200,
"docs: write a real README (keeps template credit)"))

# --- poertoe: README is literally "hi".
JOBS.append(("poertoe", """# poertoe

An earlier static portfolio site — plain HTML, CSS, and JavaScript, no
build step.

Open `index.html` in a browser, or serve the folder with any static server:

```bash
npx serve .
```

Superseded by the current portfolio at [hymndavinci.my.id](https://www.hymndavinci.my.id)
(see [portofolio](https://github.com/hymndavinci/portofolio)).
""", lambda c: c.strip() == "hi",
"docs: replace one-word README with a real one"))

# --- landing-dahayu: README is just the repo name.
JOBS.append(("landing-dahayu", """# landing-dahayu

Landing page for the Dahayu community server — static HTML, CSS, and
JavaScript with a cyber/matrix visual theme.

Open `index.html` in a browser, or serve the folder with any static server:

```bash
npx serve .
```

## Credits

Based on the [TemplateMo 594 Nexus Flow](https://templatemo.com/tm-594-nexus-flow) template.
""", lambda c: "landing-dahayu" in c and len(c) < 100,
"docs: write a real README for the Dahayu landing page"))

# --- landing-page: default create-next-app boilerplate.
JOBS.append(("landing-page", """# landing-page

Simple landing page for the Dahayu community server, built with Next.js.

## Stack

- Next.js 15 (Pages Router)
- React 19

## Run it

```bash
npm install
npm run dev
```

```bash
npm run build
npm run start
```
""", lambda c: "bootstrapped with [`create-next-app`]" in c,
"docs: replace create-next-app boilerplate README"))

# --- login-page: 38-char README.
JOBS.append(("login-page", """# login-page

Sign in / sign up page template — static HTML with Bootstrap styling, no
backend.

## Stack

- HTML + CSS (Bootstrap)
- Font Awesome icons
- Vanilla JavaScript

Open `index.html` in a browser. The form is front-end only — wire the
submit handler to your own auth backend.
""", lambda c: "login-page" in c and len(c) < 100,
"docs: write a real README for the login template"))

for repo, new_readme, check, msg in JOBS:
    print(f"{repo}:", flush=True)
    current = get_readme(repo)
    assert check(current), f"unexpected current README in {repo}; aborting"
    assert new_readme != current
    make_pr(repo, "docs/readme", new_readme, msg, msg,
            "The old README was boilerplate/a placeholder; this one "
            "describes what the repo actually is, its stack, and how "
            "to run it.")

# --- qr-gen: README is wrapped in leaked Python code.
# Strip the `readme_content = '''` prefix, the trailing Python, and fix
# the broken screenshot markdown. Keep the real content in the middle.
print("qr-gen:", flush=True)
current = get_readme("qr-gen")
assert current.lstrip().startswith("readme_content = '''"), "qr-gen wrapper changed?"
assert "with open('/mnt/agents/output/qr-dev-pro/README.md', 'w')" in current
fixed = current
fixed = fixed.replace("readme_content = '''", "", 1)
cut = fixed.find("\n'''\n\nwith open(")
assert cut != -1, "qr-gen trailing marker not found"
fixed = fixed[:cut] + "\n"
fixed = fixed.replace(
    "![QR.DEV Pro Screenshot]\nhttps://github.com/hymndavinci/qr-gen/blob/main/qr.png\n)",
    "![QR.DEV Pro Screenshot](https://github.com/hymndavinci/qr-gen/blob/main/qr.png)")
assert "readme_content" not in fixed and "with open(" not in fixed
assert fixed.strip().startswith("# QR.DEV Pro")
make_pr("qr-gen", "docs/readme", fixed,
        "docs: strip leaked Python wrapper from README, fix screenshot",
        "docs: strip leaked Python wrapper from README, fix screenshot",
        "The README was accidentally committed wrapped in the Python code "
        "that generated it (`readme_content = '''...'''` plus a file-write "
        "script), and the screenshot markdown was broken across lines. "
        "This keeps the real content and removes the wrapper.")

print("DONE: all README PRs merged", flush=True)
