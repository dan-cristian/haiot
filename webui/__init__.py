__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging

from main.admin import thread_pool
from main import app, blocking_webui_running

import webui

initialised=False

def unload():
    logging.info('WebUI module unloading')
    #thread_pool.remove_callable(webui.thread_run)
    global blocking_webui_running
    blocking_webui_running = False
    app.stop()
    global initialised
    initialised = False

def init():
    logging.info('WebUI module initialising')
    #thread_pool.add_callable(webui.thread_run, run_interval_second=60)

    from main.admin import admin, user
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(user, url_prefix='/user')
    global blocking_webui_running
    blocking_webui_running = True
    app.run(debug=True, use_reloader=False, host='0.0.0.0')
    global initialised
    initialised = True

if __name__ == '__main__':
    webui.thread_run()