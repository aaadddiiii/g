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

        # FIX: ensure content is safe text
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")

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
        from config import REPO_DIR
        from utils.git import run_git

        # ------------------------
        # Validate repo
        # ------------------------
        repo_path = os.path.join(REPO_DIR, f"{repo}.git")
        if not os.path.exists(repo_path):
            abort(404)

        # ------------------------
        # Commit metadata
        # ------------------------
        meta, _ = run_git(
            ["show", "-s", "--pretty=format:%h|%s|%an|%ar", commit_hash],
            repo
        )

        commit_info = {
            "hash": commit_hash,
            "message": "",
            "author": "",
            "time": ""
        }

        if meta:
            parts = meta.split("|")
            if len(parts) == 4:
                commit_info = {
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "time": parts[3]
                }

        # ------------------------
        # Diff (FORCE TEXT FIX)
        # ------------------------
        diff, _ = run_git(
            ["show", "--pretty=format:", "--unified=3", "--text", commit_hash],
            repo
        )

        files = []
        current_file = None

        for line in diff.split("\n"):

            # new file block
            if line.startswith("diff --git"):
                if current_file:
                    files.append(current_file)

                file_name = line.split(" b/")[-1]

                current_file = {
                    "name": file_name,
                    "lines": [],
                    "additions": 0,
                    "deletions": 0,
                    "is_binary": False
                }

            elif current_file is not None:

                # detect binary fallback
                if "Binary files" in line:
                    current_file["is_binary"] = True

                # count stats (ignore metadata lines)
                elif line.startswith("+") and not line.startswith("+++"):
                    current_file["additions"] += 1

                elif line.startswith("-") and not line.startswith("---"):
                    current_file["deletions"] += 1

                current_file["lines"].append(line)

        if current_file:
            files.append(current_file)

        # ------------------------
        # Summary stats
        # ------------------------
        total_add = sum(f["additions"] for f in files)
        total_del = sum(f["deletions"] for f in files)

        summary = {
            "files_changed": len(files),
            "additions": total_add,
            "deletions": total_del
        }

        # ------------------------
        # Render
        # ------------------------
        return render_template(
            "commit_view.html",
            repo=repo,
            commit=commit_hash,
            info=commit_info,
            files=files,
            summary=summary
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