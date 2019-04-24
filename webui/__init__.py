import os
from main.logger_helper import L
from main.flask_app import app
from common import Constant, get_json_param
from webui import helpers


class P:
    initialised = False
    flask_thread = None

    def __init__(self):
        pass


class ReverseProxied(object):
    '''Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    http://flask.pocoo.org/snippets/35/

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    '''
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


def unload():
    if P.flask_thread is not None:
        P.flask_thread.shutdown()


def init():
    L.l.debug('FlaskAdmin UI module initialising')
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.config['STATIC_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static')
    host = '0.0.0.0'
    port = int(get_json_param(Constant.P_FLASK_WEB_PORT))
    P.flask_thread = helpers.FlaskInThread(app, host=host, port=port, debug=True, use_reloader=False)
    P.initialised = True
    P.flask_thread.start()


@app.route('/')
def index():
    return '<a href="/admin/">Click me to get to Admin!</a>'
