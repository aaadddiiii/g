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
        repos = []

        for r in os.listdir(REPO_DIR):
            if not r.endswith(".git"):
                continue

            name = r.replace(".git", "")

            # last commit
            log, _ = run_git(
                ["log", "-1", "--pretty=format:%h|%s|%ar"],
                repo=name
            )

            last_commit = ""
            time = ""

            if log:
                parts = log.split("|")
                if len(parts) == 3:
                    _, last_commit, time = parts

            repos.append({
                "name": name,
                "last_commit": last_commit,
                "time": time
            })

        # sort newest first (optional)
        repos.sort(key=lambda x: x["time"], reverse=True)

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


    # Download Repo
    @app.route("/download/<repo>")
    def download_repo(repo):
        import os, tempfile
        from flask import abort, send_file, request
        from config import REPO_DIR
        from utils.git import run_git

        # check repo exists
        repo_path = os.path.join(REPO_DIR, f"{repo}.git")
        if not os.path.exists(repo_path):
            abort(404)

        # get branch (optional)
        branch = request.args.get("branch", "main")

        # temp zip file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        zip_path = tmp.name
        tmp.close()

        # create zip using git
        run_git(
            ["archive", "--format=zip", "-o", zip_path, branch],
            repo
        )

        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{repo}.zip"
        )

    # ------------------------
    # Repo view
    # ------------------------
    @app.route("/repo/<name>")
    def repo(name):
        import os
        from flask import abort, request, render_template
        from config import REPO_DIR
        from utils.git import run_git
        import markdown

        # ------------------------
        # Validate repo
        # ------------------------
        repo_path = os.path.join(REPO_DIR, f"{name}.git")
        if not os.path.exists(repo_path):
            abort(404)

        branch = request.args.get("branch", "main")
        subpath = request.args.get("path", "")

        if subpath and not subpath.endswith("/"):
            subpath += "/"

        tree_path = f"{branch}:{subpath}" if subpath else branch

        # ------------------------
        # Get tree
        # ------------------------
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
        # Parse files
        # ------------------------
        items = []

        for line in out.split("\n"):
            if not line.strip():
                continue

            try:
                meta, filename = line.split("\t", 1)
                meta_parts = meta.split()
                type_ = meta_parts[1]
            except:
                continue

            filepath = f"{subpath}{filename}"

            # ------------------------
            # Get LAST commit (FIXED)
            # ------------------------
            log_out, _ = run_git(
                ["log", "-1", "--pretty=format:%h|%s|%ar", branch, "--", filepath],
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
                "last_commit": msg or "—",
                "time": time,
                "hash": commit_hash
            })

        # folders first
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
                readme = markdown.markdown(raw)
            except:
                try:
                    content = raw.encode("latin1").decode("utf-16", errors="ignore")
                    readme = markdown.markdown(content)
                except:
                    readme = None

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
            if b.strip()
        ]

        # ------------------------
        # Render
        # ------------------------
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
            
            