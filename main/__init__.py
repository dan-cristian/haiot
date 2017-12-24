import signal
import sys
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy  # workaround for resolve issue
from flask_sqlalchemy import models_committed
from wakeonlan import wol
from main.logger_helper import Log

try:
    import pymysql
except ImportError, ex:
    print "Unable to import pymysql, err={}".format(ex)

# location for main db - sqlite db
DB_LOCATION = None
# location for storing historical reporting data
DB_REPORTING_LOCATION = None

app = None
db = None
initialised = False
shutting_down = False
exit_code = 0
MODEL_AUTO_UPDATE = False
BIND_IP = None
BIND_PORT = None
IS_STANDALONE_MODE = None  # runs standalone, no node / mqtt connection & history

def my_import(name):
    # http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    try:
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod
    except Exception, ex:
        Log.logger.warning("Unable to import module {}, err={}".format(name, ex))
        return None


def init_module(module_name, module_is_active):
    if module_is_active:
        Log.logger.info("Importing module {}".format(module_name))
        dynclass = my_import(module_name)
        if dynclass:
            # Log.logger.info('Module {} is marked as active'.format(module_name))
            if not dynclass.initialised:
                Log.logger.info('Module {} initialising'.format(module_name))
                dynclass.init()
            else:
                Log.logger.info('Module {} already initialised, skipping init'.format(module_name))
        else:
            Log.logger.critical("Module {} failed to load".format(module_name))
    else:
        Log.logger.info("Module {} is marked as not active, skipping load".format(module_name))
        '''    if dynclass.initialised:
                Log.logger.info('Module {} has been deactivated, unloading'.format(module_name))
                dynclass.unload()
                del dynclass
            else:
                Log.logger.info('Module {} already disabled, skipping unload'.format(module_name))
        '''


def unload_module(module_name):
    dynclass = my_import(module_name)
    if dynclass:
        if dynclass.initialised:
            Log.logger.info('Module {} unloading'.format(module_name))
            dynclass.unload()
        else:
            Log.logger.info('Module {} is not initialised, skipping unload'.format(module_name))


def init_modules():
    import admin.models
    import admin.model_helper
    from common import Constant
    from main.logger_helper import Log

    m = admin.models.Module
    # http://docs.sqlalchemy.org/en/rel_0_9/core/sqlelement.html
    # keep host name default to '' rather than None (which does not work on filter in)
    # get the unique/distinct list of all modules defined in config, generic or host specific ones
    module_list = m.query.filter(m.host_name.in_([Constant.HOST_NAME, ""])).group_by(m.start_order).all()
    for mod in module_list:
        # Log.logger.info("Processing host specific module definition {} {}".format(mod.name, mod.active))
        assert isinstance(mod, admin.models.Module)
        if mod.name != 'main':
            # check if there is a host specific module and use it with priority over generic one
            mod_host_specific = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.name.in_([mod.name]))
            # mod_host_specific = m.query.filter(m.host_name.in_([constant.HOST_NAME]), m.name.in_([mod.name]))
            if mod_host_specific:
                # Log.logger.info("Initialising host specific module definition {} {}".format(
                #    mod_host_specific.name, mod_host_specific.active))
                init_module(mod_host_specific.name, mod_host_specific.active == 1)
            else:
                # Log.logger.info("Initialising generic module definition name={} active={}".format(mod.name, mod.active))
                init_module(mod.name, mod.active == 1)


def signal_handler(signal_name, frame):
    Log.logger.info('I got signal {} frame {}, exiting'.format(signal_name, frame))
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


def unload_modules():
    import admin.models
    import admin.model_helper
    from common import Constant
    from main.logger_helper import Log

    m = admin.models.Module
    # http://docs.sqlalchemy.org/en/rel_0_9/core/sqlelement.html
    # keep host name default to '' rather than None (which does not work on filter in)
    # get the unique/distinct list of all modules defined in config, generic or host specific ones
    module_list = m.query.filter(m.host_name.in_([Constant.HOST_NAME, ""])).group_by(m.start_order.desc()).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        if mod.name != 'main':
            try:
                unload_module(mod.name)
            except Exception, ex:
                print "Error unloading module: {}".format(ex)

#  --------------------------------------------------------------------------  #


def unload():
    Log.logger.info('Main module is unloading, application will exit')
    import webui, main.thread_pool, gpio
    from transport import mqtt_io

    global shutting_down
    shutting_down = True
    main.thread_pool.__thread_pool_enabled = False
    unload_modules()

    #if webui.initialised:
    #    webui.unload()
    #if mqtt_io.initialised:
    #    mqtt_io.unload()
    #if gpio.initialised:
    #    gpio.unload()


def init():
    # carefull with order of imports
    import common
    from main import logger_helper
    from common import utils

    common.init_simple()
    logger_helper.Log.init_logging()
    signal.signal(signal.SIGTERM, signal_handler)

    Log.logger.info('Collecting system info')
    from main import system_info
    system_info.init()

    from common import Constant
    common.init()

    global app, db, DB_LOCATION
    common.load_config_json()
    DB_LOCATION = "sqlite:///" + common.get_json_param(common.Constant.P_DB_PATH)
    Log.logger.info('DB file is at ' + DB_LOCATION)
    # from main.logger_helper import LOG_TO_TRANSPORT
    Log.logger.info('Initialising flask')
    # http://stackoverflow.com/questions/20646822/how-to-serve-static-files-in-flask
    # set the project root directory as the static folder, you can set others.
    app = Flask('main', static_folder='../webui/static')  # , static_url_path='')
    # app.config['TESTING'] = True
    app.config.update(DEBUG=True, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)
    app.debug = True
    app.config['SECRET_KEY'] = 'secret'
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    Log.logger.info('Initialising SQLAlchemy')
    db = SQLAlchemy(app)
    db.create_all()

    Log.logger.info('Checking main db tables')
    import admin.models
    import admin.model_helper
    global MODEL_AUTO_UPDATE

    admin.model_helper.populate_tables(MODEL_AUTO_UPDATE)
    reporting_enabled = admin.model_helper.get_param(Constant.DB_REPORTING_LOCATION_ENABLED)
    if reporting_enabled == "1" and not IS_STANDALONE_MODE:
        Log.logger.info('Checking history db tables')
        # http://docs.sqlalchemy.org/en/rel_0_9/dialects/mysql.html#module-sqlalchemy.dialects.mysql.mysqlconnector
        user = admin.model_helper.get_param(Constant.DB_REPORTING_USER)
        passwd = admin.model_helper.get_param(Constant.DB_REPORTING_PASS)
        uri = str(admin.model_helper.get_param(Constant.DB_REPORTING_LOCATION))
        uri_final = uri.replace('<user>', user).replace('<passwd>', passwd)
        SQLALCHEMY_BINDS = {
            'reporting': uri_final
            #, 'appmeta':      'sqlite:////path/to/appmeta.db'
        }
        app.config['SQLALCHEMY_BINDS'] = SQLALCHEMY_BINDS
        try:
            db.create_all(bind='reporting')
            Constant.HAS_LOCAL_DB_REPORTING_CAPABILITY = True
            admin.model_helper.check_history_tables()
        except Exception, ex:
            Log.logger.critical("Local DB reporting capability is not available, err={}".format(ex))
            app.config['SQLALCHEMY_BINDS'] = None
    elif IS_STANDALONE_MODE:
        Log.logger.info('Skipping reporting feature initialising, standalone mode')

    import transport
    if not IS_STANDALONE_MODE:
        transport.init()
    else:
        Log.logger.info('Skipping transport initialising, standalone mode')

    class LogMessage:
        def __init__(self):
            pass
        message_type = 'logging'
        message = ''
        level = ''
        source_host_ = Constant.HOST_NAME  # field name must be identical with constant.JSON_PUBLISH_SOURCE_HOST
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

    Log.logger.info('Machine type is {}'.format(Constant.HOST_MACHINE_TYPE))
    Log.logger.info('Initialising modules')
    init_modules()

    Log.logger.info('Initialising generic processing threads')
    from main import thread_pool
    import threading
    t = threading.Thread(target=thread_pool.run_thread_pool)
    t.daemon = True
    t.start()

    from main import cron
    cron.init()

    global initialised, shutting_down
    initialised = True

    # trap all DB changes and propagate to event.py
    @models_committed.connect_via(app)
    def on_models_committed(sender, changes):
        from main.admin import event
        Log.logger.debug('Model commit detected sender {} change {}'.format(sender, changes))
        event.on_models_committed(sender, changes)

    Log.logger.info('Feeding dogs with grass until app will exit')
    # stop app from exiting
    try:
        while not shutting_down:
            time.sleep(1)
    finally:
        unload()
    Log.logger.critical('Looping ended, app will exit')


def run(arg_list):
    if 'debug_remote' in arg_list:
        # https://blogs.msdn.microsoft.com/mustafakasap/2016/02/04/py-01-visual-studio-publish-python-script-on-a-unix-machine-remote-debug/
        # https://github.com/Microsoft/PTVS/wiki/Cross-Platform-Remote-Debugging
        try:
            import ptvsd
            ptvsd.enable_attach(secret='secret', address=('0.0.0.0', 5678))
            print 'Enabled remote debugging, waiting 15 seconds for client to attach'
            ptvsd.wait_for_attach(timeout=15)
        except Exception, ex:
            print "Error in remote debug: {}".format(ex)
    import logging
    from main import logger_helper
    if 'debug' in arg_list:
        Log.LOGGING_LEVEL = logging.DEBUG
    elif 'warning' in arg_list:
        Log.LOGGING_LEVEL = logging.WARNING
    else:
        # this filters out message priority from being logged
        Log.LOGGING_LEVEL = logging.INFO

    Log.LOG_TO_SYSLOG = 'sysloglocal' in arg_list
    Log.RUN_IN_LIVE = 'live' in arg_list

    for s in arg_list:
        # carefull with the order for uniqueness, start with longest words first
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


    global MODEL_AUTO_UPDATE, IS_STANDALONE_MODE
    MODEL_AUTO_UPDATE = 'model_auto_update' in arg_list
    IS_STANDALONE_MODE = 'standalone' in arg_list
    init()  # will block here until app is closed
    print 'App EXIT'
    global exit_code
    sys.exit(exit_code)
