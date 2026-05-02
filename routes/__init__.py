from . import repo, file, git_http

def routes(app):
    repo.routes(app)
    file.routes(app)
    git_http.routes(app)