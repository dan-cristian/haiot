# project/__init__.py

import time
import sys
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask import Flask, redirect, url_for
from flask_sqlalchemy import models_committed
import datetime
import signal
import logging, logging.handlers
import common
from common import constant

#location for sqlite db
DB_LOCATION=None
#default logging
LOGGING_LEVEL=logging.INFO
LOG_FILE=None
app=None
db=None
initialised = False
shutting_down=False
exit_code = 0
MODEL_AUTO_UPDATE=False
LOG_TO_SYSLOG = False

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
    module_list = admin.models.Module.query.filter_by(host_name=constant.HOST_NAME).order_by(
        admin.models.Module.start_order).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        #webui will block at init, postpone init for end
        if mod.name != 'main':
            init_module(mod.name, mod.active)

def signal_handler(signal, frame):
    logging.warning('I got signal {} frame {}, exiting'.format(signal, frame))
    global exit_code
    exit_code = 1
    unload()

def execute_command(command):
    global exit_code
    if command=='restart_app':
        exit_code = 131
    elif command=='upgrade_app':
        exit_code = 132
    elif command=='shutdown_app':
        exit_code = 133
    if exit_code != 0:
        unload()
#--------------------------------------------------------------------------#


def unload():
    logging.warning('Main module is unloading, application will exit')
    import webui, admin.thread_pool, mqtt_io
    global shutting_down
    shutting_down = True
    admin.thread_pool.thread_pool_enabled = False
    if webui.initialised:
        webui.unload()
    if mqtt_io.initialised:
        mqtt_io.unload()

def init():
    signal.signal(signal.SIGTERM, signal_handler)
    global LOGGING_LEVEL, LOG_FILE, LOG_TO_SYSLOG

    common.init()
    #my_logger = logging.getLogger('haiot ' + constant.HOST_NAME)
    #my_logger.setLevel(logging.DEBUG)
    #handler = logging.handlers.SysLogHandler(address = '/dev/log')
    #my_logger.addHandler(handler)
    #my_logger.debug('Program started on {} at {}'.format(datetime.datetime.now(), constant.HOST_NAME))
    if LOG_FILE is None:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s:%(threadName)s:%(message)s',
                        level=LOGGING_LEVEL)
    else:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s:%(threadName)s:%(message)s',
                        level=LOGGING_LEVEL, filename=LOG_FILE)
    logging.info('Logging level is {}'.format(LOGGING_LEVEL))
    #annoying info messages
    logging.getLogger("requests").setLevel(logging.WARNING)


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
    from admin import system_info
    system_info.init()
    init_modules()

    from admin import thread_pool
    import threading
    t = threading.Thread(target=thread_pool.main)
    t.daemon = True
    t.start()

    global initialised, shutting_down
    initialised = True

    @models_committed.connect_via(app)
    def on_models_committed(sender, changes):
        from main.admin import event
        logging.debug('Model commit detected sender {} change {}'.format(sender, changes))
        event.on_models_committed(sender, changes)

    #stop app from exiting
    from admin import thread_pool
    while not shutting_down:
        time.sleep(1)
        #logging.debug('Threads: {}'.format(thread_pool.get_thread_status()))

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

    global LOG_TO_SYSLOG
    if 'syslog' in arg_list:
        LOG_TO_SYSLOG = True

    for s in arg_list:
        if 'log=' in s:
            global LOG_FILE
            LOG_FILE=s.split('=')[1]
            print 'Log file is {}'.format(LOG_FILE)

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