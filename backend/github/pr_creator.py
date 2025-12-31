import os
import re
import subprocess
import tempfile
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GITHUB_OWNER")
REPO = os.getenv("GITHUB_REPO")
BASE_BRANCH = os.getenv("GITHUB_BASE_BRANCH", "master")


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def find_file_in_repo(repo_path: str, ai_filename: str):
    """
    Improved file locator:
    - supports exact match
    - supports suffix match
    - supports duplicate filenames
    - chooses shortest path match as best fit
    """
    ai_basename = ai_filename.split("/")[-1]

    matches = []
    for root, dirs, files in os.walk(repo_path):
        for f in files:
            if f == ai_basename:
                full = os.path.join(root, f)
                matches.append(full)

    if not matches:
        return None

    # Best match: shortest path (closest to repo root)
    matches.sort(key=lambda p: len(p))
    return matches[0]


def normalize_patch_for_file(patch: str, filename: str):
    """
    Normalize patch headers to:
    --- a/<file>
    +++ b/<file>
    """
    normalized = []
    for line in patch.split("\n"):
        if line.startswith("---"):
            normalized.append(f"--- a/{filename}")
        elif line.startswith("+++"):
            normalized.append(f"+++ b/{filename}")
        else:
            normalized.append(line)
    return "\n".join(normalized)


def extract_files_from_diff(diff_text: str):
    """
    Supports:
    - --- a/file.py
    - diff --git a/src/x.py b/src/x.py
    - --- some/path.py
    """
    files = []

    # diff --git lines
    for match in re.findall(r"diff --git a/(.+?) b/(.+?)", diff_text):
        files.append(match[0])

    # --- a/file
    for match in re.findall(r"--- a/(.+?)\n", diff_text):
        files.append(match)

    # --- file.py
    for match in re.findall(r"--- (?!a/)(.+\.py)", diff_text):
        files.append(match)

    return list(set(files)) or ["unknown_file"]


def apply_patch_fallback(repo_path: str, filename: str, patch: str):
    """
    Safer fallback for patch applying.
    """
    real_path = find_file_in_repo(repo_path, filename)
    if not real_path:
        raise RuntimeError(f"Cannot locate file: {filename}")

    with open(real_path, "r") as f:
        original = f.read().splitlines()

    patch_lines = patch.split("\n")
    old = []
    new = []
    context = []

    for line in patch_lines:
        if line.startswith("-"):
            old.append(line[1:].rstrip())
        elif line.startswith("+"):
            new.append(line[1:].rstrip())
        else:
            context.append(line.rstrip())

    # fuzzy search
    idx = -1
    for i in range(len(original)):
        if original[i:i+len(old)] == old:
            idx = i
            break

    if idx == -1:
        # fallback: insert after context
        for i, line in enumerate(original):
            if any(c.strip() in line for c in context):
                idx = i + 1
                break

    if idx == -1:
        idx = len(original)

    updated = original[:idx] + new + original[idx+len(old):]

    with open(real_path, "w") as f:
        f.write("\n".join(updated) + "\n")


def create_pr_from_patch(full_patch: str, explanation: str, file_path: str, failure_id: str, owner: str, repo: str):
    """
    Creates AI PR with:
    - multi-file patch support
    - smart file detection
    - AI metadata
    """
    with tempfile.TemporaryDirectory() as tmp:
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{owner}/{repo}.git"

        run(["git", "clone", repo_url], cwd=tmp)
        repo_path = f"{tmp}/{repo}"

        # branch with failure_id
        branch = f"ai-fix-{failure_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        run(["git", "checkout", "-b", branch], cwd=repo_path)

        # parse multiple files
        files = extract_files_from_diff(full_patch)
        print("📂 Files detected:", files)

        # fallback to original file if AI patch has no headers
        if files == ["unknown_file"]:
            files = [file_path]

        for filename in files:
            real_path = find_file_in_repo(repo_path, filename)
            print(f"\n🔍 File: {filename}, Real: {real_path}")

            file_patch = normalize_patch_for_file(full_patch, filename)

            # write temporary patch
            patch_file = os.path.join(repo_path, "ai.patch")
            with open(patch_file, "w") as f:
                f.write(file_patch)

            # try git apply → fallback
            try:
                run(["git", "apply", "--ignore-whitespace", "ai.patch"], cwd=repo_path)
            except:
                apply_patch_fallback(repo_path, filename, file_patch)

        # Commit changes
        run(["git", "add", "."], cwd=repo_path)
        run(["git", "commit", "-m", f"AI Fix for failure {failure_id}"], cwd=repo_path)
        run(["git", "push", "origin", branch], cwd=repo_path)


        # Create PR
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        repo_info = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers
        ).json()

        default_branch = repo_info.get("default_branch", "main")
        print("Using default branch:", default_branch)
        data = {
            "title": f"AI Fix for CI Failure {failure_id}",
            "head": branch,
            "base": default_branch,
            "body": f"### 🤖 AI-Generated Fix\n\n**Failure ID:** {failure_id}\n\n{explanation}",
        }

        resp = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=headers,
            json=data
        )
        resp.raise_for_status()

        pr_info = resp.json()

        return {
            "pr_url": pr_info["html_url"],
            "branch": branch,
            "commit_sha": pr_info["head"]["sha"],
            "files_modified": files
        }
