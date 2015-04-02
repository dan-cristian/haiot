# project/__init__.py

import time
import sys
from flask_sqlalchemy import SQLAlchemy #workaround for resolve issue
from flask import Flask, redirect, url_for
from flask_sqlalchemy import models_committed
import logging
import common

#location for sqlite db
DB_LOCATION=None
#default logging
LOGGING_LEVEL=logging.INFO
app=None
db=None
blocking_webui_running = False

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
        print "Module {} is active".format(module_name)
        if not dynclass.initialised:
            logging.info('Module {} initialising'.format(module_name))
            dynclass.init()
        else:
            logging.info('Module {} already initialised'.format(module_name))
    else:
        print "Module {} is not active".format(module_name)
        if dynclass.initialised:
            logging.info('Module {} has been deactivated, unloading'.format(module_name))
            dynclass.unload()
            del dynclass

def init_modules():
    import admin.models
    import admin.model_helper
    import webui
    module_list = admin.models.Module.query.order_by(admin.models.Module.start_order).all()
    for mod in module_list:
        assert isinstance(mod, admin.models.Module)
        #webui will block at init, postpone init for end
        if mod.name != admin.model_helper.get_mod_name(webui):
            init_module(mod.name, mod.active)
        else:
            global blocking_webui_running
            blocking_webui_running = True

def set_db_location(location):
    global DB_LOCATION
    if location == 'disk':
        DB_LOCATION='sqlite:///../database.db'
    else:
        if location == 'mem':
            DB_LOCATION='sqlite:////tmp/database.db'
        else:
            logging.critical('No DB location set {}'.format(location))

def set_logging_level(level):
    global LOGGING_LEVEL
    if level=='debug':
        LOGGING_LEVEL = logging.DEBUG
    else:
        if level=='warning':
            LOGGING_LEVEL = logging.WARNING

#--------------------------------------------------------------------------#

def init():
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(module)s:%(funcName)s:%(threadName)s:%(message)s',
                        level=LOGGING_LEVEL)
    logging.info('Logging level is {}'.format(LOGGING_LEVEL))
    common.init()
    global app, db, DB_LOCATION
    app = Flask('main')
    app.config.update(DEBUG=False, SQLALCHEMY_ECHO = False, SQLALCHEMY_DATABASE_URI=DB_LOCATION)

    db = SQLAlchemy(app)
    db.create_all()

    import admin.model_helper
    admin.model_helper.populate_tables()

    from admin import event
    event.init()
    init_modules()

    from admin import thread_pool
    import threading
    t = threading.Thread(target=thread_pool.main)
    t.daemon = True
    t.start()

    if blocking_webui_running:
        import webui
        init_module(admin.model_helper.get_mod_name(webui), True)

    if not blocking_webui_running:
        logging.info('Blocking app exit as no web ui is running')
        while not blocking_webui_running:

            time.sleep(1)
        logging.info('Exiting Blocking loop as web ui is now running')


#@app.route('/')
#def home():
#    return 'Main'

@models_committed.connect_via(app)
def on_models_committed(sender, changes):
    from admin import event
    logging.debug('Model commit detected sender {} change {}'.format(sender, changes))
    event.on_models_committed(sender, changes)

def main(argv):
    if 'disk' in argv:
        return 'disk'
    else:
        if 'mem' in argv:
            return 'mem'
        else:
            print 'usage: python main disk OR mem. Assuming disk as default'
            return 'disk'
            #sys.exit(1)

def run(arg_list):
    if 'remote' in arg_list:
        import ptvsd
        ptvsd.enable_attach(secret='secret',address=('0.0.0.0', 5678))
        print 'Enabled remote debugging, waiting 10 seconds for client to attach'
        ptvsd.wait_for_attach(timeout=10)
    location = main(arg_list)
    print('DB Location is {}'.format(location))
    set_db_location(location)
    if 'debug' in arg_list:
        set_logging_level('debug')
    else:
        if 'warning' in arg_list:
            set_logging_level('warning')
    
    init()
    print 'App EXIT'

if 'main' in __name__:
    run(sys.argv[1:])
else:
    print 'Not executing main, name is ' + __name__