# import requests
# import os
# from dotenv import load_dotenv
# load_dotenv()
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# OWNER = os.getenv("GITHUB_OWNER")
# REPO = os.getenv("GITHUB_REPO")

# def fetch_pr_diff(pr_number: int):
#     """Fetch the RAW diff of the PR from GitHub."""
#     url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}"
#     headers = {
#         "Authorization": f"token {GITHUB_TOKEN}",
#         "Accept": "application/vnd.github.v3.diff"
#     }

#     resp = requests.get(url, headers=headers)
#     if resp.status_code != 200:
#         return None

#     return resp.text
