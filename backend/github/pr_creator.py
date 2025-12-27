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

def find_file_in_repo(repo_path: str, ai_filename: str):
    """
    Attempts to find the actual file path inside the real repository
    even if directory structure differs.

    Priority:
    1. Exact relative path match
    2. Suffix path match
    3. Filename-only match
    """

    ai_parts = ai_filename.split("/")
    ai_basename = ai_parts[-1]  # last part like user.py

    candidates = []

    # Walk entire repo
    for root, dirs, files in os.walk(repo_path):
        for f in files:
            if f == ai_basename:
                full_path = os.path.join(root, f)
                candidates.append(full_path)

    if not candidates:
        return None  # no matching filename

    # Try best match based on full path suffix
    for c in candidates:
        if c.replace(repo_path + "/", "").endswith(ai_filename):
            return c

    # Fallback: return first candidate found
    return candidates[0]

def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def normalize_patch_for_file(patch: str, filename: str):
    """
    Normalizes unified diff patch for ONE file.
    Ensures correct Git-friendly header lines.
    """
    normalized = []
    lines = patch.split("\n")

    for line in lines:
        # Replace placeholders
        if line.startswith("--- original_file"):
            normalized.append(f"--- a/{filename}")
        elif line.startswith("+++ fixed_file"):
            normalized.append(f"+++ b/{filename}")

        # AI may include incorrect headers — fix them:
        elif line.startswith("--- a/") and filename not in line:
            normalized.append(f"--- a/{filename}")
        elif line.startswith("+++ b/") and filename not in line:
            normalized.append(f"+++ b/{filename}")
        else:
            normalized.append(line)

    return "\n".join(normalized)

def apply_patch_fallback(repo_path: str, filename: str, patch: str):
    """
    Universal fallback patcher:
    - Uses line context matching
    - Works across ANY programming language
    - Minimal and safe modifications
    """
    file_path = find_file_in_repo(repo_path, filename)
    if not file_path:
        raise RuntimeError(f"Fallback error: {filename} not found")

    with open(file_path, "r") as f:
        original = f.read().splitlines()

    patch_lines = patch.split("\n")

    old_lines = []
    new_lines = []
    context = []

    # Extract diff blocks
    for line in patch_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("-"):
            old_lines.append(line[1:].rstrip())
        elif line.startswith("+"):
            new_lines.append(line[1:].rstrip())
        else:
            context.append(line.rstrip())

    updated = original.copy()

    # Try to locate the old block using fuzzy matching
    def find_best_match():
        for i in range(len(original)):
            window = original[i:i+len(old_lines)]
            if all(a.strip() == b.strip() for a, b in zip(window, old_lines)):
                return i
        # fallback: match using first old line
        first_old = old_lines[0].strip()
        for i, line in enumerate(original):
            if line.strip() == first_old:
                return i
        return -1  # no match found

    idx = find_best_match()

    if idx == -1:
        # Completely fallback: insert near context
        for i, line in enumerate(original):
            if any(c.strip() in line.strip() for c in context):
                insertion_index = i + 1
                updated = original[:insertion_index] + new_lines + original[insertion_index:]
                break
        else:
            # Last fallback: append at end
            updated.extend(new_lines)
    else:
        # Apply normal replacement
        updated = original[:idx] + new_lines + original[idx+len(old_lines):]

    with open(file_path, "w") as f:
        f.write("\n".join(updated) + "\n")
def split_patch_into_files(full_patch: str):
    patches = {}
    current_file = None
    buffer = []

    lines = full_patch.split('\n')

    for line in lines:
        # Detect file header in ANY form
        if line.startswith('---'):
            # Save old
            if current_file and buffer:
                patches[current_file] = '\n'.join(buffer)
                buffer = []

            # Extract filename (fallback to placeholder)
            parts = line.split()
            if len(parts) > 1:
                raw = parts[1]  # second token
                raw = raw.replace("a/", "")  # remove git prefix
                raw = raw.replace("original_file", "")  # AI placeholder
                raw = raw.strip()
                if raw == "":
                    raw = "unknown_file"

                current_file = raw
            else:
                current_file = "unknown_file"

        if current_file:
            buffer.append(line)

    if current_file and buffer:
        patches[current_file] = '\n'.join(buffer)

    return patches


def create_pr_from_patch(full_patch: str, explanation: str, file_path: str):
    """
    Multi-file smart patch application + PR creation.
    """
    with tempfile.TemporaryDirectory() as tmp:
        repo_url = f"https://{GITHUB_TOKEN}@github.com/{OWNER}/{REPO}.git"

        # Clone repo
        run(["git", "clone", repo_url], cwd=tmp)
        repo_path = f"{tmp}/{REPO}"

        # Create branch
        branch = f"ai-fix-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        run(["git", "checkout", "-b", branch], cwd=repo_path)

        # Split multi-file patches
        file_patches = split_patch_into_files(full_patch)

        print("\n📂 Files detected in patch:", list(file_patches.keys()))

        # If AI patch used placeholders, fallback to correct file
        if not file_patches or list(file_patches.keys()) == ["unknown_file"]:
            print("⚠ No valid file headers found — forcing single-file patch")
            file_patches = {file_path: full_patch}

        for filename, file_patch in file_patches.items():
            print(f"\n🔍 Processing patch for: {filename}")

            # Find real file in repo
            real_path = find_file_in_repo(repo_path, filename)
            if not real_path:
                print(f"⚠️ File {filename} not found in repo. Skipping.")
                continue

            print(f"📌 Real file path: {real_path}")

            # Normalize patch
            normalized = normalize_patch_for_file(file_patch, filename)

            # Write temp patch file
            patch_filename = f"ai_patch_{filename.replace('/', '_')}.patch"
            patch_path = os.path.join(repo_path, patch_filename)

            with open(patch_path, "w") as f:
                f.write(normalized)

            print(f"📝 Patch written to: {patch_filename}")

            # Try git apply
            try:
                run(["git", "apply", "--ignore-whitespace", patch_filename], cwd=repo_path)
                print("✅ git apply success")
            except:
                print("⚠️ git apply failed — using fallback")
                apply_patch_fallback(repo_path, filename, normalized)

        # Commit & push
        run(["git", "add", "."], cwd=repo_path)
        run(["git", "commit", "-m", "AI: Fix CI failure"], cwd=repo_path)
        run(["git", "push", "origin", branch], cwd=repo_path)

        # Create PR
        pr_url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        data = {
            "title": "AI Fix: CI Failure",
            "head": branch,
            "base": "master",
            "body": explanation,
        }

        response = requests.post(pr_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["html_url"]
