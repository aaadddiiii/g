import os
from flask import render_template, request, abort
from utils.git import run_git
from config import REPO_DIR


def routes(app):

    # ------------------------
    # File view
    # ------------------------
    @app.route("/file/<repo>/<path:filepath>")
    def file(repo, filepath):
        repo_path = os.path.join(REPO_DIR, f"{repo}.git")
        if not os.path.exists(repo_path):
            abort(404)

        branch = request.args.get("branch", "main")

        content, err = run_git(["show", f"{branch}:{filepath}"], repo)

        if err:
            content = err

        return render_template(
            "file.html",
            name=repo,
            file=filepath,
            content=content,
            branch=branch
        )


    # ------------------------
    # Commit history
    # ------------------------
    @app.route("/commits/<repo>")
    def commits(repo):
        repo_path = os.path.join(REPO_DIR, f"{repo}.git")
        if not os.path.exists(repo_path):
            abort(404)

        branch = request.args.get("branch", "main")

        log, err = run_git(
            ["log", "--pretty=format:%h|%s|%an|%ar", "-n", "30", branch],
            repo
        )

        commits = []

        if log:
            for line in log.split("\n"):
                if not line:
                    continue

                parts = line.split("|")

                # safety check
                if len(parts) < 4:
                    continue

                h, msg, author, time = parts

                commits.append({
                    "hash": h,
                    "message": msg,
                    "author": author,
                    "time": time
                })

        return render_template(
            "commits.html",
            name=repo,
            commits=commits,
            branch=branch
        )
        
        
        
        
    @app.route("/commit/<repo>/<commit_hash>")
    def commit_view(repo, commit_hash):
        import os
        from flask import abort

        repo_path = os.path.join(REPO_DIR, f"{repo}.git")
        if not os.path.exists(repo_path):
            abort(404)

        diff, _ = run_git(
            ["show", "--pretty=format:", "--unified=3", commit_hash],
            repo
        )

        files = []
        current_file = None

        for line in diff.split("\n"):
            if line.startswith("diff --git"):
                if current_file:
                    files.append(current_file)

                file_name = line.split(" b/")[-1]
                current_file = {
                    "name": file_name,
                    "lines": []
                }

            elif current_file is not None:
                current_file["lines"].append(line)

        if current_file:
            files.append(current_file)

        return render_template(
            "commit_view.html",
            repo=repo,
            commit=commit_hash,
            files=files
        )
        
        
        
        
        
    @app.route("/history/<repo>/<path:filepath>")
    def file_history(repo, filepath):
        import os
        from flask import abort, request

        repo_path = os.path.join(REPO_DIR, f"{repo}.git")
        if not os.path.exists(repo_path):
            abort(404)

        branch = request.args.get("branch", "main")

        log, _ = run_git(
            ["log", branch, "--follow", "--pretty=format:%h|%s|%an|%ar", "--", filepath],
            repo
        )

        commits = []
        if log:
            for line in log.split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) < 4:
                    continue

                h, msg, author, time = parts

                commits.append({
                    "hash": h,
                    "message": msg,
                    "author": author,
                    "time": time
                })

        return render_template(
            "history.html",
            repo=repo,
            file=filepath,
            commits=commits,
            branch=branch
        )