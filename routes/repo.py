import os
import re
import markdown
import subprocess
from flask import request, redirect, render_template, abort
from utils.git import run_git
from config import REPO_DIR

def routes(app):

    # ------------------------
    # Home (repo list)
    # ------------------------
    @app.route("/")
    def index():
        repos = [
            r.replace(".git", "")
            for r in os.listdir(REPO_DIR)
            if r.endswith(".git")
        ]
        return render_template("index.html", repos=repos)


    # ------------------------
    # Create repo
    # ------------------------


    @app.route("/create", methods=["POST"])
    def create():
        try:
            name = request.form.get("name", "").strip()
            name = os.path.basename(name).replace(".git", "")

            # validation
            if not name or not re.match(r'^[a-zA-Z0-9._-]+$', name):
                return abort(400, "Invalid repository name")

            path = os.path.join(REPO_DIR, f"{name}.git")

            # prevent overwrite
            if os.path.exists(path):
                return abort(409, "Repository already exists")

            # create repo safely
            result = subprocess.run(
                ["git", "init", "--bare", path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return abort(500, result.stderr.strip())

            return redirect(f"/repo/{name}")

        except Exception as e:
            return abort(500, str(e))


    # ------------------------
    # Repo view
    # ------------------------
    @app.route("/repo/<name>")
    def repo(name):
        path = os.path.join(REPO_DIR, f"{name}.git")
        if not os.path.exists(path):
            abort(404)

        branch = request.args.get("branch", "main")
        subpath = request.args.get("path", "")

        if subpath and not subpath.endswith("/"):
            subpath += "/"

        tree_path = f"{branch}:{subpath}" if subpath else branch

        out, err = run_git(["ls-tree", tree_path], repo=name)

        # ------------------------
        # Empty repo
        # ------------------------
        if err and "Not a valid object name" in err:
            return render_template(
                "repo.html",
                name=name,
                items=[],
                branch=branch,
                path=subpath,
                empty=True,
                readme=None,
                breadcrumbs=[],
                branches=[]
            )

        # ------------------------
        # Files + commit info (FIXED)
        # ------------------------
        items = []

        for line in out.split("\n"):
            if not line.strip():
                continue

            try:
                # correct parsing
                meta, filename = line.split("\t", 1)
                meta_parts = meta.split()
                type_ = meta_parts[1]
            except:
                continue

            # commit info
            log_out, _ = run_git(
                ["log", "-1", "--pretty=format:%h|%s|%ar", "--", f"{subpath}{filename}"],
                repo=name
            )

            commit_hash, msg, time = "", "", ""

            if log_out:
                parts = log_out.split("|")
                if len(parts) == 3:
                    commit_hash, msg, time = parts

            items.append({
                "type": type_,
                "name": filename,
                "last_commit": msg,
                "time": time,
                "hash": commit_hash

            })

        items.sort(key=lambda x: (x["type"] != "tree", x["name"]))
        
        # ------------------------
        # README
        # ------------------------
        readme = None
        raw, _ = run_git(
            ["show", f"{branch}:{subpath}README.md"],
            repo=name
        )

        if raw:
            try:
                content = raw
            except:
                content = raw.encode("latin1").decode("utf-16", errors="ignore")

            readme = markdown.markdown(content)

        # ------------------------
        # Breadcrumbs
        # ------------------------
        parts = [p for p in subpath.split("/") if p]
        breadcrumbs = []
        current = ""

        for p in parts:
            current += p + "/"
            breadcrumbs.append((p, current))

        # ------------------------
        # Branch list
        # ------------------------
        branches_out, _ = run_git(["branch", "--list"], repo=name)
        branches = [
            b.replace("*", "").strip()
            for b in branches_out.split("\n")
            if b
        ]

        return render_template(
            "repo.html",
            name=name,
            items=items,
            branch=branch,
            path=subpath,
            readme=readme,
            breadcrumbs=breadcrumbs,
            empty=False,
            branches=branches
        )