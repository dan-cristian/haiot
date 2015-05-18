__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import os
from main import logger, app, BIND_IP, BIND_PORT
from main.admin import model_helper
from flask import request, abort, send_file, render_template
from common import constant
import webui
import helpers

initialised=False
flask_thread=None

@app.route('/exit', methods=['POST'])
def exit():
    logger.info('WebUI module unloading')
    try:
        if not app.testing:
            logger.warning('Unable to shutdown werk if not in testing mode')
        else:
            #with app.app_context():
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    logger.warning('unable to unload webui, not running with the Werkzeug Server')
                else:
                    logger.info('shuting down werkzeug')
                    func()
                global initialised
                initialised = False
                return 'werkzeug exited'
    except Exception, ex:
        logger.warning('Unable to shutdown werkzeug, err {}'.format(ex))
    return 'werkzeug not exited'

def unload():
    logger.info('Webui module unloading')
    #response = app.test_client().post('/exit')

def init():
    logger.info('WebUI module initialising')
    #thread_pool.add_callable(webui.thread_run, run_interval_second=60)
    from main.admin import admin, user
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(user, url_prefix='/user')
    global initialised
    if BIND_IP is not None and BIND_PORT is not None:
        #host = os.environ.get('OPENSHIFT_PYTHON_IP')
        host = BIND_IP
        port = BIND_PORT
    else:
        #otherwise listen on all interfaces
        host='0.0.0.0'
        port = model_helper.get_param(constant.P_FLASK_WEB_PORT)
    flask_thread = helpers.FlaskInThread(app, host=host, port=port, debug=True, use_reloader=False)
    initialised = True
    flask_thread.start()
    #app.run(debug=True, use_reloader=False, host='0.0.0.0')

@app.route('/')
def home():
    return '<a href="/user/node">Node</a>'

@app.route('/ebooks', defaults={'req_path': ''})
@app.route('/<path:req_path>')
def dir_listing(req_path):
    try:
        #BASE_DIR = '/media/ebooks'
        BASE_DIR = '/temp'

        # Joining the base and the requested path
        abs_path = os.path.join(BASE_DIR, req_path)

        # Return 404 if path doesn't exist
        if not os.path.exists(abs_path):
            return abort(404)

        # Check if path is a file and serve
        if os.path.isfile(abs_path):
            return send_file(abs_path)

        # Show directory contents
        files = os.listdir(abs_path)
        return render_template('files.html', files=files)
    except Exception, ex:
        return 'Error request={}, err={}'.format(req_path, ex)