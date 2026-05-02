import os
import subprocess
from flask import request, Response
from config import REPO_DIR

def routes(app):

    @app.route("/git/<path:path>", methods=["GET", "POST"])
    def git_http(path):
        env = os.environ.copy()

        # REQUIRED for git-http-backend
        env["GIT_PROJECT_ROOT"] = REPO_DIR
        env["GIT_HTTP_EXPORT_ALL"] = "1"

        # REQUIRED for push (fix)
        env["REMOTE_USER"] = "user"

        env["PATH_INFO"] = f"/{path}"
        env["REQUEST_METHOD"] = request.method
        env["QUERY_STRING"] = request.query_string.decode()

        env["CONTENT_TYPE"] = request.headers.get("Content-Type", "")
        env["CONTENT_LENGTH"] = request.headers.get("Content-Length", "")

        proc = subprocess.Popen(
            ["git", "http-backend"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        stdout, stderr = proc.communicate(input=request.get_data())

        # Split headers and body
        header_data, _, body = stdout.partition(b"\r\n\r\n")

        headers = []
        status = 200

        for line in header_data.split(b"\r\n"):
            if line.startswith(b"Status:"):
                status = int(line.split()[1])
            elif b":" in line:
                k, v = line.split(b":", 1)
                headers.append((k.decode(), v.strip().decode()))

        return Response(body, status=status, headers=headers)