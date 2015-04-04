# project/__init__.py

import time
import sys
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask import Flask, redirect, url_for

import logging
import common
from common import constant

#location for sqlite db
DB_LOCATION=None
#default logging
LOGGING_LEVEL=logging.INFO
app=None
db=None
webui_running = False
initialised = False
shutting_down=False
exit_code = 0
MODEL_AUTO_UPDATE=False

def my_import(name):
    #http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def init_module(module_name, module_is_active):
    dynclass = my_import(module_name)
    if module_is_active:
        logging.info('Module {} is active'.format(module_name))
        if not dynclass.initialised:
            logging.info('Module {} initialising'.format(module_name))
            dynclass.init()
        else:
            logging.info('Module {} already initialised'.format(module_name))
    else:
        logging.info("Module {} is not active".format(module_name))
        if dynclass.initialised:
            logging.info('Module {} has been deactivated, unloading'.format(module_name))
            dynclass.unload()
            del dynclass
        else:
            logging.info('Module {} already disabled'.format(module_name))

def init_modules():
    import admin.models
    import admin.model_helper
    import webui
    module_list = admin.models.Module.query.filter_by(host_name=constant.HOST_NAME).order_by(
        admin.models.Module.start_order).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        #webui will block at init, postpone init for end
        if mod.name != admin.model_helper.get_mod_name(webui) and mod.name != 'main':
            init_module(mod.name, mod.active)
        else:
            if mod.name == admin.model_helper.get_mod_name(webui):
                global webui_running
                webui_running = mod.active
                pass
            elif mod.name == 'main':
                #no need to init main module, already initialised
                pass


def execute_command(command):
    global exit_code
    if command=='restart_app':
        exit_code = 5001
    elif command=='upgrade_app':
        exit_code = 5002
    elif command=='shutdown_app':
        exit_code = 137
    if exit_code != 0:
        unload()
#--------------------------------------------------------------------------#

def unload():
    logging.warning('Main module is unloading, application will exit')
    import webui, admin.thread_pool, mqtt_io
    global shutting_down
    shutting_down = True
    if webui.initialised:
        webui.unload()
    if mqtt_io.initialised:
        mqtt_io.unload()
    admin.thread_pool.thread_pool_enabled = False


def init():
    global LOGGING_LEVEL
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s:%(threadName)s:%(message)s',
                        level=LOGGING_LEVEL)
    logging.info('Logging level is {}'.format(LOGGING_LEVEL))
    common.init()
    global app, db, DB_LOCATION

    app = Flask('main')
    #app.config['TESTING'] = True
    app.config.update(DEBUG=True, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)

    db = SQLAlchemy(app)
    db.create_all()

    import admin.model_helper
    global MODEL_AUTO_UPDATE
    admin.model_helper.populate_tables(MODEL_AUTO_UPDATE)

    from admin import event
    event.init()
    init_modules()

    from admin import thread_pool
    import threading
    t = threading.Thread(target=thread_pool.main)
    t.daemon = True
    t.start()

    global initialised, shutting_down
    initialised = True
    if webui_running:
        import webui
        init_module(admin.model_helper.get_mod_name(webui), module_is_active=True)

    #if not blocking_webui_running:
    #    logging.info('Blocking app exit as no web ui is running')
    while not shutting_down:
        time.sleep(1)
    #logging.info('Exiting Blocking loop as web ui is now running')

def run(arg_list):
    if 'debug_remote' in arg_list:
        import ptvsd
        ptvsd.enable_attach(secret='secret',address=('0.0.0.0', 5678))
        print 'Enabled remote debugging, waiting 10 seconds for client to attach'
        ptvsd.wait_for_attach(timeout=10)
    global DB_LOCATION
    if 'db_disk' in arg_list:
        DB_LOCATION='sqlite:///../database.db'
    elif 'db_mem' in arg_list:
        DB_LOCATION='sqlite:////tmp/database.db'
    else:
        DB_LOCATION='sqlite:///../database.db'
        print 'Setting default DB location on disk as {}'.format(DB_LOCATION)

    global LOGGING_LEVEL
    if 'debug' in arg_list:
        LOGGING_LEVEL = logging.DEBUG
    elif 'warning' in arg_list:
        LOGGING_LEVEL = logging.WARNING
    global MODEL_AUTO_UPDATE
    MODEL_AUTO_UPDATE = 'model_auto_update' in arg_list
    init()
    print 'App EXIT'
    global exit_code
    sys.exit(exit_code)

#if 'main' in __name__:
#    run(sys.argv[1:])
#else:
#    print 'Not executing main, name is ' + __name__