import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(BASE_DIR, "repos")

# ensure repos directory exists
os.makedirs(REPO_DIR, exist_ok=True)