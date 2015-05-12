# project/__init__.py

import time
import sys
import socket
import datetime
import signal

from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask import Flask
from flask_sqlalchemy import models_committed



#location for sqlite db
DB_LOCATION=None
#default logging
LOGGING_LEVEL=None
LOG_FILE=None
app=None
db=None
initialised = False
shutting_down=False
exit_code = 0
MODEL_AUTO_UPDATE=False
LOG_TO_SYSLOG = False
logger = None
SYSLOG_ADDRESS = None
SYSLOG_PORT = None
RUN_IN_LIVE = False

from . import logger

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
        logger.info('Module {} is active'.format(module_name))
        if not dynclass.initialised:
            logger.info('Module {} initialising'.format(module_name))
            dynclass.init()
        else:
            logger.info('Module {} already initialised'.format(module_name))
    else:
        logger.info("Module {} is not active".format(module_name))
        if dynclass.initialised:
            logger.info('Module {} has been deactivated, unloading'.format(module_name))
            dynclass.unload()
            del dynclass
        else:
            logger.info('Module {} already disabled'.format(module_name))

def init_modules():
    import admin.models
    import admin.model_helper
    from common import constant

    module_list = admin.models.Module.query.filter_by(host_name=constant.HOST_NAME).order_by(
        admin.models.Module.start_order).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        #webui will block at init, postpone init for end
        if mod.name != 'main':
            init_module(mod.name, mod.active)

def signal_handler(signal, frame):
    logger.info('I got signal {} frame {}, exiting'.format(signal, frame))
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
    logger.info('Main module is unloading, application will exit')
    import webui, admin.thread_pool, relay
    from transport import mqtt_io

    global shutting_down
    shutting_down = True
    admin.thread_pool.thread_pool_enabled = False
    if webui.initialised:
        webui.unload()
    if mqtt_io.initialised:
        mqtt_io.unload()
    if relay.initialised:
        relay.unload()

def init_logging():
    import logging
    import logging.handlers

    class ContextFilter(logging.Filter):
        hostname = socket.gethostname()

        def filter(self, record):
            record.hostname = ContextFilter.hostname
            return True

    global LOGGING_LEVEL, LOG_FILE, LOG_TO_SYSLOG, SYSLOG_ADDRESS, SYSLOG_PORT, RUN_IN_LIVE
    global logger
    log_name = 'haiot-' + socket.gethostname()
    logging.basicConfig(format='%(asctime)s haiot %(levelname)s %(module)s:%(funcName)s %(message)s')#%(threadName)s
    logger = logging.getLogger(log_name)

    logger.setLevel(LOGGING_LEVEL)

    if (SYSLOG_ADDRESS is not None) and (SYSLOG_PORT is not None):
        filter_log = ContextFilter()
        logger.addFilter(filter_log)
        syslog_papertrail = logging.handlers.SysLogHandler(address=(SYSLOG_ADDRESS, int(SYSLOG_PORT)))
        pap_formatter = logging.Formatter('%(asctime)s %(hostname)s haiot %(levelname)s %(module)s:%(funcName)s %(message)s',
                                          datefmt='%Y-%m-%dT%H:%M:%S')
        syslog_papertrail.setFormatter(pap_formatter)
        logger.addHandler(syslog_papertrail)
        logger.info('Initialised syslog with {}:{}'.format(SYSLOG_ADDRESS, SYSLOG_PORT))

    if LOG_TO_SYSLOG:
        try:
            handler = logging.handlers.SysLogHandler(address = '/dev/log')
            logger.addHandler(handler)
            logger.info('Syslog program started on {} at {}'.format(datetime.datetime.now(), socket.gethostname()))
        except Exception, ex:
            try:
                ntl = logging.handlers.NTEventLogHandler(appname=log_name)
                logger.addHandler(ntl)
            except Exception, ex:
                print 'Unable to init syslog handler err=' + ex
    else:
        if not LOG_FILE is None:
            file_handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*1, backupCount=3)
            logger.addHandler(file_handler)

    logger.info('Logging level is {}'.format(LOGGING_LEVEL))
    #remove annoying info messages
    logging.getLogger("requests").setLevel(logging.WARNING)
    if RUN_IN_LIVE:
        logger.info('Logger is set to live mode, disabling propagate')
        logger.propagate = False

def init():
    init_logging()
    signal.signal(signal.SIGTERM, signal_handler)

    import common
    common.init()

    global app, db, DB_LOCATION
    logger.info('Initialising flask')
    app = Flask('main')
    #app.config['TESTING'] = True
    app.config.update(DEBUG=True, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)

    logger.info('Initialising SQLAlchemy')
    db = SQLAlchemy(app)
    db.create_all()

    logger.info('Checking db tables')
    import admin.model_helper
    global MODEL_AUTO_UPDATE
    admin.model_helper.populate_tables(MODEL_AUTO_UPDATE)

    logger.info('Initialising events')
    from admin import event
    event.init()
    logger.info('Collecting system info')
    from admin import system_info
    system_info.init()
    from common import constant
    logger.info('Machine type is {}'.format(constant.HOST_MACHINE_TYPE))
    logger.info('Initialising modules')
    init_modules()

    logger.info('Initialising threads')
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
        logger.debug('Model commit detected sender {} change {}'.format(sender, changes))
        event.on_models_committed(sender, changes)

    logger.info('Looping until app exit')
    #stop app from exiting
    from admin import thread_pool
    while not shutting_down:
        time.sleep(1)
        #logger.debug('Threads: {}'.format(thread_pool.get_thread_status()))
    logger.critical('Looping ended, app will exit')

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
    import logging
    if 'debug' in arg_list:
        LOGGING_LEVEL = logging.DEBUG
    elif 'warning' in arg_list:
        LOGGING_LEVEL = logging.WARNING
    else:
        LOGGING_LEVEL = logging.INFO

    global LOG_TO_SYSLOG
    LOG_TO_SYSLOG = 'sysloglocal' in arg_list
    global RUN_IN_LIVE
    RUN_IN_LIVE = 'live' in arg_list

    for s in arg_list:
        #carefull with the order for unicity, start with longest words first
        if 'syslog=' in s:
            #syslog=logs2.papertrailapp.com:30445
            global SYSLOG_ADDRESS, SYSLOG_PORT
            par_vals = s.split('=')[1].split(':')
            SYSLOG_ADDRESS = par_vals[0]
            SYSLOG_PORT = par_vals[1]
        elif 'log=' in s:
            # log=c:\tmp\iot-nohup.out
            global LOG_FILE
            LOG_FILE=s.split('=')[1]


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