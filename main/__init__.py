import signal
import sys
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy  # workaround for resolve issue
from flask_sqlalchemy import models_committed
from main.logger_helper import L
try:
    from wakeonlan import send_magic_packet
except ImportError as ex:
    from wakeonlan.wol import send_magic_packet

try:
    import pymysql
except ImportError as ex:
    print("Unable to import pymysql, err={}".format(ex))

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


class P:
    init_mod_list = []

    def __init__(self):
        pass


def my_import(name):
    # http://stackoverflow.com/questions/547829/how-to-dynamically-load-a-python-class
    try:
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod
    except Exception as ex:
        L.l.error("Unable to import module {}, err={}".format(name, ex), exc_info=True)
        return None


def init_module(module_name, module_is_active):
    if module_is_active:
        # L.l.info("Importing module {}".format(module_name))
        dynclass = my_import(module_name)
        if dynclass:
            # Log.logger.info('Module {} is marked as active'.format(module_name))
            if hasattr(dynclass, 'initialised'):
                inited = dynclass.initialised
            else:
                inited = dynclass.P.initialised
            if not inited:
                L.l.info('Module {} initialising'.format(module_name))
                dynclass.init()
                P.init_mod_list.append(module_name)
            else:
                L.l.info('Module {} already initialised, skipping init'.format(module_name))
        else:
            L.l.critical("Module {} failed to load".format(module_name))
    else:
        L.l.info("Module {} is marked as not active, skipping load".format(module_name))
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
        try:
            if hasattr(dynclass, 'initialised'):
                inited = dynclass.initialised
            else:
                inited = dynclass.P.initialised
            if inited:
                L.l.info('Module {} unloading'.format(module_name))
                dynclass.unload()
            else:
                L.l.info('Module {} is not initialised, skipping unload'.format(module_name))
        except Exception as ex:
            L.l.info("Error unloading module {}, ex={}".format(module_name, ex))


def init_modules(init_mod=None):
    import admin.models
    import admin.model_helper
    from common import Constant
    from main.logger_helper import L

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
                mod_name = mod_host_specific.name
                mod_active = mod_host_specific.active
            else:
                # Log.logger.info("Initialising generic mod definition name={} active={}".format(mod.name, mod.active))
                mod_name = mod.name
                mod_active = mod.active
            if init_mod is True:
                init_module(mod_name, mod_active)
            elif init_mod is False and mod_active is True:
                unload_module(mod_name)


def init_post_modules():
    # run post_init actions
    for module_name in P.init_mod_list:
        dynclass = my_import(module_name)
        if dynclass:
            # Log.logger.info('Module {} is marked as active'.format(module_name))
            if hasattr(dynclass, 'initialised'):
                inited = dynclass.initialised
            else:
                inited = dynclass.P.initialised
            if inited and hasattr(dynclass, 'post_init'):
                dynclass.post_init()


def signal_handler(signal_name, frame):
    L.l.info('I got signal {} frame {}, exiting'.format(signal_name, frame))
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
        L.l.info('Sending wol magic packet to MAC {}'.format(node.mac))
        send_magic_packet(node.mac)

    if exit_code != 0:
        unload()


def unload_modules():
    init_modules(init=False)

#  --------------------------------------------------------------------------  #


def unload():
    L.l.info('Main module is unloading, application will exit')
    import main.thread_pool

    global shutting_down
    shutting_down = True
    main.thread_pool.__thread_pool_enabled = False
    unload_modules()


def init():
    # carefull with order of imports
    import common
    from main import logger_helper
    from common import utils

    common.init_simple()
    logger_helper.L.init_logging()
    signal.signal(signal.SIGTERM, signal_handler)

    L.l.info('Collecting system info')
    from main import system_info
    system_info.init()

    from common import Constant
    common.init()

    global app, db, DB_LOCATION
    common.load_config_json()
    DB_LOCATION = "sqlite:///" + common.get_json_param(common.Constant.P_DB_PATH)
    L.l.info('DB file is at ' + DB_LOCATION)
    # from main.logger_helper import LOG_TO_TRANSPORT
    L.l.info('Initialising flask')
    # http://stackoverflow.com/questions/20646822/how-to-serve-static-files-in-flask
    # set the project root directory as the static folder, you can set others.
    app = Flask('main', static_folder='../webui/static')  # , static_url_path='')
    # app.config['TESTING'] = True
    app.config.update(DEBUG=True, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)
    app.debug = True
    app.config['SECRET_KEY'] = 'secret'
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    L.l.info('Initialising SQLAlchemy')
    db = SQLAlchemy(app)
    db.create_all()

    L.l.info('Checking main db tables')
    import admin.models
    import admin.model_helper
    global MODEL_AUTO_UPDATE

    admin.model_helper.populate_tables(MODEL_AUTO_UPDATE)
    reporting_enabled = admin.model_helper.get_param(Constant.DB_REPORTING_LOCATION_ENABLED)
    if reporting_enabled == "1" and not IS_STANDALONE_MODE:
        L.l.info('Checking history db tables')
        # try several times to connect to reporting DB
        for i in range(10):
            try:
                admin.model_helper.init_reporting()
                break
            except Exception as ex:
                L.l.critical("Local DB reporting capability is not available, err={}".format(ex))
                app.config['SQLALCHEMY_BINDS'] = None
            time.sleep(10)
    elif IS_STANDALONE_MODE:
        L.l.info('Skipping reporting feature initialising, standalone mode')

    import transport
    if not IS_STANDALONE_MODE:
        transport.init()
    else:
        L.l.info('Skipping transport initialising, standalone mode')

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

    if L.LOG_TO_TRANSPORT:
        L.l.addHandler(TransportLogging())
        L.l.info('Initialised logging via transport proxy')

    L.l.info('Initialising events - import')
    from admin import event
    L.l.info('Initialising events - init')
    event.init()

    L.l.info('Machine type is {}'.format(Constant.HOST_MACHINE_TYPE))
    L.l.info('Initialising modules')
    init_modules(init=True)

    L.l.info('Initialising generic processing threads')
    from main import thread_pool
    import threading
    t = threading.Thread(target=thread_pool.run_thread_pool)
    t.daemon = True
    t.start()

    from common import performance
    performance.init(admin.model_helper.get_param(Constant.P_PERF_FILE_PATH))

    global initialised, shutting_down
    initialised = True

    # trap all DB changes and propagate to event.py
    @models_committed.connect_via(app)
    def on_models_committed(sender, changes):
        from main.admin import event
        # L.l.debug('Model commit detected sender {} change {}'.format(sender, changes))
        event.on_models_committed(sender, changes)
    init_post_modules()
    L.l.info('Feeding dogs with grass until app will exit')
    global exit_code
    # stop app from exiting
    try:
        while not shutting_down:
            time.sleep(1)
    except KeyboardInterrupt:
        print('CTRL+C was pressed, exiting')
        exit_code = 1
    except Exception as ex:
        print('Main exit with exception {}'.format(ex))
    finally:
        unload()
    L.l.critical('Looping ended, app will exit')


def run(arg_list):
    if 'debug_remote' in arg_list:
        # https://blogs.msdn.microsoft.com/mustafakasap/2016/02/04/py-01-visual-studio-publish-python-script-on-a-unix-machine-remote-debug/
        # https://github.com/Microsoft/PTVS/wiki/Cross-Platform-Remote-Debugging
        try:
            import ptvsd
            ptvsd.enable_attach(address=('0.0.0.0', 5678), redirect_output=True)
            print('Enabled remote debugging, waiting 15 seconds for client to attach')
            ptvsd.wait_for_attach(timeout=15)
        except Exception as ex:
            print("Error in remote debug: {}".format(ex))
    import logging
    from main import logger_helper
    if 'debug' in arg_list:
        L.LOGGING_LEVEL = logging.DEBUG
    elif 'warning' in arg_list:
        L.LOGGING_LEVEL = logging.WARNING
    else:
        # this filters out message priority from being logged
        L.LOGGING_LEVEL = logging.INFO

    L.LOG_TO_SYSLOG = 'sysloglocal' in arg_list
    L.RUN_IN_LIVE = 'live' in arg_list

    for s in arg_list:
        # carefull with the order for uniqueness, start with longest words first
        if 'transport_syslog' in s:
            L.LOG_TO_TRANSPORT = True
        elif 'syslog=' in s:
            #syslog=logs2.papertrailapp.com:30445
            par_vals = s.split('=')[1].split(':')
            L.SYSLOG_ADDRESS = par_vals[0]
            L.SYSLOG_PORT = par_vals[1]
        elif 'log=' in s:
            # log=c:\tmp\iot-nohup.out
            L.LOG_FILE=s.split('=')[1]
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
    print('App EXIT')
    global exit_code
    sys.exit(exit_code)
