#!/usr/bin/env python3
"""Finish the remaining README PRs from readme_prs.py (login-page, qr-gen).
The first run was interrupted by a service restart after landing-page."""
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
        pass
    print(f"  branch {branch} deleted", flush=True)
    return pr["number"]


print("login-page:", flush=True)
current = get_readme("login-page")
assert "login-page" in current and len(current) < 100, "unexpected README"
new_readme = """# login-page

Sign in / sign up page template — static HTML with Bootstrap styling, no
backend.

## Stack

- HTML + CSS (Bootstrap)
- Font Awesome icons
- Vanilla JavaScript

Open `index.html` in a browser. The form is front-end only — wire the
submit handler to your own auth backend.
"""
make_pr("login-page", "docs/readme", new_readme,
        "docs: write a real README for the login template",
        "docs: write a real README for the login template",
        "The old README was a one-liner; this one describes what the "
        "template is, its stack, and how to use it.")

print("qr-gen:", flush=True)
current = get_readme("qr-gen")
assert current.lstrip().startswith("readme_content = '''"), "qr-gen wrapper changed?"
assert "with open('/mnt/agents/output/qr-dev-pro/README.md', 'w')" in current
fixed = current.replace("readme_content = '''", "", 1)
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

print("DONE: remaining README PRs merged", flush=True)
