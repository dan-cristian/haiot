# project/__init__.py

import time
import sys
import signal

from wakeonlan import wol
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask import Flask
from flask_sqlalchemy import models_committed
from main.logger_helper import Log

#location for sqlite db
DB_LOCATION=None
app=None
db=None
initialised = False
shutting_down=False
exit_code = 0
MODEL_AUTO_UPDATE=False
BIND_IP = None
BIND_PORT = None


def my_import(name):
    #http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    try:
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod
    except Exception, ex:
        Log.logger.warning("Unabel to import module {}, err={}".format(name, ex))
        return None

def init_module(module_name, module_is_active):
    Log.logger.info("Importing module {}".format(module_name))
    dynclass = my_import(module_name)
    if dynclass:
        if module_is_active:
            Log.logger.info('Module {} is marked as active'.format(module_name))
            if not dynclass.initialised:
                Log.logger.info('Module {} initialising'.format(module_name))
                dynclass.init()
            else:
                Log.logger.info('Module {} already initialised, skipping init'.format(module_name))
        else:
            Log.logger.info("Module {} is marked as not active ".format(module_name))
            if dynclass.initialised:
                Log.logger.info('Module {} has been deactivated, unloading'.format(module_name))
                dynclass.unload()
                del dynclass
            else:
                Log.logger.info('Module {} already disabled, skipping unload'.format(module_name))
    else:
        Log.logger.critical("Module {} cannot be loaded".format(module_name))

def init_modules():
    import admin.models
    import admin.model_helper
    from common import Constant
    from main.logger_helper import Log

    m = admin.models.Module

    #http://docs.sqlalchemy.org/en/rel_0_9/core/sqlelement.html

    #keep host name default to '' rather than None (which does not work on filter in)

    #TODO: remove if ok, module_list = m.query.filter(m.host_name.in_([constant.HOST_NAME, ""])).order_by(m.start_order).all()

    #get the unique/distinct list of all modules defined in config, generic or host specific ones
    module_list = m.query.filter(m.host_name.in_([Constant.HOST_NAME, ""])).group_by(m.start_order).all()

    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        if mod.name != 'main':
            #check if there is a host specific module and use it with priority over generic one

            mod_host_specific = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.name.in_([mod.name]))

            #mod_host_specific = m.query.filter(m.host_name.in_([constant.HOST_NAME]), m.name.in_([mod.name]))
            if mod_host_specific:
                Log.logger.info("Initialising host specific module definition")
                init_module(mod_host_specific.name, mod_host_specific.active)
            else:
                Log.logger.info("Initialising generic module definition")
                init_module(mod.name, mod.active)

def signal_handler(signal, frame):
    Log.logger.info('I got signal {} frame {}, exiting'.format(signal, frame))
    global exit_code
    exit_code = 1
    unload()

def execute_command(command, node=None):
    global exit_code
    exit_code = 0

    if command == 'restart_app':
        exit_code = 131
    elif command == 'upgrade_app':
        exit_code = 132
    elif command == 'shutdown_app':
        exit_code = 133
    elif command == 'wake':
        #http://techie-blog.blogspot.ro/2014/03/making-wake-on-lan-wol-work-in-windows.html
        Log.logger.info('Sending wol magic packet to MAC {}'.format(node.mac))
        wol.send_magic_packet(node.mac)

    if exit_code != 0:
        unload()

#--------------------------------------------------------------------------#


def unload():
    Log.logger.info('Main module is unloading, application will exit')
    import webui, admin.thread_pool, relay
    from transport import mqtt_io

    global shutting_down
    shutting_down = True
    admin.thread_pool.__thread_pool_enabled = False
    if webui.initialised:
        webui.unload()
    if mqtt_io.initialised:
        mqtt_io.unload()
    if relay.initialised:
        relay.unload()



def init():
    #carefull with order of imports
    import common
    from main import logger_helper
    from common import utils, Constant

    common.init_simple()
    logger_helper.Log.init_logging()
    signal.signal(signal.SIGTERM, signal_handler)

    common.init()

    global app, db, DB_LOCATION
    #from main.logger_helper import LOG_TO_TRANSPORT
    Log.logger.info('Initialising flask')
    app = Flask('main')
    #app.config['TESTING'] = True
    app.config.update(DEBUG=True, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)
    app.config['SECRET_KEY'] = 'secret'
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    Log.logger.info('Initialising SQLAlchemy')
    db = SQLAlchemy(app)
    db.create_all()

    Log.logger.info('Checking db tables')
    import admin.model_helper
    import admin.models
    global MODEL_AUTO_UPDATE
    admin.model_helper.populate_tables(MODEL_AUTO_UPDATE)

    import transport
    transport.init()

    class LogMessage:
        message_type = 'logging'
        message = ''
        level = ''
        source_host_ = Constant.HOST_NAME #field name must be identical with constant.JSON_PUBLISH_SOURCE_HOST
        datetime = utils.date_serialised(utils.get_base_location_now_date())

    import logging
    class TransportLogging(logging.Handler):
        def emit(self, record):
            if transport.initialised and transport.mqtt_io.client_connected:
                msg = LogMessage()
                msg.message = self.format(record)
                msg.level = record.levelname
                transport.send_message_json(utils.unsafeobj2json(msg))

    if Log.LOG_TO_TRANSPORT:
        Log.logger.addHandler(TransportLogging())
        Log.logger.info('Initialised logging via transport proxy')


    Log.logger.info('Initialising events - import')
    from admin import event
    Log.logger.info('Initialising events - init')
    event.init()
    Log.logger.info('Collecting system info')
    from admin import system_info
    system_info.init()
    from common import Constant
    Log.logger.info('Machine type is {}'.format(Constant.HOST_MACHINE_TYPE))
    Log.logger.info('Initialising modules')
    init_modules()

    Log.logger.info('Initialising generic processing threads')
    from admin import thread_pool
    import threading
    t = threading.Thread(target=thread_pool.run_thread_pool)
    t.daemon = True
    t.start()

    from admin import cron
    cron.init()

    global initialised, shutting_down
    initialised = True

    #trap all DB changes
    @models_committed.connect_via(app)
    def on_models_committed(sender, changes):
        from main.admin import event
        Log.logger.debug('Model commit detected sender {} change {}'.format(sender, changes))
        event.on_models_committed(sender, changes)

    Log.logger.info('Feeding dogs with grass until app will exit')
    #stop app from exiting
    while not shutting_down:
        time.sleep(1)
    Log.logger.critical('Looping ended, app will exit')

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

    import logging
    from main import logger_helper
    if 'debug' in arg_list:
        Log.LOGGING_LEVEL = logging.DEBUG
    elif 'warning' in arg_list:
        Log.LOGGING_LEVEL = logging.WARNING
    else:
        Log.LOGGING_LEVEL = logging.INFO

    Log.LOG_TO_SYSLOG = 'sysloglocal' in arg_list
    Log.RUN_IN_LIVE = 'live' in arg_list

    for s in arg_list:
        #carefull with the order for uniqueness, start with longest words first
        if 'transport_syslog' in s:
            Log.LOG_TO_TRANSPORT = True
        elif 'syslog=' in s:
            #syslog=logs2.papertrailapp.com:30445
            par_vals = s.split('=')[1].split(':')
            Log.SYSLOG_ADDRESS = par_vals[0]
            Log.SYSLOG_PORT = par_vals[1]
        elif 'log=' in s:
            # log=c:\tmp\iot-nohup.out
            Log.LOG_FILE=s.split('=')[1]
        elif 'bind_ip=' in s:
            global BIND_IP
            BIND_IP = s.split('=')[1]
        elif 'bind_port=' in s:
            global BIND_PORT
            BIND_PORT = s.split('=')[1]


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