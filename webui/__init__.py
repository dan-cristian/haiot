import os
from flask import request, render_template, redirect, url_for, send_from_directory, send_file
from main.logger_helper import L
from main import app, BIND_IP, BIND_PORT
from main.admin import model_helper
from common import Constant
import helpers
import traceback

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


initialised = False
flask_thread = None


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


@app.route('/exit', methods=['POST'])
def exit_module():
    L.l.info('WebUI module unloading')
    try:
        if not app.testing:
            L.l.warning('Unable to shutdown werk if not in testing mode')
        else:
            #with app.app_context():
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    L.l.warning('unable to unload webui, not running with the Werkzeug Server')
                else:
                    L.l.info('shuting down werkzeug')
                    func()
                global initialised
                initialised = False
                return 'werkzeug exited'
    except Exception, ex:
        L.l.warning('Unable to shutdown werkzeug, err {}'.format(ex))
    return 'werkzeug not exited'


def unload():
    L.l.info('Webui module unloading')
    # response = app.test_client().post('/exit')


def init():
    L.l.debug('WebUI module initialising')
    # thread_pool.add_callable(webui.thread_run, run_interval_second=60)
    from crud import admin, user
    crud.init_crud()
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(user, url_prefix='/user')
    global initialised, flask_thread
    if BIND_IP is not None and BIND_PORT is not None:
        host = BIND_IP
        port = BIND_PORT
    else:
        # otherwise listen on all interfaces
        host = '0.0.0.0'
        port = int(model_helper.get_param(Constant.P_FLASK_WEB_PORT))
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.config['STATIC_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static')
    flask_thread = helpers.FlaskInThread(app, host=host, port=port, debug=True, use_reloader=False)
    initialised = True
    flask_thread.start()
    from webui.api import api_v1
    # app.run(debug=True, use_reloader=False, host='0.0.0.0')


@app.route('/')
def home():
    # return '<a href="user/node">Node</a>'
    return redirect(url_for('user.node'))


@app.route('/favicon.ico')
def favicon():
    return send_file("../webui/static/favicon.ico", mimetype='image/ico')


@app.before_request
def log_before_request():
    # if app.config.get('LOG_REQUESTS'):
    L.l.debug('HTTP Request START: {}'.format(request))


@app.after_request
def log_after_request(response):
    # if app.config.get('LOG_REQUESTS'):
    L.l.debug('HTTP Request END: {} ARG={}'.format(request, response))
    return response


@app.errorhandler(Exception)
def exceptions(e):
    tb = traceback.format_exc()
    L.l.error('%s %s %s %s 5xx INTERNAL SERVER ERROR\n%s',
              request.remote_addr, request.method, request.scheme, request.full_path, tb)
    return e.status_code


@app.errorhandler(404)
def page_not_found(e):
    L.l.error('Error {} [{}]'.format(e, request.path))
    return render_template('404.html'), 404
