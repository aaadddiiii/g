import subprocess
import os
from config import REPO_DIR

def run_git(args, repo=None):
    import subprocess, os
    from config import REPO_DIR

    cmd = ["git"]
    if repo:
        cmd += ["--git-dir", os.path.join(REPO_DIR, f"{repo}.git")]
    cmd += args

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return "", result.stderr.strip()

    return result.stdout.strip(), None