import mimetypes

from sqlalchemy import Connection
from werkzeug import Request, Response, run_simple

from openrouteindex.db import engine
from openrouteindex.environment import build_environment
from openrouteindex.views.base import BaseView


class WSGIApplication:
    def __init__(self, conn: Connection, pages: list[BaseView], global_context: dict):
        self.conn = conn
        self.pages = pages
        self.global_context = global_context

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        if not response:
            response = Response('404 - Page not found', status=404)

        return response(environ, start_response)

    def dispatch_request(self, request) -> Response | None:
        for item in self.pages:
            path = request.path.lstrip('/')
            if item.get_filename() == path:
                mtype, _ = mimetypes.guess_type(path)
                with self.conn.begin() as tx:
                    response_message = item.render(self.conn, self.global_context)
                return Response(response_message, content_type=mtype if mtype else 'text/html')

        if request.path == '/' or request.path == '':
            return Response('Redirect to index.html', status=301, headers={'Location': 'index.html'})


def run_server():
    with engine.connect() as conn:
        with conn.begin() as tx:
            pages, global_context = build_environment(conn)

        app = WSGIApplication(conn, pages, global_context)
        run_simple('127.0.0.1', 8000, app, use_debugger=True, use_reloader=True)


if __name__ == '__main__':
    run_server()