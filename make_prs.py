#!/usr/bin/env python3
"""Open and merge two genuine docs PRs (no review) for hymndavinci.

PR 1 (hymn-router): README dashboard bullet describes the old dashboard;
update it to the new Activity layout (7/30-day range, tabs, stat cards).
PR 2 (portofolio): document that the DB uses `prisma db push` with no
migration history and that `prisma migrate deploy` breaks the build.
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
        # DELETE ref returns 204 with an empty body; the helper's JSON
        # parser chokes on it even though the delete succeeded.
        gp.api_request("DELETE", f"/repos/{OWNER}/{repo}/git/refs/heads/{branch}")
    except Exception as e:
        print(f"  branch delete response ignored ({type(e).__name__})", flush=True)
    print(f"  branch {branch} deleted", flush=True)
    return pr["number"]


# --- PR 1: hymn-router README dashboard bullet ---
# DONE already (PR #1 merged 2026-11-14T04:59:51Z, branch deleted).

# --- PR 2: portofolio README database note ---
print("PR 2: portofolio", flush=True)
anchor = "## Project Structure"
db_note = (
    "## Database\n"
    "\n"
    "PostgreSQL via Prisma. The schema is synced with `prisma db push` — this\n"
    "project has **no migration history** (`prisma/migrations` does not exist).\n"
    "\n"
    "> Do not run `prisma migrate deploy` or `prisma migrate dev`: without a\n"
    "> baseline migration they fail (P3005) and break the build. The build\n"
    "> script already runs `prisma generate && prisma db push && next build`.\n"
    "\n"
)
content = get_readme("portofolio")
assert anchor in content, "anchor not found in portofolio README"
assert "prisma db push" not in content.split(anchor)[0], "note already present?"
content = content.replace(anchor, db_note + anchor, 1)
make_pr(
    "portofolio", "docs/db-push-note", content,
    "docs: note that the DB uses prisma db push, no migrations",
    "docs: note that the DB uses prisma db push, no migrations",
    "Documents the actual database workflow: `prisma db push`, no "
    "`prisma/migrations` history. Warns that `prisma migrate deploy` / "
    "`migrate dev` fail with P3005 and break the build.",
)

print("DONE: both PRs merged", flush=True)
